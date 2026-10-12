"""Marathi grounded report-generation pipeline (Components 1-5 of plan.md).

Public entry point: pipeline.run.run_pipeline(csv_text, schema, lexicon, engine)
Returns the same JSON contract the React frontend consumes:

    {
      "slots": [{"id": str, "tokens": [{"text": str, "source": Optional[str]}]}],
      "verification": {"ok": bool, "total": int, "traceable": int,
                        "unsupported": int, "claims": [{"field","value","cell"}]},
      "engine": "llm" | "deterministic",
    }
"""
# Load a repo-root .env (if present) so API keys are available to every entry
# point (CLI, server, eval) without exporting them in the shell.
try:
    from dotenv import load_dotenv
    from pathlib import Path
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except Exception:
    pass

from .run import run_pipeline  # noqa: E402,F401

__all__ = ["run_pipeline"]
