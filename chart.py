# plot_total_score_fixed.py
import re
import numpy as np
import matplotlib.pyplot as plt

INPUT  = "output.txt"
OUTPUT = "total_score_by_3k.png"
TOPN   = None  # เช่น 20 ถ้าต้องการเฉพาะ Top 20

with open(INPUT, "r", encoding="utf-8", errors="replace") as f:
    raw = f.read()

# ดึงโดเมน+คะแนนจากบล็อกเดียวกัน
pattern = r"^----\s+(.+?)\s+----[\s\S]*?^TotalScore:\s*([0-9]+)\s*/\s*100"
matches = re.findall(pattern, raw, flags=re.M)

rows = [(d.strip(), int(s)) for d, s in matches]
if not rows:
    raise SystemExit("ไม่พบ Domain/TotalScore ใน output.txt")

# เรียงคะแนน มาก->น้อย และเลือก TopN ถ้ากำหนด
rows.sort(key=lambda x: x[1], reverse=True)
if TOPN:
    rows = rows[:TOPN]

domains = [d for d, _ in rows]
scores  = [s for _, s in rows]
n = len(domains)

# ขนาดรูปปรับตามจำนวนโดเมน
fig_w = max(8, min(0.6 * n + 2, 40))  # จำกัดกว้างสุด 40 นิ้ว

fig, ax = plt.subplots(figsize=(fig_w, 6))

# ------------------ จุดสำคัญเรื่องเว้นระยะและระยะห่าง ------------------
x = np.arange(n, dtype=float)  # ศูนย์แท่งที่ 0..n-1
bar_width = 0.82               # ช่องว่างระหว่างแท่ง = 1 - bar_width  (เช่น 0.18)
left_margin_bars  = 1.0        # เว้นซ้าย ~ เท่า 'หนึ่งแท่ง'
right_margin_bars = 0.30       # เว้นขวานิดหน่อยให้สมดุล

bars = ax.bar(x, scores, width=bar_width)

# ปิด auto padding แล้วกำหนดขอบเอง
ax.margins(x=0)
ax.set_xlim(-left_margin_bars, (n - 1) + right_margin_bars)
# -------------------------------------------------------------------------

ax.set_ylim(0, 100)
ax.set_ylabel("Score")
ax.set_xlabel("Domain Name")
ax.set_title("KMUTT vs KMITL vs KMUTNB")

# ตั้ง tick และป้ายโดเมน (ตัวอักษรตรง ไม่เอียง)
ax.set_xticks(x)
ax.set_xticklabels(domains, rotation=90, ha="right", rotation_mode="anchor")

# เส้นกริดแนวนอนให้อ่านง่าย
ax.grid(axis="y", linestyle="--", alpha=0.30)

# แสดงตัวเลขบนแท่ง
for xi, v in zip(x, scores):
    ax.text(xi, v + 1, f"{v}", ha="center", va="bottom", fontsize=9)

# กันป้ายด้านล่างโดนตัด และเผื่อสำหรับ label ยาว ๆ
plt.tight_layout()
fig.subplots_adjust(bottom=0.28)

plt.savefig(OUTPUT, dpi=150)
plt.show()
print(f"Saved chart to {OUTPUT}")