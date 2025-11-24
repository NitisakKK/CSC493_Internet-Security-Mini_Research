import csv, subprocess, re, socket
import os
from urllib.parse import urlsplit
from datetime import datetime, UTC

os.environ.setdefault("LANG", "C.UTF-8")
os.environ.setdefault("LC_ALL", "C.UTF-8")

csv_file = "websites.csv"
output_file = "output.txt"

def _run(cmd, t=8):
    try:
        return subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=t
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(args=cmd, returncode=124, stdout="", stderr="TIMEOUT")

def _resolve_ipv4(domain):
    try:
        infos = socket.getaddrinfo(domain, 443, family=socket.AF_INET, type=socket.SOCK_STREAM)
        return infos[0][4][0]
    except:
        return None

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
        host = host.split('@')[-1].split(':')[0].strip()
        if host and '.' in host:
            return host
    return None

def get_info(domain):
    ip = _resolve_ipv4(domain)
    target = f"{ip}:443" if ip else f"{domain}:443"
    base = f'echo | openssl s_client -connect {target} -servername {domain}'
    res = _run(base + ' 2>&1', 8)
    if "BEGIN CERTIFICATE" not in res.stdout:
        return {"Protocol": "-", "DaysLeft": "-", "CertText": "", "ChainTrusted": False}
    proto_m = re.search(r'Protocol\s*:\s*([A-Za-z0-9\.\-]+)', res.stdout)
    proto = proto_m.group(1) if proto_m else "-"
    cert_text = _run(base + ' 2>&1 | openssl x509 -text -noout', 8).stdout
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
    verify_out = _run(base + ' -verify_return_error 2>&1', 8).stdout
    vr_m = re.search(r'Verify return code:\s*(\d+)', verify_out)
    chain_trusted = (vr_m and vr_m.group(1) == "0")
    return {"Protocol": proto, "DaysLeft": days_left, "CertText": cert_text, "ChainTrusted": chain_trusted}

def to_idna(h):
    try:
        return h.encode("idna").decode("ascii")
    except:
        return h.lower()

def is_ip(host):
    if re.fullmatch(r'\d{1,3}(?:\.\d{1,3}){3}', host):
        return True
    if re.fullmatch(r'\[?[0-9A-Fa-f:]+\]?', host):
        return True
    return False

def match_hostname(domain: str, pattern: str) -> bool:
    d = to_idna(domain.strip().lower())
    p = to_idna(pattern.strip().lower())
    if is_ip(d):
        return d.strip("[]") == p.strip("[]")
    if p.startswith("*."):
        suffix = p[1:]
        if not d.endswith(suffix):
            return False
        left = d[: -len(suffix)]
        return left.count(".") == 1 and left.endswith(".")
    return d == p

def hostname_matches(cert_text: str, domain: str) -> bool:
    for name in re.findall(r'DNS:([^,\s]+)', cert_text):
        if match_hostname(domain, name.strip()):
            return True
    for ip in re.findall(r'IP Address:([0-9A-Fa-f:\.\[\]]+)', cert_text):
        if match_hostname(domain, ip.strip()):
            return True
    m = re.search(r'Subject:.*?CN\s*=\s*([^,\n]+)', cert_text)
    if m and match_hostname(domain, m.group(1).strip()):
        return True
    return False

def score_tls(proto: str) -> int:
    p = (proto or "").lower()
    if "tlsv1.3" in p:
        return 20
    if "tlsv1.2" in p:
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

def get_http_headers(domain):
    head = _run(f'curl -s -D - -o /dev/null -L -I --max-redirs 5 --connect-timeout 4 -m 8 https://{domain}', 10).stdout
    def latest(h):
        m = re.findall(rf'(?im)^{h}:\s*(.+)$', head)
        return m[-1].strip() if m else "none"
    hsts = latest("strict-transport-security")
    xct  = latest("x-content-type-options")
    csp  = latest("content-security-policy")
    if csp == "none":
        csp_ro = latest("content-security-policy-report-only")
        if csp_ro != "none":
            csp = csp_ro + " (report-only)"
    if csp == "none":
        body = _run(f'curl -sL --max-redirs 5 --connect-timeout 4 -m 8 https://{domain}', 10).stdout[:200000]
        meta = re.search(r'(?is)<meta[^>]+http-equiv=["\']Content-Security-Policy["\'][^>]*content=["\']([^"\']+)["\']', body)
        if meta:
            csp = meta.group(1).strip() + " (meta)"
    cookies = re.findall(r'(?im)^set-cookie:\s*(.+)$', head)
    return {"HSTS": hsts, "CSP": csp, "XCTO": xct, "SetCookies": cookies}

def score_hsts(hsts_value: str) -> int:
    if not hsts_value or hsts_value.lower() == "none":
        return 0
    m = re.search(r'max-age\s*=\s*(\d+)', hsts_value, re.I)
    if not m:
        return 10
    return 15 if int(m.group(1)) >= 15552000 else 10

def score_csp(csp_value: str) -> int:
    if not csp_value or csp_value.strip().lower() == "none":
        return 0
    csp_core = csp_value.split(" (", 1)[0].strip().lower()
    m = re.search(r'(^|;)\s*script-src(?:-elem)?\s+([^;]+)', csp_core)
    if not m:
        return 5
    tokens = [t for t in re.split(r'\s+', m.group(2).strip()) if t]
    tokset = set(tokens)
    if "'none'" in tokset:
        return 20
    has_unsafe = ("'unsafe-inline'" in tokset) or ("'unsafe-eval'" in tokset)
    has_scheme_or_wild = any(t in ("*", "http:", "https:", "data:", "blob:", "filesystem:", "mediastream:") for t in tokens)
    has_wildcard_domain = any(t.startswith("*.") for t in tokens if not t.endswith(":"))
    weaknesses = has_unsafe or has_scheme_or_wild or has_wildcard_domain
    return 20 if not weaknesses else 12

def score_xcto(xcto_value: str) -> int:
    return 5 if xcto_value and "nosniff" in xcto_value.lower() else 0

def score_cookie_flags(cookies: list) -> int:
    if not cookies:
        return 15
    any_missing_secure = False
    any_missing_other = False
    for c in cookies:
        c_low = c.lower()
        has_secure = bool(re.search(r'\bsecure\b', c_low))
        has_httponly = bool(re.search(r'\bhttponly\b', c_low))
        m_ss = re.search(r'\bsamesite\s*=\s*(strict|lax|none)\b', c_low)
        samesite = m_ss.group(1) if m_ss else None
        appropriate_ss = samesite in ("lax", "strict")
        if not has_secure:
            any_missing_secure = True
        if (not has_httponly) or (not appropriate_ss):
            any_missing_other = True
    if any_missing_secure:
        return 0
    if any_missing_other:
        return 8
    return 15

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
        headers = get_http_headers(domain)
        days_display = "expired" if isinstance(days, int) and days < 0 else str(days)
        tls_score = score_tls(proto)
        days_score = score_days(days)
        cert_score = score_cert_validation(host_ok, chain_ok)
        hsts_score = score_hsts(headers["HSTS"])
        csp_score = score_csp(headers["CSP"])
        xcto_score = score_xcto(headers["XCTO"])
        cookie_score = score_cookie_flags(headers["SetCookies"])
        total = tls_score + days_score + cert_score + hsts_score + csp_score + xcto_score + cookie_score
        out.write(f"---- {domain} ----\n")
        out.write(f"Protocol: {proto}\n")
        out.write(f"DaysLeft: {days_display}\n")
        out.write("SSL/TLS Certificate Validation : {\n")
        out.write(f"HostnameMatch: {str(host_ok)}\n")
        out.write(f"ChainTrusted: {str(chain_ok)}\n")
        out.write("}\n")
        out.write("HTTP Security Headers : {\n")
        out.write(f"HSTS: {headers['HSTS']}\n")
        out.write(f"CSP: {headers['CSP']}\n")
        out.write(f"X-Content-Type-Options: {headers['XCTO']}\n")
        out.write(f"Set-Cookie Count: {len(headers['SetCookies'])}\n")
        out.write("}\n")
        out.write("---- Scoring Criteria ----\n")
        out.write(f"TLSScore: {tls_score}/20\n")
        out.write(f"DaysLeftScore: {days_score}/5\n")
        out.write(f"CertValidationScore: {cert_score}/20\n")
        out.write(f"HSTSScore: {hsts_score}/15\n")
        out.write(f"CSPScore: {csp_score}/20\n")
        out.write(f"XContentTypeOptionsScore: {xcto_score}/5\n")
        out.write(f"CookieFlagsScore: {cookie_score}/15\n")
        out.write(f"TotalScore: {total}/100\n\n")