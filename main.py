import csv, subprocess, re
from datetime import datetime

csv_file = "websites.csv"
output_file = "output.txt"

def get_info(domain):
    cmds = [
        f'echo | openssl s_client -connect {domain}:443 2>&1',
        f'openssl s_client -connect {domain}:443 -servername {domain} 2>&1'
    ]
    for cmd in cmds:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if "BEGIN CERTIFICATE" not in res.stdout:
            continue

        proto = re.search(r'Protocol\s*:\s*([A-Za-z0-9\.\-]+)', res.stdout)
        proto = proto.group(1) if proto else "-"

        cert = subprocess.run(f'{cmd} | openssl x509 -text -noout',
                              shell=True, capture_output=True, text=True).stdout

        algo = re.search(r'Public Key Algorithm:\s*(.*)', cert)
        key  = re.search(r'(?:RSA\s+)?Public-Key:\s*\((\d+\s*bits?)\)', cert)
        exp  = re.search(r'Not After\s*:\s*(.*)', cert)

        not_after = exp.group(1).strip() if exp else None
        days_left = "-"
        if not_after:
            try:
                expiry_date = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
                days_left = (expiry_date - datetime.utcnow()).days
            except ValueError:
                try:
                    expiry_date = datetime.strptime(not_after, "%b %d %H:%M:%S %Y")
                    days_left = (expiry_date - datetime.utcnow()).days
                except ValueError:
                    days_left = "-"

        return {
            "Protocol": proto,
            "Algorithm": algo.group(1).strip() if algo else "-",
            "KeySize": key.group(1).strip() if key else "-",
            "NotAfter": not_after if not_after else "-",
            "DaysLeft": days_left
        }
    return None

with open(csv_file) as f, open(output_file, "w") as out:
    for row in csv.reader(f):
        if not row or not row[0].strip(): 
            continue
        domain = re.sub(r"^https?://", "", row[0].strip()).strip("/")
        out.write(f"\n=== {domain} ===\n")
        info = get_info(domain)
        if not info:
            out.write("Failed to get certificate\n")
            continue
        for k, v in info.items():
            out.write(f"{k}: {v}\n")

