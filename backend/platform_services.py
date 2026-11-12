"""
platform_services.py - Modular security, ticketing, waitlist, wallet, TOTP 2FA,
and outgoing webhook utilities for Events Booking.
"""
import base64
import hashlib
import hmac
import io
import secrets
import struct
import threading
import time
import urllib.parse
from datetime import datetime, timedelta
import qrcode

# ---------------------------------------------------------------------------
# 1. Hardened SVG CAPTCHA Renderer
# ---------------------------------------------------------------------------

def generate_captcha_code(length=5):
    """Return a cryptographically random numeric string preserving leading zeros."""
    return "".join(str(secrets.randbelow(10)) for _ in range(length))


def render_captcha_svg(code):
    """Render an inline SVG CAPTCHA with digit rotation/jitter and decoy noise."""
    palette = ["#38bdf8", "#60a5fa", "#a78bfa", "#34d399", "#f472b6"]
    digits_svg = []
    for idx, ch in enumerate(str(code)):
        x = 20 + idx * 30 + (secrets.randbelow(5) - 2)
        y = 35 + (secrets.randbelow(9) - 4)
        angle = secrets.randbelow(29) - 14
        color = palette[secrets.randbelow(len(palette))]
        font_size = 24 + secrets.randbelow(5)
        digits_svg.append(
            f'<text x="{x}" y="{y}" fill="{color}" font-family="Courier New, monospace" '
            f'font-size="{font_size}" font-weight="800" '
            f'transform="rotate({angle} {x} {y - 8})">{ch}</text>'
        )

    lines_svg = []
    for _ in range(4):
        x1, y1 = secrets.randbelow(30), secrets.randbelow(54)
        cx, cy = 40 + secrets.randbelow(100), secrets.randbelow(54)
        x2, y2 = 140 + secrets.randbelow(40), secrets.randbelow(54)
        stroke = palette[secrets.randbelow(len(palette))]
        lines_svg.append(
            f'<path d="M {x1} {y1} Q {cx} {cy} {x2} {y2}" stroke="{stroke}" '
            f'stroke-opacity="0.38" stroke-width="1.6" fill="none"/>'
        )

    dots_svg = []
    for _ in range(18):
        dx = 6 + secrets.randbelow(168)
        dy = 6 + secrets.randbelow(42)
        r = 1 + (secrets.randbelow(2) * 0.5)
        dots_svg.append(
            f'<circle cx="{dx}" cy="{dy}" r="{r}" fill="#94a3b8" fill-opacity="0.35"/>'
        )

    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 180 54" width="180" height="54" '
        'role="img" aria-label="Security CAPTCHA challenge" '
        'style="display:block;max-width:100%;height:auto;border-radius:6px;">'
        '<defs><linearGradient id="capGrad" x1="0%" y1="0%" x2="100%" y2="100%">'
        '<stop offset="0%" stop-color="#090d16"/><stop offset="100%" stop-color="#111827"/>'
        '</linearGradient></defs>'
        '<rect width="180" height="54" rx="6" fill="url(#capGrad)"/>'
        + "".join(lines_svg)
        + "".join(dots_svg)
        + "".join(digits_svg)
        + "</svg>"
    )


# ---------------------------------------------------------------------------
# 2. Brute-Force Login Rate Limiter
# ---------------------------------------------------------------------------

_RATE_LOCK = threading.Lock()
_ACCOUNT_FAILURES = {}   # (ip, identifier_lower) -> {'timestamps': [...], 'locked_until': float}
_IP_FAILURES = {}        # ip -> {'timestamps': [...], 'locked_until': float}


def check_login_rate_limit(ip, identifier="", window_sec=600):
    """Return (allowed, retry_after_seconds) without mutating failure counters."""
    now = time.time()
    norm_id = (identifier or "").strip().lower()
    with _RATE_LOCK:
        if ip:
            ip_entry = _IP_FAILURES.get(ip)
            if ip_entry and ip_entry.get("locked_until", 0) > now:
                return False, max(1, int(ip_entry["locked_until"] - now) + 1)
        if norm_id:
            key = (ip or "unknown", norm_id)
            acc_entry = _ACCOUNT_FAILURES.get(key)
            if acc_entry and acc_entry.get("locked_until", 0) > now:
                return False, max(1, int(acc_entry["locked_until"] - now) + 1)
            if acc_entry:
                acc_entry["timestamps"] = [t for t in acc_entry["timestamps"] if now - t < window_sec]
    return True, 0


def record_login_failure(ip, identifier="", max_attempts=6, max_ip_attempts=30, window_sec=600, lockout_sec=60):
    """Record a failed login attempt and return (locked_now, retry_after_seconds)."""
    now = time.time()
    norm_id = (identifier or "").strip().lower()
    locked_after = 0
    with _RATE_LOCK:
        if ip:
            ip_entry = _IP_FAILURES.setdefault(ip, {"timestamps": [], "locked_until": 0.0})
            ip_entry["timestamps"] = [t for t in ip_entry["timestamps"] if now - t < window_sec]
            ip_entry["timestamps"].append(now)
            if len(ip_entry["timestamps"]) >= max_ip_attempts:
                ip_entry["locked_until"] = now + lockout_sec
                locked_after = max(locked_after, lockout_sec)

        if norm_id:
            key = (ip or "unknown", norm_id)
            acc_entry = _ACCOUNT_FAILURES.setdefault(key, {"timestamps": [], "locked_until": 0.0})
            acc_entry["timestamps"] = [t for t in acc_entry["timestamps"] if now - t < window_sec]
            acc_entry["timestamps"].append(now)
            if len(acc_entry["timestamps"]) >= max_attempts:
                acc_entry["locked_until"] = now + lockout_sec
                locked_after = max(locked_after, lockout_sec)

    return locked_after > 0, locked_after


def clear_login_failures(ip, identifier=""):
    """Reset failed login counter for (ip, identifier) after successful auth."""
    norm_id = (identifier or "").strip().lower()
    with _RATE_LOCK:
        if norm_id:
            _ACCOUNT_FAILURES.pop((ip or "unknown", norm_id), None)


def reset_all_login_rate_limits():
    """Clear all in-memory rate-limit buckets (for testing or admin reset)."""
    with _RATE_LOCK:
        _ACCOUNT_FAILURES.clear()
        _IP_FAILURES.clear()


# ---------------------------------------------------------------------------
# 3. RFC-6238 TOTP Two-Factor Authentication
# ---------------------------------------------------------------------------

def generate_totp_secret(num_bytes=20):
    """Generate a Base32 secret compatible with Authenticator apps."""
    raw = secrets.token_bytes(num_bytes)
    return base64.b32encode(raw).decode("ascii").rstrip("=")


def _decode_base32_secret(secret):
    clean = str(secret or "").strip().replace(" ", "").upper()
    pad_len = (-len(clean)) % 8
    return base64.b32decode(clean + ("=" * pad_len))


def get_totp_code(secret, for_time=None, interval=30, digits=6):
    """Compute RFC-6238 6-digit TOTP code for the given secret and UNIX time."""
    ts = int(time.time() if for_time is None else for_time)
    counter = ts // interval
    key = _decode_base32_secret(secret)
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code_int = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(code_int % (10 ** digits)).zfill(digits)


def verify_totp_code(secret, code, valid_window=1, interval=30, for_time=None):
    """Constant-time verification of a 6-digit TOTP code allowing +-valid_window drift."""
    clean_code = "".join(str(code or "").split())
    if not clean_code.isdigit() or len(clean_code) != 6 or not secret:
        return False
    base_ts = int(time.time() if for_time is None else for_time)
    matched = False
    for step in range(-valid_window, valid_window + 1):
        expected = get_totp_code(secret, for_time=base_ts + (step * interval), interval=interval)
        if hmac.compare_digest(clean_code, expected):
            matched = True
    return matched


def build_otpauth_uri(secret, account_name, issuer="Events Booking"):
    """Build standard otpauth://totp URI for QR scanning."""
    label = urllib.parse.quote(f"{issuer}:{account_name}")
    iss = urllib.parse.quote(issuer)
    return f"otpauth://totp/{label}?secret={secret}&issuer={iss}&algorithm=SHA1&digits=6&period=30"


def generate_qr_data_uri(payload_text):
    """Return a data:image/png;base64 URI encoding payload_text."""
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=5, border=2)
    qr.add_data(payload_text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def generate_backup_codes(count=8):
    """Generate single-use uppercase alphanumeric recovery codes (XXXX-XXXX)."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    codes = []
    for _ in range(count):
        part1 = "".join(secrets.choice(alphabet) for _ in range(4))
        part2 = "".join(secrets.choice(alphabet) for _ in range(4))
        codes.append(f"{part1}-{part2}")
    return codes


# ---------------------------------------------------------------------------
# 4. Pricing, Refund Tiers, Recurrence & Webhooks
# ---------------------------------------------------------------------------

def parse_event_price_numeric(price_val):
    """Parse ticket price string like '₹800', '₹1,200', or 'Free' into float."""
    if price_val is None:
        return 0.0
    if isinstance(price_val, (int, float)):
        return max(0.0, float(price_val))
    raw = str(price_val).strip().lower()
    if not raw or raw == "free":
        return 0.0
    cleaned = "".join(ch for ch in raw if ch.isdigit() or ch == ".")
    try:
        return max(0.0, float(cleaned)) if cleaned else 0.0
    except ValueError:
        return 0.0


def _parse_event_start_datetime(event_dict):
    date_raw = str(event_dict.get("date") or "").strip()
    time_raw = str(event_dict.get("time") or "10:00 AM").strip()
    parsed_date = None
    for fmt in ("%b %d, %Y", "%d %b %Y", "%Y-%m-%d", "%B %d, %Y"):
        try:
            parsed_date = datetime.strptime(date_raw, fmt).date()
            break
        except ValueError:
            pass
    if not parsed_date:
        return None
    for tfmt in ("%I:%M %p", "%H:%M"):
        try:
            t = datetime.strptime(time_raw, tfmt).time()
            return datetime.combine(parsed_date, t)
        except ValueError:
            pass
    return datetime.combine(parsed_date, datetime.min.time())


def calculate_event_ticket_refund(event_dict, amount_paid, ref_now=None):
    """Compute tiered wallet refund for cancelling a paid event registration."""
    paid = max(0.0, float(amount_paid or 0.0))
    policy = str((event_dict or {}).get("refund_policy") or "flexible").strip().lower()
    if policy not in ("flexible", "moderate", "strict"):
        policy = "flexible"

    if paid <= 0:
        return {
            "eligible": False,
            "refund_percent": 0,
            "refund_amount": 0.0,
            "policy": policy,
            "reason": "Free pass — no payment refund applicable."
        }

    if policy == "strict":
        return {
            "eligible": False,
            "refund_percent": 0,
            "refund_amount": 0.0,
            "policy": policy,
            "reason": "Strict non-refundable ticket policy for this event."
        }

    now = ref_now or datetime.now()
    start_dt = _parse_event_start_datetime(event_dict or {})
    if not start_dt:
        # Safe fallback when custom date cannot be parsed
        hours_until = 200.0
    else:
        hours_until = (start_dt - now).total_seconds() / 3600.0

    if hours_until <= 0:
        return {
            "eligible": False,
            "refund_percent": 0,
            "refund_amount": 0.0,
            "policy": policy,
            "reason": "Event has already started or ended."
        }

    if policy == "flexible":
        if hours_until >= 168:  # > 7 days
            pct = 100
            reason = "Flexible policy: 100% refund (> 7 days before event)."
        elif hours_until >= 48:
            pct = 50
            reason = "Flexible policy: 50% refund (48h–7 days before event)."
        else:
            pct = 0
            reason = "Flexible policy cutoff passed (< 48 hours before event)."
    else:  # moderate
        if hours_until >= 336:  # > 14 days
            pct = 100
            reason = "Moderate policy: 100% refund (> 14 days before event)."
        elif hours_until >= 168:  # > 7 days
            pct = 50
            reason = "Moderate policy: 50% refund (7–14 days before event)."
        else:
            pct = 0
            reason = "Moderate policy cutoff passed (< 7 days before event)."

    refund_amt = round(paid * (pct / 100.0), 2)
    return {
        "eligible": refund_amt > 0,
        "refund_percent": pct,
        "refund_amount": refund_amt,
        "policy": policy,
        "reason": reason
    }


def generate_occurrence_dates(start_date_str, rule="weekly", count=4):
    """Generate formatted 'MMM DD, YYYY' dates for recurring event series."""
    count = max(1, min(int(count or 1), 12))
    base_date = None
    for fmt in ("%b %d, %Y", "%d %b %Y", "%Y-%m-%d", "%B %d, %Y"):
        try:
            base_date = datetime.strptime(str(start_date_str).strip(), fmt).date()
            break
        except ValueError:
            pass
    if not base_date:
        return [str(start_date_str).strip()]

    rule_norm = str(rule or "weekly").strip().lower()
    dates = []
    for idx in range(count):
        if rule_norm == "biweekly":
            dt = base_date + timedelta(days=14 * idx)
        elif rule_norm == "monthly":
            # Approximate month step keeping day valid
            month = (base_date.month - 1) + idx
            year = base_date.year + (month // 12)
            month = (month % 12) + 1
            day = min(base_date.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
            dt = base_date.replace(year=year, month=month, day=day)
        else:
            dt = base_date + timedelta(days=7 * idx)
        dates.append(dt.strftime("%b %d, %Y"))
    return dates


def sign_webhook_payload(secret_key, payload_bytes):
    """Compute HMAC-SHA256 signature header for outgoing host webhooks."""
    digest = hmac.new(str(secret_key or "").encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    return f"sha256={digest}"

