import csv, re
from urllib.parse import urlsplit

src = "universities.csv"
dst = "websites.csv"

with open(src, encoding="utf-8-sig") as f, open(dst, "w", newline="") as out:
    w = csv.writer(out)
    for row in csv.reader(f):
        if not row: 
            continue
        domain = None
        for cell in reversed(row):
            cell = (cell or "").strip()
            if not cell:
                continue
            m = re.search(r'https?://[^\s,]+', cell)
            url = m.group(0) if m else cell
            if '.' not in url:
                continue
            parts = urlsplit(url if url.startswith('http') else 'http://' + url)
            host = (parts.netloc or parts.path.split('/')[0]).split('@')[-1].split(':')[0].strip()
            if host and '.' in host:
                domain = host
                break
        if domain:
            w.writerow([domain])