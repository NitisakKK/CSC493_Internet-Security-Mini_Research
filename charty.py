# plot_total_score_all_in_one.py
import re, math
import matplotlib.pyplot as plt

INPUT  = "output.txt"
OUTPUT = "total_score_all_Rajamangala.png"

# ปรับได้ตามใจ
STRIP_WWW  = True   # ตัด 'www.' ออกเพื่อให้สั้นลง
MAX_LABEL  = 40     # ตัด label ยาวเกินด้วย …
FONT       = 8      # ขนาดฟอนต์ y-tick และตัวเลขบนแท่ง
ANNOTATE   = True   # แสดงตัวเลขคะแนนท้ายแท่ง

# --- parse output.txt ---
with open(INPUT, "r", encoding="utf-8", errors="replace") as f:
    raw = f.read()

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

labels = [shorten(d) for d, _ in rows]
scores = [s for _, s in rows]

# --- plot (ทั้งหมดในรูปเดียว) ---
fig_w = 12
fig_h = max(6, 0.36 * len(labels))
fig, ax = plt.subplots(figsize=(fig_w, fig_h))

y = range(len(labels))
ax.barh(y, scores, align="center")

# ให้คะแนนมากอยู่ด้านบน และตัดช่องว่างหัว/ท้ายแท่งออก
ax.set_ylim(len(labels) - 0.5, -0.5)   # กำหนดขอบเอง + กลับแกนในตัว
ax.margins(x=0.02, y=0)                # ปิด vertical padding

ax.set_xlim(0, 100)
ax.set_xlabel("Score (0–100)")
ax.set_ylabel("Domain")
ax.set_title("Rajamangala University Domain")

ax.set_yticks(list(y))
ax.set_yticklabels(labels, fontsize=FONT)
ax.grid(axis="x", linestyle="--", alpha=0.25)

if ANNOTATE:
    for i, v in enumerate(scores):
        x = min(v + 1.5, 99)
        ax.text(x, i, f"{v}", va="center", fontsize=FONT)

# เผื่อที่ทางซ้ายตามความยาว label และดึงกราฟขึ้นเล็กน้อย
left_margin = min(0.65, max(0.25, 0.012 * max(len(lb) for lb in labels)))
fig.tight_layout()
fig.subplots_adjust(left=left_margin, top=0.92)   # ลดช่องว่างด้านบน

fig.savefig(OUTPUT, dpi=150)