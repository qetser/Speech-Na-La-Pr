"""FastAPI backend exposing the pipeline to the React frontend.

Run:  uvicorn server.app:app --reload --port 8000
The frontend calls POST /api/generate; the response matches the exact JSON
contract that frontend/src/lib/pipeline.js already renders.
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from pipeline.pdf import render_report_pdf
from pipeline.report import build_comparison, build_report
from pipeline.run import run_pipeline

app = FastAPI(title="Marathi Grounded Report Generation")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class GenerateRequest(BaseModel):
    csv: str
    engine: str = "auto"          # auto | llm | deterministic
    row: int = 1


class Fact(BaseModel):
    label: str = ""
    value: str = ""


class ReportRequest(BaseModel):
    subject: str
    report_type: str = ""
    facts: list[Fact] = []
    notes: str = ""
    engine: str = "auto"


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/generate")
def generate(req: GenerateRequest) -> dict:
    try:
        return run_pipeline(req.csv, engine=req.engine, row_index=req.row)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(e))


def _validate(req: ReportRequest) -> list[dict]:
    if not req.subject.strip():
        raise HTTPException(status_code=400, detail="Subject is required.")
    facts = [f.model_dump() for f in req.facts if f.value.strip()]
    if not facts:
        raise HTTPException(status_code=400, detail="Add at least one detail (label + value).")
    return facts


@app.post("/api/report")
def report(req: ReportRequest) -> dict:
    facts = _validate(req)
    try:
        return build_report(req.subject, facts, req.report_type, req.notes, req.engine)
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/report/compare")
def report_compare(req: ReportRequest) -> dict:
    facts = _validate(req)
    try:
        return build_comparison(req.subject, facts, req.report_type, req.notes, req.engine)
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(e))


class PdfRequest(BaseModel):
    title: str
    sections: list[dict] = []
    submitted_by: str = "अहवाल सादरकर्ता\n(ग्रामसेवक)"
    authorised_by: str = "सक्षम अधिकारी\n(सरपंच)"
    place: str = ""


@app.post("/api/report/pdf")
def report_pdf(req: PdfRequest) -> Response:
    if not req.title.strip() or not req.sections:
        raise HTTPException(status_code=400, detail="Need a title and sections.")
    try:
        pdf = render_report_pdf(req.title, req.sections, req.submitted_by,
                                req.authorised_by, req.place)
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(e))
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="report.pdf"'})
