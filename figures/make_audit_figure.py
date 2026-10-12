"""3-panel scale-audit figure (mirrors a scientific instrument-audit layout) from
the real 500-report audit in eval/audit.json. Run: python figures/make_audit_figure.py"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
A = json.loads((ROOT / "eval" / "audit.json").read_text(encoding="utf-8"))

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10,
    "axes.edgecolor": "#969394", "axes.labelcolor": "#251f21",
    "xtick.color": "#585254", "ytick.color": "#585254", "text.color": "#251f21",
    "figure.dpi": 150,
})
TEAL, RED, GREY = "#73a89a", "#ed313e", "#b9b4b0"

our = np.array(A["our_tokens"]); gpt = np.array(A["gpt_tokens"])
nfig = np.array(A["n_figures"]); b1 = np.array(A["sample_b1"]); b4 = np.array(A["sample_b4"])
n = A["n_reports"]

fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15.5, 4.4))
fig.suptitle(f"Marathi grounded report generation — scale audit ({n} reports)",
             fontsize=13, fontweight="bold")

# Panel 1 — tokens per report, our tokenizer vs GPT-4o (sorted for readability)
order = np.argsort(gpt)[::-1]
x = np.arange(n)
ax1.plot(x, gpt[order], color=GREY, lw=1.4, label=f"GPT-4o (o200k): {gpt.sum():,} total")
ax1.plot(x, our[order], color=TEAL, lw=1.1, label=f"Marathi-BPE (ours): {our.sum():,} total")
ax1.fill_between(x, our[order], gpt[order], color=TEAL, alpha=.10)
ax1.set_title("Tokenization cost per report", fontsize=11)
ax1.set_xlabel("report (sorted by token count)"); ax1.set_ylabel("tokens to encode the report")
ax1.legend(frameon=False, fontsize=8.5, loc="upper right")
ax1.spines[["top", "right"]].set_visible(False)

# Panel 2 — faithfulness audit: grounded (B4) vs ungrounded (B1), sample
s = np.arange(1, len(b1) + 1)
ax2.axhline(1.0, color="#585254", ls="--", lw=1, alpha=.6)
ax2.plot(s, b4, "o-", color=TEAL, ms=5, lw=1.2, label="B4 grounded (ours)")
ax2.plot(s, b1, "o", color=RED, ms=5, label="B1 ungrounded")
for i in range(len(b1)):
    ax2.plot([s[i], s[i]], [b1[i], b4[i]], color=RED, lw=0.6, alpha=.4)
ax2.set_ylim(0.35, 1.06)
ax2.set_title(f"Faithfulness audit (sample of {len(b1)})", fontsize=11)
ax2.set_xlabel("sampled report"); ax2.set_ylabel("fraction of figures traceable")
ax2.legend(frameon=False, fontsize=8.5, loc="lower left")
ax2.spines[["top", "right"]].set_visible(False)

# Panel 3 — per-report token count: ours vs GPT-4o, colored by #figures
sc = ax3.scatter(gpt, our, c=nfig, cmap="viridis", s=18, alpha=.8, edgecolors="none")
lim = [0, max(gpt.max(), our.max()) * 1.05]
ax3.plot(lim, lim, color="#585254", ls="--", lw=1, alpha=.6)
ax3.text(lim[1] * .62, lim[1] * .72, "y = x (parity)", fontsize=8, color="#585254", rotation=38)
ax3.set_xlim(lim); ax3.set_ylim(lim)
ax3.set_title("Per-report tokens: ours vs GPT-4o", fontsize=11)
ax3.set_xlabel("GPT-4o tokens"); ax3.set_ylabel("our tokens")
ax3.spines[["top", "right"]].set_visible(False)
cb = fig.colorbar(sc, ax=ax3, pad=.02); cb.set_label("figures per report", fontsize=9)

fig.tight_layout(rect=[0, 0, 1, 0.96])
out = ROOT / "figures" / "fig6_scale_audit.png"
fig.savefig(out, bbox_inches="tight")
print("wrote", out.name)
print(f"det faithfulness mean={np.mean(A['det_faithfulness']):.3f} | "
      f"token savings={gpt.sum()/our.sum():.2f}x | B1={b1.mean():.3f} B4={b4.mean():.3f}")
