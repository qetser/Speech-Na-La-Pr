"""Generate research-paper-style figures from the project's real results and the
base papers' reported numbers. Run: python figures/make_figures.py"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parent
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 11,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": "#969394", "axes.labelcolor": "#251f21",
    "xtick.color": "#585254", "ytick.color": "#585254", "text.color": "#251f21",
    "figure.dpi": 150,
})
TEAL, RED, GREY, DK = "#73a89a", "#ed313e", "#b9b4b0", "#251f21"


def bar_labels(ax, bars, fmt="{:.2f}"):
    for b in bars:
        ax.text(b.get_x() + b.get_width() / 2, b.get_height(),
                fmt.format(b.get_height()), ha="center", va="bottom", fontsize=9)


# Fig 1 — faithfulness: ungrounded vs grounded, across models (our Experiment B)
def fig_models():
    models = ["GPT-4o", "GPT-4o-mini"]
    b1 = [0.588, 0.831]
    b4 = [1.000, 1.000]
    x = range(len(models)); w = 0.36
    fig, ax = plt.subplots(figsize=(6, 3.6))
    r1 = ax.bar([i - w / 2 for i in x], b1, w, label="B1 · ungrounded", color=RED, alpha=.85)
    r2 = ax.bar([i + w / 2 for i in x], b4, w, label="B4 · grounded (ours)", color=TEAL)
    bar_labels(ax, r1); bar_labels(ax, r2)
    ax.set_xticks(list(x)); ax.set_xticklabels(models)
    ax.set_ylim(0, 1.15); ax.set_ylabel("Faithfulness (figures traceable)")
    ax.set_title("Grounding reaches 100% faithfulness on every model", fontweight="bold", fontsize=12)
    ax.legend(frameon=False, loc="lower center", ncol=2, bbox_to_anchor=(0.5, -0.28))
    fig.tight_layout(); fig.savefig(OUT / "fig1_models_faithfulness.png", bbox_inches="tight")


# Fig 2 — B1 -> B2 -> B4 ablation (our Experiment A, 10-report benchmark)
def fig_ablation():
    sys = ["B1\nungrounded", "B2\ndeterministic", "B4\ngrounded (ours)"]
    vals = [0.629, 1.000, 1.000]
    cols = [RED, GREY, TEAL]
    fig, ax = plt.subplots(figsize=(6, 3.6))
    bars = ax.bar(sys, vals, color=cols, width=.6)
    bar_labels(ax, bars)
    ax.set_ylim(0, 1.15); ax.set_ylabel("Faithfulness")
    ax.set_title("Ablation: grounding + verification removes hallucination",
                 fontweight="bold", fontsize=12)
    ax.axhline(1.0, color=TEAL, lw=1, ls="--", alpha=.5)
    fig.tight_layout(); fig.savefig(OUT / "fig2_ablation.png", bbox_inches="tight")


# Fig 3 — tokenizer fertility (our Experiment C)
def fig_fertility():
    toks = ["char\nbaseline", "GPT-3.5/4\n(cl100k)", "GPT-4o\n(o200k)", "Marathi-BPE\n(ours)"]
    vals = [6.76, 7.98, 2.80, 2.18]
    cols = [GREY, RED, GREY, TEAL]
    fig, ax = plt.subplots(figsize=(6.2, 3.6))
    bars = ax.bar(toks, vals, color=cols, width=.62)
    bar_labels(ax, bars, "{:.2f}")
    ax.set_ylabel("Fertility (tokens / word)")
    ax.set_title("Our tokenizer encodes Marathi in fewer tokens", fontweight="bold", fontsize=12)
    fig.tight_layout(); fig.savefig(OUT / "fig3_tokenizer_fertility.png", bbox_inches="tight")


# Fig 4 — base paper: Marathi tokenizer tax vs English (Tokenizer Tax, 2607.24276)
def fig_tax():
    toks = ["GPT-2", "cl100k\n(GPT-3.5/4)", "o200k\n(GPT-4o)", "XLM-R\n(multiling.)"]
    vals = [9.04, 5.84, 2.11, 1.41]
    cols = [GREY, RED, GREY, TEAL]
    fig, ax = plt.subplots(figsize=(6.2, 3.6))
    bars = ax.bar(toks, vals, color=cols, width=.62)
    bar_labels(ax, bars, "{:.2f}×")
    ax.axhline(1.0, color=DK, lw=1, ls="--", alpha=.6)
    ax.text(3.35, 1.05, "English parity", fontsize=8, color=DK, ha="right")
    ax.set_ylabel("Marathi fertility tax (× English)")
    ax.set_title("Base paper: the tokenizer tax on Marathi (arXiv:2607.24276)",
                 fontweight="bold", fontsize=11)
    fig.tight_layout(); fig.savefig(OUT / "fig4_paper_tokenizer_tax.png", bbox_inches="tight")


# Fig 5 — base paper: IndicGenBench Marathi vs English (2404.16816), chrF
def fig_indicgenbench():
    models = ["GPT-4", "PaLM-2-L"]
    mr = [22.4, 25.4]; en = [30.3, 41.1]
    x = range(len(models)); w = 0.36
    fig, ax = plt.subplots(figsize=(6, 3.6))
    r1 = ax.bar([i - w / 2 for i in x], mr, w, label="Marathi", color=TEAL)
    r2 = ax.bar([i + w / 2 for i in x], en, w, label="English", color=GREY)
    bar_labels(ax, r1, "{:.1f}"); bar_labels(ax, r2, "{:.1f}")
    ax.set_xticks(list(x)); ax.set_xticklabels(models)
    ax.set_ylabel("chrF (summarization)")
    ax.set_title("Base paper: Marathi↔English gap persists (arXiv:2404.16816)",
                 fontweight="bold", fontsize=11)
    ax.legend(frameon=False, loc="upper left")
    fig.tight_layout(); fig.savefig(OUT / "fig5_paper_indicgenbench.png", bbox_inches="tight")


if __name__ == "__main__":
    fig_models(); fig_ablation(); fig_fertility(); fig_tax(); fig_indicgenbench()
    print("wrote figures:", sorted(p.name for p in OUT.glob("*.png")))
