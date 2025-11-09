import csv, subprocess, re
from urllib.parse import urlsplit
from datetime import datetime, UTC

csv_file = "websites.csv"
output_file = "output.txt"

def extract_domain_from_row(row):
    for cell in reversed(row):
        cell = (cell or "").strip()
        if not cell:
            continue
        m = re.search(r'https?://[^\s,]+', cell)
        url = m.group(0) if m else cell
        if '.' not in url:
            continue
        parts = urlsplit(url if url.startswith('http') else 'http://' + url)
        host = parts.netloc or parts.path.split('/')[0]
        host = host.split('@')[-1].split(':')[0]
        host = host.strip()
        if host and '.' in host:
            return host
    return None

def get_info(domain):
    cmds = [
        f'echo | openssl s_client -connect {domain}:443 2>&1',
        f'echo | openssl s_client -connect {domain}:443 -servername {domain} 2>&1'
    ]
    for cmd in cmds:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if "BEGIN CERTIFICATE" not in res.stdout:
            continue
        proto_m = re.search(r'Protocol\s*:\s*([A-Za-z0-9\.\-]+)', res.stdout)
        proto = proto_m.group(1) if proto_m else "-"
        cert_text = subprocess.run(f'{cmd} | openssl x509 -text -noout', shell=True, capture_output=True, text=True).stdout
        exp_m = re.search(r'Not After\s*:\s*(.*)', cert_text)
        not_after = exp_m.group(1).strip() if exp_m else None
        days_left = "-"
        if not_after:
            expiry_date = None
            for fmt in ("%b %d %H:%M:%S %Y %Z", "%b %d %H:%M:%S %Y"):
                try:
                    expiry_date = datetime.strptime(not_after, fmt)
                    break
                except ValueError:
                    pass
            if expiry_date:
                if expiry_date.tzinfo is None:
                    expiry_date = expiry_date.replace(tzinfo=UTC)
                days_left = (expiry_date - datetime.now(UTC)).days
        verify_cmd = f'echo | openssl s_client -connect {domain}:443 -servername {domain} -verify_return_error 2>&1'
        verify_res = subprocess.run(verify_cmd, shell=True, capture_output=True, text=True)
        vr_m = re.search(r'Verify return code:\s*(\d+)', verify_res.stdout)
        chain_trusted = (vr_m and vr_m.group(1) == "0")
        return {"Protocol": proto, "DaysLeft": days_left, "CertText": cert_text, "ChainTrusted": chain_trusted}
    return {"Protocol": "-", "DaysLeft": "-", "CertText": "", "ChainTrusted": False}

def match_hostname(domain: str, pattern: str) -> bool:
    domain = domain.lower()
    pattern = pattern.lower()
    if pattern.startswith("*."):
        suffix = pattern[1:]
        return domain.endswith(suffix) and domain.count(".") > suffix.count(".")
    return domain == pattern

def hostname_matches(cert_text: str, domain: str) -> bool:
    sans = re.findall(r'DNS:([^,\s]+)', cert_text)
    for name in sans:
        if match_hostname(domain, name.strip()):
            return True
    m = re.search(r'Subject:.*?CN\s*=\s*([^,\n]+)', cert_text)
    if m and match_hostname(domain, m.group(1).strip()):
        return True
    return False

def score_tls(proto: str) -> int:
    p = (proto or "").lower()
    if "tlsv1.3" in p:
        return 20
    if "tlsv1.1" in p:
        return 10
    return 0

def score_days(days) -> int:
    try:
        d = int(days)
    except:
        return 0
    if d > 90:
        return 5
    if 30 <= d <= 90:
        return 3
    if 0 <= d < 30:
        return 1
    return 0

def score_cert_validation(host_ok: bool, chain_ok: bool) -> int:
    if host_ok and chain_ok:
        return 20
    if host_ok and not chain_ok:
        return 10
    return 0

with open(csv_file, encoding="utf-8-sig") as f, open(output_file, "w") as out:
    reader = csv.reader(f)
    for row in reader:
        if not row:
            continue
        domain = extract_domain_from_row(row)
        if not domain:
            continue
        info = get_info(domain)
        proto = info.get("Protocol", "-")
        days = info.get("DaysLeft", "-")
        cert_text = info.get("CertText", "")
        chain_ok = info.get("ChainTrusted", False)
        host_ok = hostname_matches(cert_text, domain)
        days_display = "expired" if isinstance(days, int) and days < 0 else str(days)
        tls_score = score_tls(proto)
        days_score = score_days(days)
        cert_score = score_cert_validation(host_ok, chain_ok)
        total = tls_score + days_score + cert_score
        out.write(f"---- {domain} ----\n")
        out.write(f"Protocol: {proto}\n")
        out.write(f"DaysLeft: {days_display}\n")
        out.write("SSL/TLS Certificate Validation : {\n")
        out.write(f"HostnameMatch: {str(host_ok)}\n")
        out.write(f"ChainTrusted: {str(chain_ok)}\n")
        out.write("}\n")
        out.write("---- Scoring Criteria ----\n")
        out.write(f"TLSScore: {tls_score}/20\n")
        out.write(f"DaysLeftScore: {days_score}/5\n")
        out.write(f"CertValidationScore: {cert_score}/20\n")
        out.write(f"TotalScore: {total}/100\n\n")