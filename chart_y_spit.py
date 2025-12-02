# plot_total_score_paginated.py
import re, math
import matplotlib.pyplot as plt

INPUT       = "output.txt"
OUT_PREFIX  = "total_score_page_private_university"   # ไฟล์จะเป็น total_score_page_01.png, 02.png, ...
PAGE_SIZE   = 20                    # จำนวนโดเมนต่อรูป
STRIP_WWW   = True                  # ตัด www. ออกเพื่อให้สั้นลง
MAX_LABEL   = 40                    # ตัดชื่อโดเมนยาวเกินด้วย …
FONT        = 8                     # ฟอนต์ y-tick และตัวเลขท้ายแท่ง
ANNOTATE    = True                  # แสดงตัวเลขคะแนนท้ายแท่ง

# --- อ่านและพาร์ส output.txt ---
with open(INPUT, "r", encoding="utf-8", errors="replace") as f:
    raw = f.read()

# จับโดเมน + คะแนนจากบล็อกเดียวกัน
pattern = r"^----\s+(.+?)\s+----[\s\S]*?^TotalScore:\s*([0-9]+)\s*/\s*100"
rows = [(d.strip(), int(s)) for d, s in re.findall(pattern, raw, flags=re.M)]
if not rows:
    raise SystemExit("No Domain/TotalScore found in output.txt")

# เรียงคะแนน มาก -> น้อย
rows.sort(key=lambda x: x[1], reverse=True)

def shorten(name: str) -> str:
    n = name
    if STRIP_WWW and n.lower().startswith("www."):
        n = n[4:]
    return n if len(n) <= MAX_LABEL else n[:MAX_LABEL-1] + "…"

total_pages = math.ceil(len(rows) / PAGE_SIZE)
for p in range(total_pages):
    chunk   = rows[p*PAGE_SIZE:(p+1)*PAGE_SIZE]
    labels  = [shorten(d) for d, _ in chunk]
    scores  = [s for _, s in chunk]

    # --- วาดกราฟแนวนอน (Horizontal bar) ---
    fig_w = 12
    fig_h = max(6, 0.42 * len(labels))  # สูงขึ้นตามจำนวนโดเมนในหน้า
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))

    y = range(len(labels))
    ax.barh(y, scores, align="center")

    # ให้รายการแรก (คะแนนสูงสุดของหน้านี้) อยู่ด้านบน + ตัด headroom
    ax.set_ylim(len(labels) - 0.5, -0.5)
    ax.margins(x=0.02, y=0)

    ax.set_xlim(0, 100)
    ax.set_xlabel("Score (0–100)")
    ax.set_ylabel("Domain")
    ax.set_title(f"TotalScore by Domain (Page {p+1}/{total_pages})")

    ax.set_yticks(list(y))
    ax.set_yticklabels(labels, fontsize=FONT)
    ax.grid(axis="x", linestyle="--", alpha=0.25)

    if ANNOTATE:
        for i, v in enumerate(scores):
            x = min(v + 1.5, 99)  # กันตัวเลขล้นขวา
            ax.text(x, i, f"{v}", va="center", fontsize=FONT)

    # เผื่อขอบซ้ายตามความยาว label
    left_margin = min(0.65, max(0.25, 0.012 * max(len(lb) for lb in labels)))
    fig.tight_layout()
    fig.subplots_adjust(left=left_margin, top=0.92, bottom=0.06, right=0.98)

    outpath = f"{OUT_PREFIX}{p+1:02d}.png"
    fig.savefig(outpath, dpi=150)
    plt.close(fig)
    print("Saved:", outpath)

print(f"Done. Pages: {total_pages}, items: {len(rows)}")