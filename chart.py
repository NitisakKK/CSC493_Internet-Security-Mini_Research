# plot_total_score_fixed.py
import re
import matplotlib.pyplot as plt

INPUT = "output.txt"
OUTPUT = "total_score_by_ratchapat.png" # ใส่ชื่อ output
TOPN = None  # ตั้งเป็น 20 ถ้าอยากโชว์เฉพาะ Top 20

with open(INPUT, "r", encoding="utf-8", errors="replace") as f:
    raw = f.read()

# ดึงโดเมน+คะแนนจากบล็อกเดียวกัน (ทนทานกว่าแยกค้นทีละบรรทัด)
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

# ขนาดรูปปรับตามจำนวนโดเมน เพื่อให้ label ไม่ทับกัน/ไม่โดนตัด
fig_w = max(8, min(0.6 * len(domains) + 2, 40))  # จำกัดกว้างสุด 40 นิ้ว
plt.figure(figsize=(fig_w, 6))

# ใช้ตำแหน่งตัวเลขแล้วตั้ง tick label เอง (กันหาย)
xpos = range(len(domains))
plt.bar(xpos, scores)
plt.ylim(0, 100)
plt.ylabel("Score")
plt.xlabel("Domain Name")
plt.title("Ratchapat University")

# ตั้งชื่อโดเมนเป็น tick labels + หมุน
plt.xticks(list(xpos), domains, rotation=45, ha="right")

# เส้นกริดแนวนอนอ่านง่าย
plt.grid(axis="y", linestyle="--", alpha=0.3)

# ตัวเลขบนแท่ง
for i, v in enumerate(scores):
    plt.text(i, v + 1, f"{v}", ha="center", va="bottom", fontsize=9)

# กัน label โดนตัดขอบล่าง
plt.tight_layout()
plt.gcf().subplots_adjust(bottom=0.28)

plt.savefig(OUTPUT, dpi=150)
plt.show()
print(f"Saved chart to {OUTPUT}")