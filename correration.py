# correration.py  (locked X, multi-Y) — single color points + trendline + equality line
import argparse, os, re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def compute_stats(x: np.ndarray, y: np.ndarray):
    if len(x) < 2:
        return float("nan"), float("nan"), float("nan"), float("nan"), float("nan")
    m, c = np.polyfit(x, y, 1)
    y_pred = m * x + c
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    x_s = pd.Series(x); y_s = pd.Series(y)
    pearson = x_s.corr(y_s, method="pearson")
    spearman = x_s.rank().corr(y_s.rank(), method="pearson")
    return m, c, r2, pearson, spearman

def _safe_name(s: str) -> str:
    return re.sub(r'[^A-Za-z0-9_\-]+', '_', str(s).strip())

def plot_one(x_fixed: pd.Series, y_raw: pd.Series,
             label_x: str, label_y: str,
             outpath: str, max_score: float = 100.0):
    # ล็อก X และกรองค่าที่ไม่ใช่ตัวเลข
    x_num = pd.to_numeric(x_fixed, errors="coerce")
    y_num = pd.to_numeric(y_raw,  errors="coerce")
    mask = ~x_num.isna() & ~y_num.isna()
    x = x_num[mask].values
    y = y_num[mask].values
    if len(x) == 0:
        raise SystemExit(f"No valid data pairs for {label_y}")

    m, c, r2, pearson, spearman = compute_stats(x, y)

    # พล็อต: จุดสีเดียว + เส้นแนวโน้ม + เส้น equality
    base_color = "C0"
    plt.figure(figsize=(8, 6))
    plt.scatter(x, y, s=28, alpha=0.9, label="Data", color=base_color)

    xs = np.linspace(0, max_score, 200)
    plt.plot(xs, m*xs + c, linewidth=2, label="Trendline (linear)", color=base_color)
    plt.plot(xs, xs, linestyle="--", linewidth=1.4, color="gray",
             label=f"Equality line ({label_y} = {label_x})")

    plt.xlim(0, max_score); plt.ylim(0, max_score)
    plt.xlabel(f"TotalScore ({label_x}) [0–{int(max_score)}]")
    plt.ylabel(f"TotalScore ({label_y}) [0–{int(max_score)}]")
    plt.title(f"Correlation of Total Scores ({label_x} vs {label_y})")
    plt.legend()
    plt.tight_layout()
    plt.savefig(outpath, dpi=150)
    plt.close()

    return {
        "pearson": pearson, "spearman": spearman,
        "m": m, "c": c, "r2": r2, "n": len(x)
    }

def main():
    ap = argparse.ArgumentParser(description="Correlation scatter with locked X and multiple Y columns")
    ap.add_argument("-i","--input",   default="correration.csv")
    ap.add_argument("-o","--outdir",  default="corr_out")
    ap.add_argument("--x-col",        default="our", help="คอลัมน์แกน X (เช่น our หรือ 'our platform')")
    ap.add_argument("--y-cols",       nargs="+", default=["sucuri","pentest","mozilla"],
                    help="รายชื่อคอลัมน์แกน Y หลายชุด")
    ap.add_argument("--label-x",      default="Our_Platform")
    ap.add_argument("--labels-y",     nargs="+", default=None,
                    help="ป้ายชื่อสำหรับ Y ให้ตรงจำนวนกับ --y-cols (ไม่ระบุ = ใช้ชื่อคอลัมน์)")
    ap.add_argument("--max-score",    type=float, default=100.0)
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    df = pd.read_csv(args.input)

    if args.x_col not in df.columns:
        raise SystemExit(f"Column '{args.x_col}' not found in CSV. Available: {list(df.columns)}")
    x_fixed = df[args.x_col]

    labels_y = args.labels_y or args.y_cols
    if len(labels_y) != len(args.y_cols):
        raise SystemExit("--labels-y ต้องมีจำนวนเท่ากับ --y-cols")

    summary_lines = []
    for ycol, ylab in zip(args.y_cols, labels_y):
        if ycol not in df.columns:
            summary_lines.append(f"[SKIP] '{ycol}' not in CSV\n")
            continue
        out_file = os.path.join(
            args.outdir, f"scatter_{_safe_name(args.x_col)}_vs_{_safe_name(ycol)}.png"
        )
        stats = plot_one(x_fixed, df[ycol], args.label_x, ylab, out_file,
                         max_score=args.max_score)
        summary_lines.append(
            f"{ylab}: n={stats['n']}, Pearson={stats['pearson']:.4f}, "
            f"Spearman={stats['spearman']:.4f}, R^2={stats['r2']:.4f}, "
            f"line: y = {stats['m']:.4f}x + {stats['c']:.4f} -> {out_file}"
        )

    with open(os.path.join(args.outdir, "correlation_summary.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(summary_lines))

    print("Done. Files saved in:", args.outdir)
    for line in summary_lines:
        print(" -", line)

if __name__ == "__main__":
    main()