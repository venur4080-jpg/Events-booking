"""
backend/subscription_service.py
Enterprise Subscription Management Engine for Events Booking System.
Provides complete subscription plans, checkout verification, order summaries,
dynamic refund calculations, feature access controls, invoice generation,
auto-renewal management, and background expiry worker.
"""

import os
import re
import io
import json
import random
import string
import hashlib
import hmac
from datetime import datetime, timedelta
from fpdf import FPDF
import qrcode

# ─────────────────────────────────────────────────────────────────────────────
# 1. SUBSCRIPTION PLANS & FEATURE CONFIGURATIONS
# ─────────────────────────────────────────────────────────────────────────────

SUBSCRIPTION_PLANS = {
    'normal': {
        'id': 'normal',
        'title': 'Normal Pack',
        'badge': '💎 Normal Pack',
        'tagline': 'Essential Stage Pass for Live Streams & Events',
        'monthly_price': 149.0,
        'yearly_price': 899.0,
        'yearly_saving_pct': 50,
        'effective_monthly_yearly': 75.0,
        'max_quality': '720p',
        'quality_label': '720p HD (1080p locked)',
        'max_screens': 1,
        'max_event_price_inr': 1000.0,
        'includes_free_up_to': 1000.0,
        'monthly_events_limit': 15,
        'is_featured': False,
        'is_recommended': False,
        'multi_camera': False,
        'vip_crown_badge': False,
        'priority_qa': False,
        'ad_free': True,
        'offline_downloads': True,
        'free_trial_days': 7,
        'features': [
            '1 Screen / Device at a time',
            '720p HD Video Quality (No buffering)',
            'Watch all live events up to ₹1,000 for FREE',
            'Standard Live Stage Chat & Audience Reactions',
            'Interactive Q&A Audience Voting',
            'Zero Commercial Ad Breaks',
            'Downloadable Event Completion Pass'
        ]
    },
    'super': {
        'id': 'super',
        'title': 'Super Pack',
        'badge': '👑 Super VIP',
        'tagline': 'Unlimited Full HD & 2K QHD Live Stage VIP Pass',
        'monthly_price': 299.0,
        'yearly_price': 1499.0,
        'yearly_saving_pct': 58,
        'effective_monthly_yearly': 125.0,
        'max_quality': '2k',
        'quality_label': '1080p FHD & 2K QHD Ultra',
        'max_screens': 2,
        'max_event_price_inr': None,  # Unlimited free access
        'includes_free_up_to': None,  # Unlimited free access
        'monthly_events_limit': 999999,
        'is_featured': True,
        'is_recommended': True,
        'multi_camera': True,
        'vip_crown_badge': True,
        'priority_qa': True,
        'ad_free': True,
        'offline_downloads': True,
        'free_trial_days': 0,
        'features': [
            '2 Screens / Devices at a time',
            '1080p Full HD & Ultra 2K QHD Resolution',
            'ALL Live Events included for FREE (Even > ₹1,000!)',
            '👑 VIP Crown Badge in Live Chat & Event Rosters',
            'Multi-Camera Dashcam & Backstage Feeds',
            'Dolby Digital Atmospheric Stage Audio',
            'Priority Live Q&A Question Highlighting',
            'Zero Stream Commercials & Ad Interruptions',
            'VIP Fast-Track Check-In Pass'
        ]
    }
}

TIER_LIMITS = {
    'free': {
        'max_quality': '480p',
        'included_event_price_max': 0.0,
        'multi_camera': False,
        'vip_crown_badge': False,
        'priority_qa': False,
        'ad_free': False,
        'max_screens': 1,
        'monthly_events_limit': 3,
        'downloads_allowed': False
    },
    'normal': {
        'max_quality': '720p',
        'included_event_price_max': 1000.0,
        'multi_camera': False,
        'vip_crown_badge': False,
        'priority_qa': False,
        'ad_free': True,
        'max_screens': 1,
        'monthly_events_limit': 15,
        'downloads_allowed': True
    },
    'super': {
        'max_quality': '2k',
        'included_event_price_max': 999999.0,
        'multi_camera': True,
        'vip_crown_badge': True,
        'priority_qa': True,
        'ad_free': True,
        'max_screens': 2,
        'monthly_events_limit': 999999,
        'downloads_allowed': True
    }
}

DEFAULT_COUPONS = [
    {
        'code': 'SAVE20',
        'discount_type': 'percent',
        'discount_val': 20.0,
        'max_discount': 500.0,
        'min_amount': 100.0,
        'applicable_plan': 'all',
        'applicable_cycle': 'all',
        'max_uses': 5000,
        'description': '20% discount on all subscription packs'
    },
    {
        'code': 'WELCOME50',
        'discount_type': 'percent',
        'discount_val': 50.0,
        'max_discount': 150.0,
        'min_amount': 140.0,
        'applicable_plan': 'all',
        'applicable_cycle': 'monthly',
        'max_uses': 2000,
        'description': '50% off on your first monthly subscription'
    },
    {
        'code': 'SUPER100',
        'discount_type': 'flat',
        'discount_val': 100.0,
        'max_discount': 100.0,
        'min_amount': 800.0,
        'applicable_plan': 'super',
        'applicable_cycle': 'yearly',
        'max_uses': 1000,
        'description': '₹100 flat discount on Super Pack Annual Pass'
    },
    {
        'code': 'FESTIVE30',
        'discount_type': 'percent',
        'discount_val': 30.0,
        'max_discount': 600.0,
        'min_amount': 800.0,
        'applicable_plan': 'all',
        'applicable_cycle': 'yearly',
        'max_uses': 3000,
        'description': 'Festive Special: 30% discount on any Annual plan'
    }
]

# ─────────────────────────────────────────────────────────────────────────────
# 2. DATABASE INITIALIZATION & MIGRATIONS
# ─────────────────────────────────────────────────────────────────────────────

def init_subscription_db(conn):
    """
    Safely migrates and initializes all tables and columns needed for the
    Subscription Management Module.
    """
    c = conn.cursor()

    # 1. Ensure subscriptions table exists
    c.execute('''CREATE TABLE IF NOT EXISTS subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        plan_type TEXT NOT NULL,
        billing_cycle TEXT NOT NULL,
        price_paid REAL NOT NULL,
        max_quality TEXT NOT NULL DEFAULT '720p',
        max_event_price_inr REAL,
        max_screens INTEGER DEFAULT 1,
        status TEXT DEFAULT 'active',
        started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        expires_at DATETIME NOT NULL,
        payment_id TEXT DEFAULT '',
        payment_method TEXT DEFAULT 'UPI',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    # Safe column additions on subscriptions table
    sub_cols = [
        ("ALTER TABLE subscriptions ADD COLUMN auto_renew INTEGER DEFAULT 1",),
        ("ALTER TABLE subscriptions ADD COLUMN cancellation_reason TEXT DEFAULT ''",),
        ("ALTER TABLE subscriptions ADD COLUMN cancellation_feedback TEXT DEFAULT ''",),
        ("ALTER TABLE subscriptions ADD COLUMN cancelled_at DATETIME",),
        ("ALTER TABLE subscriptions ADD COLUMN cancel_type TEXT DEFAULT ''",),
        ("ALTER TABLE subscriptions ADD COLUMN refund_amount REAL DEFAULT 0.0",),
        ("ALTER TABLE subscriptions ADD COLUMN refund_status TEXT DEFAULT 'none'",),
        ("ALTER TABLE subscriptions ADD COLUMN refund_id TEXT DEFAULT ''",),
        ("ALTER TABLE subscriptions ADD COLUMN refund_reason TEXT DEFAULT ''",),
        ("ALTER TABLE subscriptions ADD COLUMN refunded_at DATETIME",),
        ("ALTER TABLE subscriptions ADD COLUMN is_trial INTEGER DEFAULT 0",),
        ("ALTER TABLE subscriptions ADD COLUMN trial_ends_at DATETIME",),
        ("ALTER TABLE subscriptions ADD COLUMN grace_period_ends_at DATETIME",),
        ("ALTER TABLE subscriptions ADD COLUMN reminded_7d INTEGER DEFAULT 0",),
        ("ALTER TABLE subscriptions ADD COLUMN reminded_3d INTEGER DEFAULT 0",),
        ("ALTER TABLE subscriptions ADD COLUMN reminded_1d INTEGER DEFAULT 0",),
        ("ALTER TABLE subscriptions ADD COLUMN reminded_0d INTEGER DEFAULT 0",),
        ("ALTER TABLE subscriptions ADD COLUMN invoice_number TEXT DEFAULT ''",),
        ("ALTER TABLE subscriptions ADD COLUMN tax_amount REAL DEFAULT 0.0",),
        ("ALTER TABLE subscriptions ADD COLUMN discount_amount REAL DEFAULT 0.0",),
        ("ALTER TABLE subscriptions ADD COLUMN coupon_code TEXT DEFAULT ''",),
        ("ALTER TABLE users ADD COLUMN trial_used INTEGER DEFAULT 0",),
        ("ALTER TABLE users ADD COLUMN cancellation_count INTEGER DEFAULT 0",),
        ("ALTER TABLE users ADD COLUMN is_banned INTEGER DEFAULT 0",),
        ("ALTER TABLE users ADD COLUMN ban_reason TEXT DEFAULT ''",),
        ("ALTER TABLE users ADD COLUMN banned_at DATETIME",),
    ]
    for statement in sub_cols:
        try:
            c.execute(statement[0])
        except Exception:
            pass

    # 2. Subscription Payments Audit Table
    c.execute('''CREATE TABLE IF NOT EXISTS subscription_payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subscription_id INTEGER,
        username TEXT NOT NULL,
        order_id TEXT,
        payment_id TEXT UNIQUE,
        plan_type TEXT NOT NULL,
        billing_cycle TEXT NOT NULL,
        amount REAL NOT NULL,
        tax_amount REAL DEFAULT 0.0,
        discount_amount REAL DEFAULT 0.0,
        coupon_code TEXT DEFAULT '',
        currency TEXT DEFAULT 'INR',
        payment_method TEXT DEFAULT 'Razorpay',
        payment_status TEXT DEFAULT 'success',
        invoice_number TEXT DEFAULT '',
        receipt_url TEXT DEFAULT '',
        error_message TEXT DEFAULT '',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    # 3. Subscription Refunds Table
    c.execute('''CREATE TABLE IF NOT EXISTS subscription_refunds (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subscription_id INTEGER NOT NULL,
        username TEXT NOT NULL,
        payment_id TEXT,
        amount REAL NOT NULL,
        reason TEXT,
        status TEXT DEFAULT 'processed',
        gateway_refund_id TEXT DEFAULT '',
        processed_by TEXT DEFAULT 'system',
        notes TEXT DEFAULT '',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    # 4. Subscription Coupons Table
    c.execute('''CREATE TABLE IF NOT EXISTS subscription_coupons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        discount_type TEXT NOT NULL DEFAULT 'percent',
        discount_val REAL NOT NULL,
        max_discount REAL DEFAULT 0.0,
        min_amount REAL DEFAULT 0.0,
        applicable_plan TEXT DEFAULT 'all',
        applicable_cycle TEXT DEFAULT 'all',
        valid_until DATETIME,
        max_uses INTEGER DEFAULT 1000,
        times_used INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1,
        description TEXT DEFAULT '',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    # 5. Subscription Feature Usage Table
    c.execute('''CREATE TABLE IF NOT EXISTS subscription_usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        subscription_id INTEGER,
        feature_name TEXT NOT NULL,
        usage_count INTEGER DEFAULT 1,
        last_used DATETIME DEFAULT CURRENT_TIMESTAMP,
        metadata TEXT DEFAULT '{}'
    )''')

    # Populate default coupons if table is empty
    c.execute("SELECT COUNT(*) FROM subscription_coupons")
    if c.fetchone()[0] == 0:
        expiry = (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d %H:%M:%S')
        for cp in DEFAULT_COUPONS:
            c.execute("""
                INSERT OR IGNORE INTO subscription_coupons 
                (code, discount_type, discount_val, max_discount, min_amount, applicable_plan, applicable_cycle, valid_until, max_uses, times_used, is_active, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 1, ?)
            """, (cp['code'], cp['discount_type'], cp['discount_val'], cp['max_discount'], cp['min_amount'],
                  cp['applicable_plan'], cp['applicable_cycle'], expiry, cp['max_uses'], cp['description']))

    # Create composite indexes
    for idx in [
        "CREATE INDEX IF NOT EXISTS idx_subs_user_status ON subscriptions(username, status);",
        "CREATE INDEX IF NOT EXISTS idx_subs_expires_at ON subscriptions(expires_at);",
        "CREATE INDEX IF NOT EXISTS idx_sub_pay_user ON subscription_payments(username);",
        "CREATE INDEX IF NOT EXISTS idx_sub_pay_order ON subscription_payments(order_id);",
        "CREATE INDEX IF NOT EXISTS idx_sub_refunds_sub ON subscription_refunds(subscription_id);",
        "CREATE INDEX IF NOT EXISTS idx_sub_coupons_code ON subscription_coupons(code);",
        "CREATE INDEX IF NOT EXISTS idx_sub_usage_user ON subscription_usage(username, feature_name);",
    ]:
        try:
            c.execute(idx)
        except Exception:
            pass

    conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# 3. CORE SUBSCRIPTION HELPERS & STATUS CHECKERS
# ─────────────────────────────────────────────────────────────────────────────

def parse_iso_datetime(dt_str):
    if not dt_str:
        return None
    s = str(dt_str).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass
    try:
        return datetime.fromisoformat(s.replace(' ', 'T'))
    except Exception:
        return None

def get_user_subscription(username, get_db_fn, include_grace=True):
    """
    Fetches the current active or grace-period subscription for the given user.
    Handles automatic expiration transitions and grace-period status detection.
    """
    if not username:
        return None
    try:
        conn = get_db_fn(row_factory=True)
        c = conn.cursor()
        c.execute("""
            SELECT id, username, plan_type, billing_cycle, price_paid, max_quality, 
                   max_event_price_inr, max_screens, status, started_at, expires_at, 
                   payment_id, payment_method, auto_renew, cancellation_reason, cancellation_feedback,
                   cancelled_at, cancel_type, refund_amount, refund_status, is_trial,
                   trial_ends_at, grace_period_ends_at, invoice_number, tax_amount, discount_amount, coupon_code
            FROM subscriptions 
            WHERE username = ?
              AND (
                  (status = 'active')
                  OR (status = 'cancelled' AND (cancel_type = 'end_of_period' OR cancel_type = ''))
                  OR (status = 'in_grace_period')
              )
            ORDER BY id DESC LIMIT 1
        """, (username,))
        row = c.fetchone()
        conn.close()

        if not row:
            return None

        d = dict(row)
        plan_meta = SUBSCRIPTION_PLANS.get(d['plan_type'], SUBSCRIPTION_PLANS['normal'])
        d['plan_title'] = plan_meta.get('title', d['plan_type'].capitalize())
        d['badge'] = plan_meta.get('badge', d['plan_type'])
        d['quality_label'] = plan_meta.get('quality_label', d['max_quality'])
        d['features'] = plan_meta.get('features', [])
        d['is_recommended'] = plan_meta.get('is_recommended', False)

        now = datetime.now()
        exp_dt = parse_iso_datetime(d.get('expires_at'))
        start_dt = parse_iso_datetime(d.get('started_at')) or (exp_dt - timedelta(days=30) if exp_dt else now)

        if not exp_dt:
            d['days_left'] = 30
            d['is_active'] = True
            d['is_expired'] = False
            d['in_grace_period'] = False
            d['progress_pct'] = 50
            return d

        total_days = max(1, (exp_dt - start_dt).days)
        elapsed_days = max(0, (now - start_dt).days)
        days_left = max(0, (exp_dt - now).days)
        seconds_left = (exp_dt - now).total_seconds()

        d['days_left'] = days_left
        d['total_days'] = total_days
        d['progress_pct'] = min(100, max(0, int((elapsed_days / total_days) * 100)))

        # Grace period check (3 days after expires_at)
        grace_limit = exp_dt + timedelta(days=3)
        current_status = (d.get('status') or 'active').lower()

        if current_status == 'active':
            if seconds_left > 0:
                d['is_active'] = True
                d['is_expired'] = False
                d['in_grace_period'] = False
                return d
            elif now <= grace_limit and include_grace:
                # In 3-day grace period
                d['is_active'] = True
                d['is_expired'] = False
                d['in_grace_period'] = True
                d['status'] = 'in_grace_period'
                d['days_left'] = 0
                return d
            else:
                # Expired past grace period
                _mark_subscription_expired(d['id'], get_db_fn)
                d['is_active'] = False
                d['is_expired'] = True
                d['in_grace_period'] = False
                d['status'] = 'expired'
                return None
        elif current_status in ('cancelled', 'in_grace_period'):
            if current_status == 'cancelled' and d.get('cancel_type') == 'immediate':
                d['is_active'] = False
                d['is_expired'] = True
                d['in_grace_period'] = False
                return None
            if seconds_left > 0:
                d['is_active'] = True
                d['is_expired'] = False
                d['in_grace_period'] = False
                return d
            elif now <= grace_limit and include_grace:
                d['is_active'] = True
                d['is_expired'] = False
                d['in_grace_period'] = True
                return d
            else:
                d['is_active'] = False
                d['is_expired'] = True
                d['in_grace_period'] = False
                return None
        else:
            d['is_active'] = False
            d['is_expired'] = True
            d['in_grace_period'] = False
            return None

    except Exception as e:
        print(f"[SUBSCRIPTION SERVICE FETCH ERROR] {e}")
        return None

def _mark_subscription_expired(sub_id, get_db_fn):
    try:
        conn = get_db_fn()
        c = conn.cursor()
        c.execute("UPDATE subscriptions SET status = 'expired' WHERE id = ? AND status = 'active'", (sub_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[ERROR MARKING SUB EXPIRED] {e}")

def get_user_subscription_status(username, get_db_fn):
    """
    Returns full status dictionary including active sub, historical latest sub,
    and recommended popup prompt triggers.
    """
    active_sub = get_user_subscription(username, get_db_fn, include_grace=True)
    if active_sub:
        return {
            'has_active': True,
            'status': active_sub.get('status', 'active'),
            'subscription': active_sub,
            'plan_type': active_sub.get('plan_type'),
            'billing_cycle': active_sub.get('billing_cycle'),
            'in_grace_period': active_sub.get('in_grace_period', False),
            'days_left': active_sub.get('days_left', 0),
            'popup_trigger': 'in_grace_period' if active_sub.get('in_grace_period') else None
        }

    # If no active sub, check latest historical sub
    latest_sub = None
    try:
        conn = get_db_fn(row_factory=True)
        c = conn.cursor()
        c.execute("""
            SELECT id, username, plan_type, billing_cycle, price_paid, max_quality, 
                   status, started_at, expires_at, payment_id, refund_status
            FROM subscriptions WHERE username = ? ORDER BY id DESC LIMIT 1
        """, (username,))
        row = c.fetchone()
        conn.close()
        if row:
            latest_sub = dict(row)
            plan_meta = SUBSCRIPTION_PLANS.get(latest_sub['plan_type'], SUBSCRIPTION_PLANS['normal'])
            latest_sub['plan_title'] = plan_meta.get('title', latest_sub['plan_type'].capitalize())
    except Exception:
        pass

    popup_trigger = None
    if latest_sub:
        popup_trigger = 'expired'
    else:
        popup_trigger = 'login_unsubscribed'

    return {
        'has_active': False,
        'status': latest_sub.get('status', 'none') if latest_sub else 'none',
        'subscription': None,
        'latest_sub': latest_sub,
        'plan_type': 'free',
        'billing_cycle': None,
        'in_grace_period': False,
        'days_left': 0,
        'popup_trigger': popup_trigger
    }

def get_user_subscription_history(username, get_db_fn):
    """Returns a list of all subscriptions held by the user ordered newest first."""
    if not username:
        return []
    try:
        conn = get_db_fn(row_factory=True)
        c = conn.cursor()
        c.execute("""
            SELECT id, username, plan_type, billing_cycle, price_paid, max_quality, 
                   status, started_at, expires_at, payment_id, payment_method, 
                   auto_renew, cancelled_at, cancel_type, refund_amount, refund_status,
                   invoice_number, tax_amount, discount_amount, coupon_code
            FROM subscriptions 
            WHERE username = ?
            ORDER BY id DESC
        """, (username,))
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        for r in rows:
            plan_meta = SUBSCRIPTION_PLANS.get(r['plan_type'], {})
            r['plan_title'] = plan_meta.get('title', r['plan_type'].capitalize())
            r['badge'] = plan_meta.get('badge', r['plan_type'])
        return rows
    except Exception as e:
        print(f"[SUB HISTORY ERROR] {e}")
        return []

def get_user_payment_history(username, get_db_fn):
    """Returns all payment transactions recorded for this user."""
    if not username:
        return []
    try:
        conn = get_db_fn(row_factory=True)
        c = conn.cursor()
        c.execute("""
            SELECT id, subscription_id, username, order_id, payment_id, plan_type,
                   billing_cycle, amount, tax_amount, discount_amount, coupon_code,
                   currency, payment_method, payment_status, invoice_number, created_at
            FROM subscription_payments
            WHERE username = ?
            ORDER BY id DESC
        """, (username,))
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        for r in rows:
            plan_meta = SUBSCRIPTION_PLANS.get(r['plan_type'], {})
            r['plan_title'] = plan_meta.get('title', r['plan_type'].capitalize())
        return rows
    except Exception as e:
        print(f"[SUB PAYMENTS ERROR] {e}")
        return []


# ─────────────────────────────────────────────────────────────────────────────


def calculate_monthly_upgrade_credit(current_sub):
    """
    Calculates upgrade discount/credit when an active monthly subscriber upgrades to an annual plan.
    Credits the price paid for the active monthly plan towards the annual plan.
    """
    if not current_sub or not current_sub.get('is_active'):
        return 0.0
    if current_sub.get('billing_cycle') != 'monthly':
        return 0.0
    price_paid = float(current_sub.get('price_paid', 0.0))
    return round(price_paid, 2)

def get_annual_cancellation_eligibility(sub_dict, current_time=None):
    """
    Calculates the 7-calendar-day cancellation with refund eligibility
    for an active Annual subscription based on the original purchase timestamp.
    """
    if not sub_dict or sub_dict.get('billing_cycle') != 'yearly':
        return {
            'is_annual': False,
            'is_eligible': False,
            'remaining_str': 'Not an annual subscription',
            'days_remaining': 0,
            'hours_remaining': 0,
            'elapsed_days': 0,
            'elapsed_seconds': 0
        }

    now = current_time or datetime.now()
    purchase_str = sub_dict.get('started_at') or sub_dict.get('created_at')
    purchase_dt = parse_iso_datetime(purchase_str) or now

    elapsed_seconds = max(0.0, (now - purchase_dt).total_seconds())
    elapsed_days = int(elapsed_seconds / 86400.0)
    seven_days_seconds = 7.0 * 86400.0

    import math
    is_eligible = elapsed_seconds <= seven_days_seconds
    remaining_seconds = max(0.0, seven_days_seconds - elapsed_seconds)
    days_remaining = int(math.ceil(remaining_seconds / 86400.0)) if is_eligible and remaining_seconds > 0 else 0
    hours_remaining = max(1, int(math.ceil(remaining_seconds / 3600.0))) if is_eligible and remaining_seconds > 0 else 0

    if is_eligible:
        if days_remaining > 0:
            remaining_str = f"{days_remaining} day(s) remaining ({hours_remaining} hours left)"
        else:
            remaining_str = f"{hours_remaining} hour(s) remaining"
    else:
        remaining_str = f"Eligibility period expired ({elapsed_days} days since original purchase)"

    return {
        'is_annual': True,
        'is_eligible': is_eligible,
        'original_purchase_at': str(purchase_str),
        'purchase_date': purchase_dt.strftime('%b %d, %Y'),
        'elapsed_days': elapsed_days,
        'elapsed_seconds': elapsed_seconds,
        'days_remaining': days_remaining,
        'hours_remaining': hours_remaining,
        'remaining_str': remaining_str
    }


def get_user_pending_cancellation(username, get_db_fn):
    """Returns subscription record if user has a pending cancellation or pending refund."""
    if not username:
        return None
    try:
        conn = get_db_fn(row_factory=True)
        c = conn.cursor()
        c.execute("""
            SELECT * FROM subscriptions
            WHERE username = ?
              AND (status = 'cancellation_pending' OR refund_status = 'pending')
            ORDER BY id DESC LIMIT 1
        """, (username,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception:
        return None


# 4. DYNAMIC REFUND CALCULATION ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def calculate_subscription_refund(sub_dict, current_time=None):
    """
    Calculates refund eligibility and amount dynamically according to configured policies:
    1. Full 100% Refund: Cancelled within 48 hours of purchase with no or minimal usage.
    2. Pro-rated Partial Refund:
       - Annual plans: Between 2 days and 14 days, refunded proportionally for unused days less 5% processing fee.
       - Monthly plans: Between 2 days and 5 days, refunded proportionally for unused days less 5% processing fee.
    3. Ineligible: After 14 days (Annual), after 5 days (Monthly), or if price_paid <= 0 (trials/complimentary).

    Returns a dict with:
        is_eligible: bool
        refund_amount: float
        rule_applied: str
        policy_explanation: str
        days_used: int
        days_total: int
        original_price: float
    """
    now = current_time or datetime.now()
    price_paid = float(sub_dict.get('price_paid', 0.0))
    billing_cycle = (sub_dict.get('billing_cycle') or 'monthly').lower()
    start_dt = parse_iso_datetime(sub_dict.get('started_at')) or now
    exp_dt = parse_iso_datetime(sub_dict.get('expires_at')) or (now + timedelta(days=30))

    if price_paid <= 0.0:
        return {
            'is_eligible': False,
            'refund_amount': 0.0,
            'rule_applied': 'Free Pass / Trial',
            'policy_explanation': 'This subscription had zero monetary charge, so no refund is applicable.',
            'days_used': 0,
            'days_total': (exp_dt - start_dt).days,
            'original_price': 0.0
        }

    total_days = max(1, (exp_dt - start_dt).days)
    elapsed_seconds = max(0, (now - start_dt).total_seconds())
    elapsed_hours = elapsed_seconds / 3600.0
    elapsed_days = int(elapsed_seconds / 86400.0)
    remaining_days = max(0, total_days - elapsed_days)

    # 1. Annual Subscription Cancellation Rules:
    # Cancellation allowed with refund only within 7 calendar days (later strictly locked).
    # Daily charges applied based on days used + 5% processing fee; remaining amount refunded.
    if billing_cycle == 'yearly':
        seven_days_seconds = 7.0 * 86400.0
        if elapsed_seconds > seven_days_seconds or elapsed_days > 7:
            return {
                'is_eligible': False,
                'is_locked': True,
                'refund_amount': 0.0,
                'rule_applied': 'Locked: Exceeded 7-Day Window',
                'policy_explanation': 'Annual subscription cancellation with refund is locked after 7 calendar days of purchase. Your VIP benefits remain active until the end of your billing cycle.',
                'days_used': elapsed_days,
                'days_total': total_days,
                'original_price': price_paid,
                'deduction': price_paid
            }

        # Within 7 days: calculate daily usage charge and processing fee
        days_charged = max(1, elapsed_days if elapsed_days > 0 else 1)
        daily_charge = round((price_paid / 365.0) * days_charged, 2)
        processing_fee = round(price_paid * 0.05, 2)
        total_cut = round(daily_charge + processing_fee, 2)
        refund_amount = round(max(0.0, price_paid - total_cut), 2)

        return {
            'is_eligible': True,
            'is_locked': False,
            'refund_amount': refund_amount,
            'rule_applied': f'7-Day Policy ({days_charged}/7 Days Charged)',
            'policy_explanation': f'Cancelled on day {days_charged} of 7-day satisfaction window. Daily usage charge (₹{daily_charge:,.2f}) and 5% processing fee (₹{processing_fee:,.2f}) deducted. Remaining refund: ₹{refund_amount:,.2f}.',
            'days_used': days_charged,
            'days_total': 7,
            'original_price': price_paid,
            'daily_charge': daily_charge,
            'processing_fee': processing_fee,
            'deduction': total_cut
        }

    # 2. Monthly Subscription Cancellation Rules (48h full refund, up to 5 days pro-rated)
    if elapsed_hours <= 48.0:
        return {
            'is_eligible': True,
            'is_locked': False,
            'refund_amount': price_paid,
            'rule_applied': 'Full 100% Refund (48-Hour Guarantee)',
            'policy_explanation': 'Cancelled within the 48-hour satisfaction window. You are eligible for a 100% full refund.',
            'days_used': max(1, elapsed_days),
            'days_total': total_days,
            'original_price': price_paid
        }

    if elapsed_days <= 5 and remaining_days > 0:
        fraction_remaining = remaining_days / float(total_days)
        raw_refund = price_paid * fraction_remaining
        net_refund = round(max(0.0, raw_refund * 0.95), 2)
        return {
            'is_eligible': True,
            'is_locked': False,
            'refund_amount': net_refund,
            'rule_applied': f'Pro-Rated Refund ({remaining_days}/{total_days} Unused Days)',
            'policy_explanation': f'Cancelled within 5 days. Eligible for pro-rated refund for {remaining_days} unused days (less 5% processing fee).',
            'days_used': elapsed_days,
            'days_total': total_days,
            'original_price': price_paid
        }

    # 3. Monthly Window Expired
    return {
        'is_eligible': False,
        'is_locked': True,
        'refund_amount': 0.0,
        'rule_applied': 'Ineligible (Exceeded 5-Day Window)',
        'policy_explanation': 'The monthly cancellation refund window (5 days) has concluded. Cancellation with refund is no longer eligible.',
        'days_used': elapsed_days,
        'days_total': total_days,
        'original_price': price_paid
    }


# ─────────────────────────────────────────────────────────────────────────────
# 5. FEATURE ACCESS CONTROL & USAGE LIMITS
# ─────────────────────────────────────────────────────────────────────────────

def check_subscription_feature_access(username, feature_name, context, get_db_fn, is_admin_or_host=False):
    """
    Enforces feature-level access for Free, Normal, and Super tiers.
    Features: 'stream_hd', 'stream_fhd_2k', 'multi_camera', 'vip_crown_badge',
              'priority_qa', 'ad_free', 'free_event_entry', 'offline_downloads'.
    Returns: (is_allowed: bool, reason: str, required_tier: str)
    """
    if is_admin_or_host:
        return True, "Full Administrative Access", "super"

    sub = get_user_subscription(username, get_db_fn, include_grace=True)
    tier = (sub.get('plan_type') if sub else 'free').lower()
    limits = TIER_LIMITS.get(tier, TIER_LIMITS['free'])

    if feature_name == 'stream_hd':
        # 720p HD: Normal and Super
        if tier in ('normal', 'super'):
            return True, "720p HD streaming allowed", tier
        return False, "HD streaming requires a Normal or Super Pack subscription.", "normal"

    elif feature_name in ('stream_fhd_2k', 'stream_1080p', 'stream_2k'):
        # 1080p and 2K: Super only
        if tier == 'super':
            return True, "1080p FHD & 2K QHD streaming allowed", "super"
        return False, "1080p Full HD & 2K QHD streaming requires the Super Pack VIP.", "super"

    elif feature_name in ('multi_camera', 'dashcam_feed'):
        if tier == 'super':
            return True, "Multi-camera feed unlocked", "super"
        return False, "Multi-camera and dashcam feeds are exclusive to Super Pack VIP members.", "super"

    elif feature_name == 'vip_crown_badge':
        if tier == 'super':
            return True, "VIP Crown Badge active", "super"
        return False, "VIP Crown Badge is an exclusive perk of the Super Pack.", "super"

    elif feature_name == 'priority_qa':
        if tier == 'super':
            return True, "Priority Q&A highlighting unlocked", "super"
        return False, "Priority live question highlighting requires Super Pack VIP.", "super"

    elif feature_name == 'ad_free':
        if tier in ('normal', 'super'):
            return True, "Ad-free experience active", tier
        return False, "Ad-free live broadcasting requires a subscription pack.", "normal"

    elif feature_name == 'free_event_entry':
        event_price = float(context.get('price', 0.0) if isinstance(context, dict) else 0.0)
        if tier == 'super':
            return True, "All events included free with Super Pack VIP", "super"
        elif tier == 'normal':
            if event_price <= 1000.0:
                return True, f"Event (₹{event_price:,.0f}) is within Normal Pack ₹1,000 allowance", "normal"
            else:
                return False, f"Event price ₹{event_price:,.0f} exceeds Normal Pack ₹1,000 limit. Upgrade to Super Pack for unlimited access.", "super"
        else:
            if event_price == 0.0:
                return True, "Free public event", "free"
            return False, "Paid event pass required. Subscribe to watch without fees.", "normal"

    # Default fallback
    return True, "Standard access", tier

def record_subscription_usage(username, feature_name, get_db_fn, amount=1, metadata=None):
    """Logs feature usage into subscription_usage table."""
    if not username:
        return
    try:
        conn = get_db_fn()
        c = conn.cursor()
        c.execute("""
            INSERT INTO subscription_usage (username, feature_name, usage_count, metadata)
            VALUES (?, ?, ?, ?)
        """, (username, feature_name, amount, json.dumps(metadata or {})))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[RECORD USAGE ERROR] {e}")

def get_subscription_usage_stats(username, get_db_fn):
    """Aggregates feature usage counts for dashboard widgets."""
    stats = {
        'streams_watched': 0,
        'multicam_switches': 0,
        'vip_chat_messages': 0,
        'priority_questions': 0,
        'invoices_downloaded': 0
    }
    if not username:
        return stats
    try:
        conn = get_db_fn()
        c = conn.cursor()
        c.execute("""
            SELECT feature_name, SUM(usage_count) 
            FROM subscription_usage 
            WHERE username = ? 
            GROUP BY feature_name
        """, (username,))
        for row in c.fetchall():
            feat, cnt = row[0], row[1] or 0
            if feat in ('stream_view', 'live_stream'):
                stats['streams_watched'] += cnt
            elif feat in ('multi_camera', 'multicam'):
                stats['multicam_switches'] += cnt
            elif feat in ('vip_chat', 'chat_crown'):
                stats['vip_chat_messages'] += cnt
            elif feat in ('priority_qa', 'qa_upvote'):
                stats['priority_questions'] += cnt
            elif feat in ('invoice_download',):
                stats['invoices_downloaded'] += cnt
        conn.close()
    except Exception as e:
        print(f"[USAGE STATS ERROR] {e}")
    return stats


# ─────────────────────────────────────────────────────────────────────────────
# 6. COUPON & DISCOUNT ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def validate_subscription_coupon(code, plan_type, billing_cycle, original_amount, get_db_fn):
    """
    Validates a subscription coupon code against constraints.
    Returns: { 'ok': bool, 'error': str, 'discount_amount': float, 'final_amount': float, 'coupon': dict }
    """
    if not code:
        return {'ok': False, 'error': 'Coupon code is required.'}

    clean_code = str(code).strip().upper()
    try:
        conn = get_db_fn(row_factory=True)
        c = conn.cursor()
        c.execute("""
            SELECT id, code, discount_type, discount_val, max_discount, min_amount,
                   applicable_plan, applicable_cycle, valid_until, max_uses, times_used, is_active, description
            FROM subscription_coupons
            WHERE UPPER(code) = ?
        """, (clean_code,))
        row = c.fetchone()
        conn.close()

        if not row:
            return {'ok': False, 'error': f"Coupon '{clean_code}' is invalid or expired."}

        cp = dict(row)
        if not cp['is_active']:
            return {'ok': False, 'error': f"Coupon '{clean_code}' is currently inactive."}

        if cp['times_used'] >= cp['max_uses']:
            return {'ok': False, 'error': f"Coupon '{clean_code}' has reached its maximum redemption limit."}

        if cp['valid_until']:
            exp = parse_iso_datetime(cp['valid_until'])
            if exp and datetime.now() > exp:
                return {'ok': False, 'error': f"Coupon '{clean_code}' expired on {cp['valid_until'][:10]}."}

        if original_amount < float(cp['min_amount']):
            return {'ok': False, 'error': f"Minimum cart order of ₹{cp['min_amount']:,.0f} required for coupon '{clean_code}'."}

        app_plan = (cp['applicable_plan'] or 'all').lower()
        if app_plan not in ('all', plan_type.lower()):
            return {'ok': False, 'error': f"Coupon '{clean_code}' applies only to {app_plan.capitalize()} Pack."}

        app_cycle = (cp['applicable_cycle'] or 'all').lower()
        if app_cycle not in ('all', billing_cycle.lower()):
            return {'ok': False, 'error': f"Coupon '{clean_code}' applies only to {app_cycle.capitalize()} billing."}

        # Calculate discount
        if cp['discount_type'] == 'percent':
            discount = original_amount * (float(cp['discount_val']) / 100.0)
            if cp['max_discount'] > 0:
                discount = min(discount, float(cp['max_discount']))
        else:  # flat
            discount = float(cp['discount_val'])

        discount = round(min(original_amount, max(0.0, discount)), 2)
        final_amount = round(max(0.0, original_amount - discount), 2)

        return {
            'ok': True,
            'code': clean_code,
            'discount_amount': discount,
            'final_amount': final_amount,
            'description': cp.get('description', ''),
            'discount_type': cp['discount_type'],
            'discount_val': cp['discount_val']
        }
    except Exception as e:
        print(f"[COUPON VALIDATION ERROR] {e}")
        return {'ok': False, 'error': 'Server error validating coupon code.'}

def mark_coupon_used(code, get_db_fn):
    if not code:
        return
    try:
        conn = get_db_fn()
        c = conn.cursor()
        c.execute("UPDATE subscription_coupons SET times_used = times_used + 1 WHERE UPPER(code) = ?", (code.strip().upper(),))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[COUPON USE INCREMENT ERROR] {e}")


# ─────────────────────────────────────────────────────────────────────────────
# 7. TAX INVOICE GENERATOR (FPDF A4)
# ─────────────────────────────────────────────────────────────────────────────

def generate_subscription_invoice_pdf_bytes(sub, payment_info, user_info) -> bytes:
    sub_id = sub.get('id', 1)
    username = user_info.get('username') or sub.get('username') or 'subscriber'
    full_name = user_info.get('full_name') or username
    email = user_info.get('email') or 'N/A'
    phone = user_info.get('phone') or 'N/A'
    user_id_str = user_info.get('user_id') or f"UID-{user_info.get('id', 1):04d}"

    plan_type = sub.get('plan_type', 'normal')
    billing_cycle = sub.get('billing_cycle', 'monthly')
    plan_title = 'Super Pack VIP' if plan_type == 'super' else 'Normal Pack'
    cycle_str = 'Annual VIP Pass (12 Months)' if billing_cycle == 'yearly' else 'Monthly VIP Pass (30 Days)'

    price_paid = float(sub.get('price_paid', 0.0))
    discount_amount = float(sub.get('discount_amount', 0.0) or payment_info.get('discount_amount', 0.0))
    coupon_code = sub.get('coupon_code') or payment_info.get('coupon_code', '')

    base_taxable = round(price_paid / 1.18, 2)
    tax_total = round(price_paid - base_taxable, 2)
    cgst = round(tax_total / 2.0, 2)
    sgst = round(tax_total - cgst, 2)

    invoice_num = sub.get('invoice_number') or f"INV-SUB-2026-{sub_id:05d}"
    payment_id = sub.get('payment_id') or payment_info.get('payment_id') or f"PAY-{sub_id:05d}"
    payment_method = sub.get('payment_method') or payment_info.get('payment_method') or 'Razorpay / UPI'
    started_at = str(sub.get('started_at') or datetime.now().strftime('%Y-%m-%d %H:%M:%S'))[:16]
    expires_at = str(sub.get('expires_at') or (datetime.now() + timedelta(days=365 if billing_cycle == 'yearly' else 30)).strftime('%Y-%m-%d %H:%M:%S'))[:16]

    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()

    # 1. Dark Modern Header Banner (#090D16)
    pdf.set_fill_color(9, 13, 22)
    pdf.rect(0, 0, 210, 48, 'F')

    # Accent Top Lines (Cyan #008be3 + Neon Rose #ff1389)
    pdf.set_fill_color(0, 139, 227)
    pdf.rect(0, 0, 130, 3, 'F')
    pdf.set_fill_color(255, 19, 137)
    pdf.rect(130, 0, 80, 3, 'F')

    # Platform Title & Tagline
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Helvetica', 'B', 20)
    pdf.set_xy(14, 11)
    pdf.cell(100, 9, "EVENTS BOOKING", align='L')

    pdf.set_font('Helvetica', '', 8.5)
    pdf.set_text_color(148, 163, 184)
    pdf.set_xy(14, 21)
    pdf.cell(100, 4.5, "Official Live Stage Stream & VIP Accreditation Platform", align='L')
    pdf.set_xy(14, 26)
    pdf.cell(100, 4.5, "GSTIN: 29AAACE9999P1Z8  |  SAC: 9984 (Digital Online Streaming)", align='L')
    pdf.set_xy(14, 31)
    pdf.cell(100, 4.5, "Bengaluru, Karnataka, India - 560001  |  support@eventsbooking.internal", align='L')

    # Top Right Invoice Title & Paid Badge
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(0, 139, 227)
    pdf.set_xy(110, 11)
    pdf.cell(86, 7, "TAX INVOICE & RECEIPT", align='R')

    # Paid Pill Badge (#10B981)
    pdf.set_fill_color(16, 185, 129)
    pdf.rect(168, 19, 28, 6.5, 'F')
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Helvetica', 'B', 7.5)
    pdf.set_xy(168, 19)
    pdf.cell(28, 6.5, "PAID IN FULL", align='C')

    # Invoice Metadata
    pdf.set_xy(110, 27)
    pdf.set_text_color(148, 163, 184)
    pdf.set_font('Helvetica', '', 8)
    pdf.cell(46, 4.5, "Invoice Number:", align='R')
    pdf.set_font('Helvetica', 'B', 8.5)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(40, 4.5, invoice_num, align='R')

    pdf.set_xy(110, 32)
    pdf.set_text_color(148, 163, 184)
    pdf.set_font('Helvetica', '', 8)
    pdf.cell(46, 4.5, "Billing Date:", align='R')
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_text_color(203, 213, 225)
    pdf.cell(40, 4.5, started_at, align='R')

    pdf.set_xy(110, 37)
    pdf.set_text_color(148, 163, 184)
    pdf.set_font('Helvetica', '', 8)
    pdf.cell(46, 4.5, "Transaction Ref:", align='R')
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_text_color(0, 139, 227)
    pdf.cell(40, 4.5, str(payment_id)[:18], align='R')

    # 2. Two Distinct Card Boxes: Billed To vs Plan Specifications
    # Box 1: Billed To
    pdf.set_fill_color(248, 250, 252)
    pdf.set_draw_color(226, 232, 240)
    pdf.set_line_width(0.3)
    pdf.rect(14, 53, 88, 38, 'DF')

    pdf.set_fill_color(0, 139, 227)
    pdf.rect(14, 53, 2.5, 38, 'F')

    pdf.set_xy(19, 56)
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(80, 4, "BILLED TO SUBSCRIBER", align='L')

    pdf.set_xy(19, 61)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(80, 5, full_name[:32], align='L')

    pdf.set_font('Helvetica', '', 8)
    pdf.set_text_color(71, 85, 105)
    pdf.set_xy(19, 67)
    pdf.cell(80, 4, f"Account ID: {user_id_str}  (@{username})", align='L')
    pdf.set_xy(19, 72)
    pdf.cell(80, 4, f"Email: {email[:34]}", align='L')
    pdf.set_xy(19, 77)
    pdf.cell(80, 4, f"Phone: {phone}", align='L')
    pdf.set_xy(19, 82)
    pdf.cell(80, 4, f"Gateway: {payment_method}", align='L')

    # Box 2: Plan Details
    pdf.set_fill_color(248, 250, 252)
    pdf.set_draw_color(226, 232, 240)
    pdf.rect(108, 53, 88, 38, 'DF')

    accent_color = (255, 19, 137) if plan_type == 'super' else (0, 139, 227)
    pdf.set_fill_color(*accent_color)
    pdf.rect(108, 53, 2.5, 38, 'F')

    pdf.set_xy(113, 56)
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(80, 4, "VIP MEMBERSHIP SPECIFICATIONS", align='L')

    pdf.set_xy(113, 61)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(*accent_color)
    pdf.cell(80, 5, f"{plan_title.upper()}", align='L')

    pdf.set_font('Helvetica', '', 8)
    pdf.set_text_color(71, 85, 105)
    pdf.set_xy(113, 67)
    pdf.cell(80, 4, f"Billing Cycle: {cycle_str}", align='L')
    pdf.set_xy(113, 72)
    pdf.cell(80, 4, f"Resolution: {'1080p FHD & 2K QHD' if plan_type == 'super' else '720p HD'}", align='L')
    pdf.set_xy(113, 77)
    pdf.cell(80, 4, f"Screens: {'2 Devices Simultaneously' if plan_type == 'super' else '1 Device at a time'}", align='L')
    pdf.set_xy(113, 82)
    pdf.cell(80, 4, f"Valid: {started_at[:10]} to {expires_at[:10]}", align='L')

    # 3. Itemized Table
    pdf.set_xy(14, 96)
    pdf.set_fill_color(15, 23, 42)
    pdf.rect(14, 96, 182, 8, 'F')
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(10, 8, "#", align='C')
    pdf.cell(92, 8, "DESCRIPTION & SERVICE SCOPE", align='L')
    pdf.cell(26, 8, "SAC CODE", align='C')
    pdf.cell(26, 8, "TAX RATE", align='C')
    pdf.cell(28, 8, "AMOUNT (INR)", align='R')

    # Row 1
    pdf.set_xy(14, 104)
    pdf.set_fill_color(255, 255, 255)
    pdf.set_font('Helvetica', '', 8.5)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(10, 8.5, "1", align='C')
    pdf.set_font('Helvetica', 'B', 8.5)
    pdf.cell(92, 8.5, f"{plan_title} - {cycle_str}", align='L')
    pdf.set_font('Helvetica', '', 8.5)
    pdf.cell(26, 8.5, "9984", align='C')
    pdf.cell(26, 8.5, "18% GST", align='C')
    pdf.cell(28, 8.5, f"{base_taxable:,.2f}", align='R')

    pdf.set_draw_color(226, 232, 240)
    pdf.line(14, 113, 196, 113)

    # 4. Financial Summary
    y_sum = 117
    sum_items = [
        ("Base Service Fee (Excl. Tax):", f"INR {base_taxable:,.2f}"),
        ("Central GST (CGST @ 9%):", f"INR {cgst:,.2f}"),
        ("State GST (SGST @ 9%):", f"INR {sgst:,.2f}"),
    ]
    if discount_amount > 0:
        sum_items.append((f"Promo Coupon Discount ({coupon_code or 'APPLIED'}):", f"- INR {discount_amount:,.2f}"))

    # Settlement Mode Box (Left side of financial breakdown)
    pdf.set_fill_color(240, 253, 244)
    pdf.set_draw_color(187, 247, 208)
    pdf.rect(14, 117, 72, 24, 'DF')
    pdf.set_fill_color(16, 185, 129)
    pdf.rect(14, 117, 2, 24, 'F')

    pdf.set_xy(18, 119)
    pdf.set_font('Helvetica', 'B', 7.5)
    pdf.set_text_color(22, 101, 52)
    pdf.cell(66, 3.8, "PAYMENT RECONCILIATION", align='L')
    pdf.set_xy(18, 123.5)
    pdf.set_font('Helvetica', '', 7)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(66, 3.5, f"Status: COMPLETED & SETTLED", align='L')
    pdf.set_xy(18, 127.5)
    pdf.cell(66, 3.5, f"Channel: {payment_method[:28]}", align='L')
    pdf.set_xy(18, 131.5)
    pdf.cell(66, 3.5, f"Clearing Ref: {str(payment_id)[:24]}", align='L')
    pdf.set_xy(18, 135.5)
    pdf.cell(66, 3.5, f"Accounting: Automated Platform Reconciled", align='L')

    # Right side financial lines
    for label, val in sum_items:
        pdf.set_xy(90, y_sum)
        pdf.set_font('Helvetica', '', 8)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(60, 4.5, label, align='R')
        pdf.set_text_color(30, 41, 59)
        pdf.set_font('Helvetica', 'B', 8.5)
        pdf.cell(46, 4.5, val, align='R')
        y_sum += 5

    # Total Amount Banner
    pdf.set_fill_color(240, 249, 255)
    pdf.set_draw_color(186, 230, 253)
    pdf.rect(90, y_sum + 1, 106, 9.5, 'DF')
    pdf.set_fill_color(0, 139, 227)
    pdf.rect(90, y_sum + 1, 2.5, 9.5, 'F')

    pdf.set_xy(95, y_sum + 1)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(55, 9.5, "TOTAL AMOUNT PAID:", align='L')
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(0, 139, 227)
    pdf.cell(44, 9.5, f"INR {price_paid:,.2f}", align='R')

    # 5. VIP Protection & Tax Exemption Badges Strip (Y = 152 to 166)
    pdf.set_fill_color(248, 250, 252)
    pdf.set_draw_color(226, 232, 240)
    pdf.rect(14, 150, 182, 12, 'DF')

    badges = [
        ("100% Tax Deductible", "Valid GST Tax Invoice under CGST Rule 46"),
        ("Instant Gateway Settlement", "No physical signature required under IT Act 2000"),
        ("Satisfaction Guarantee", "Protected by Platform 7-Day Guarantee")
    ]
    x_badge = 14
    for b_title, b_sub in badges:
        pdf.set_xy(x_badge, 151.5)
        pdf.set_font('Helvetica', 'B', 7)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(60, 3.5, f"[OK] {b_title}", align='C')
        pdf.set_xy(x_badge, 155.5)
        pdf.set_font('Helvetica', '', 6.2)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(60, 3.5, b_sub, align='C')
        x_badge += 60.6

    # 6. Beautiful Authenticity & Cryptographic Verification Section (Y = 168 to 260)
    sig_hash = hashlib.sha256(f"{invoice_num}|{payment_id}|{username}|{price_paid}".encode()).hexdigest()[:24].upper()
    cert_id = f"EB-AUTH-2026-{sub_id:05d}"

    # Left: QR Code Verification Card
    pdf.set_fill_color(255, 255, 255)
    pdf.set_draw_color(226, 232, 240)
    pdf.rect(14, 168, 88, 86, 'DF')
    pdf.set_fill_color(0, 139, 227)
    pdf.rect(14, 168, 88, 1.5, 'F')

    try:
        qr = qrcode.QRCode(version=1, box_size=3, border=1)
        qr_data = f"EVENTS-VIP|{invoice_num}|{sig_hash}|{price_paid}|{started_at}"
        qr.add_data(qr_data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        qr_buffer = io.BytesIO()
        img.save(qr_buffer, format="PNG")
        qr_buffer.seek(0)
        pdf.image(qr_buffer, x=42, y=173, w=32, h=32)
    except Exception:
        pass

    pdf.set_xy(18, 208)
    pdf.set_font('Helvetica', 'B', 8.5)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(80, 4, "SCAN TO VERIFY AUTHENTICITY", align='C')

    pdf.set_xy(18, 214)
    pdf.set_font('Helvetica', '', 7.2)
    pdf.set_text_color(100, 116, 139)
    pdf.multi_cell(80, 3.4, "Scan with any smartphone camera or gate scanner to instantly confirm live stage pass credentials, screen allotment, and official tax clearance.", align='C')

    pdf.set_xy(18, 232)
    pdf.set_font('Helvetica', 'B', 7)
    pdf.set_text_color(0, 139, 227)
    pdf.cell(80, 3.5, f"CERTIFICATE ID: {cert_id}", align='C')

    pdf.set_xy(18, 236)
    pdf.set_font('Helvetica', '', 6.8)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(80, 3.5, f"INTEGRITY HASH: {sig_hash[:12]}-{sig_hash[12:]}", align='C')

    pdf.set_xy(18, 242)
    pdf.set_fill_color(240, 253, 244)
    pdf.rect(20, 242, 76, 6, 'F')
    pdf.set_font('Helvetica', 'B', 6.8)
    pdf.set_text_color(22, 101, 52)
    pdf.cell(80, 6, "[OK] CRYPTOGRAPHICALLY VALIDATED", align='C')

    # Right: Executive Digital Certificate & Security Seal Medallion
    pdf.set_fill_color(255, 255, 255)
    pdf.set_draw_color(226, 232, 240)
    pdf.rect(108, 168, 88, 86, 'DF')
    pdf.set_fill_color(16, 185, 129)
    pdf.rect(108, 168, 88, 1.5, 'F')

    # Gold / Emerald Medallion Crest Box
    pdf.set_fill_color(254, 252, 232) # Soft warm cream/gold
    pdf.set_draw_color(217, 119, 6)   # Amber gold border
    pdf.rect(114, 174, 76, 22, 'DF')
    pdf.set_fill_color(217, 119, 6)
    pdf.rect(114, 174, 1.5, 22, 'F')

    pdf.set_xy(118, 176.5)
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_text_color(180, 83, 9)
    pdf.cell(68, 3.8, "* OFFICIAL EXECUTIVE SEAL *", align='C')

    pdf.set_xy(118, 181)
    pdf.set_font('Helvetica', 'B', 8.5)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(68, 4.2, "EVENTS BOOKING ACCREDITED", align='C')

    pdf.set_xy(118, 186.5)
    pdf.set_font('Helvetica', 'I', 6.5)
    pdf.set_text_color(120, 53, 15)
    pdf.cell(68, 3.5, "Digital Security Clearance & Compliance Seal", align='C')

    pdf.set_xy(118, 190.5)
    pdf.set_font('Helvetica', 'B', 6.5)
    pdf.set_text_color(16, 185, 129)
    pdf.cell(68, 3.5, "[OK] VERIFIED & RECONCILED", align='C')

    # Digital Signature Representation (Stylized Executive Script)
    pdf.set_xy(114, 200)
    pdf.set_font('Helvetica', 'B', 7.5)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(76, 3.5, "DIGITALLY CERTIFIED BY:", align='L')

    # Simulated Calligraphic Digital Signature Ribbon
    pdf.set_fill_color(248, 250, 252)
    pdf.set_draw_color(203, 213, 225)
    pdf.rect(114, 204.5, 76, 14, 'DF')

    pdf.set_xy(116, 206)
    pdf.set_font('Helvetica', 'BI', 9.5)
    pdf.set_text_color(0, 139, 227)
    pdf.cell(72, 4.5, "Events Booking Core Automation", align='C')

    pdf.set_xy(116, 211)
    pdf.set_font('Helvetica', '', 6.5)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(72, 3.5, "Cryptographic Public Key Certificate & Billing Gateway", align='C')

    # Legal & Compliance Notice
    pdf.set_xy(114, 222)
    pdf.set_font('Helvetica', 'B', 7)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(76, 3.5, "LEGAL & TAX RECOGNITION:", align='L')

    pdf.set_xy(114, 226)
    pdf.set_font('Helvetica', '', 6.8)
    pdf.set_text_color(71, 85, 105)
    pdf.multi_cell(76, 3.2, "Issued in accordance with Rule 46 of the Central Goods and Services Tax (CGST) Act, 2017. Validated pursuant to Section 10A of the Information Technology Act, 2000.")

    pdf.set_xy(114, 240)
    pdf.set_font('Helvetica', 'I', 6.5)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(76, 3.5, "Tamper-Evident Electronic Document - No Physical Signature Required", align='C')

    # 7. Bottom Footer (Y = 275 to 297)
    pdf.set_fill_color(9, 13, 22)
    pdf.rect(0, 275, 210, 22, 'F')
    pdf.set_fill_color(0, 139, 227)
    pdf.rect(0, 275, 130, 1.5, 'F')
    pdf.set_fill_color(255, 19, 137)
    pdf.rect(130, 275, 80, 1.5, 'F')

    pdf.set_xy(14, 280)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Helvetica', 'B', 8)
    pdf.cell(182, 4, "EVENTS BOOKING - LIVE VIP STAGE STREAMING & TICKETING PLATFORM", align='C')

    pdf.set_xy(14, 285)
    pdf.set_text_color(148, 163, 184)
    pdf.set_font('Helvetica', '', 7)
    pdf.cell(182, 4, "Official Support: support@eventsbooking.internal  |  Bengaluru, India  |  EULA & Platform Terms Apply", align='C')

    try:
        return bytes(pdf.output())
    except TypeError:
        return pdf.output(dest='S')


# ─────────────────────────────────────────────────────────────────────────────
# 8. BACKGROUND EXPIRY & NOTIFICATION WORKER
# ─────────────────────────────────────────────────────────────────────────────

def run_subscription_lifecycle_checks(get_db_fn, dispatch_email_fn=None, push_notif_fn=None, logger_fn=None):
    """
    Scans subscriptions to process:
    1. Automated milestone reminders (7 days, 3 days, 1 day, 0 days).
    2. Grace period activations.
    3. Expiration state transitions.
    Prevents duplicate notifications through tracked database milestone flags.
    """
    now = datetime.now()
    try:
        conn = get_db_fn(row_factory=True)
        c = conn.cursor()
        c.execute("""
            SELECT id, username, plan_type, billing_cycle, price_paid, expires_at,
                   status, auto_renew, reminded_7d, reminded_3d, reminded_1d, reminded_0d
            FROM subscriptions
            WHERE status IN ('active', 'in_grace_period')
        """)
        subs = [dict(r) for r in c.fetchall()]

        for s in subs:
            exp = parse_iso_datetime(s.get('expires_at'))
            if not exp:
                continue

            username = s['username']
            sub_id = s['id']
            plan_type = s['plan_type']
            plan_meta = SUBSCRIPTION_PLANS.get(plan_type, SUBSCRIPTION_PLANS['normal'])
            plan_title = plan_meta.get('title', plan_type.capitalize())
            days_left = (exp - now).days
            seconds_left = (exp - now).total_seconds()

            # Milestone 1: 7 Days Before Expiry
            if 3 < days_left <= 7 and not s.get('reminded_7d'):
                c.execute("UPDATE subscriptions SET reminded_7d = 1 WHERE id = ?", (sub_id,))
                if push_notif_fn:
                    push_notif_fn(username, f"⏳ Notice: Your {plan_title} expires in {days_left} days. Renew now for continuous VIP access.", "/subscriptions")
                if dispatch_email_fn:
                    _dispatch_expiry_email(username, plan_title, days_left, exp, get_db_fn, dispatch_email_fn)
                if logger_fn:
                    logger_fn(username, 'SUB_REMINDER_7D', f"Sent 7-day expiry reminder for {plan_title}")

            # Milestone 2: 3 Days Before Expiry
            elif 1 < days_left <= 3 and not s.get('reminded_3d'):
                c.execute("UPDATE subscriptions SET reminded_3d = 1 WHERE id = ?", (sub_id,))
                if push_notif_fn:
                    push_notif_fn(username, f"⚠️ Important: Only {days_left} days left on your {plan_title} pass.", "/subscriptions")
                if dispatch_email_fn:
                    _dispatch_expiry_email(username, plan_title, days_left, exp, get_db_fn, dispatch_email_fn)
                if logger_fn:
                    logger_fn(username, 'SUB_REMINDER_3D', f"Sent 3-day expiry reminder for {plan_title}")

            # Milestone 3: 1 Day Before Expiry
            elif 0 <= days_left <= 1 and seconds_left > 0 and not s.get('reminded_1d'):
                c.execute("UPDATE subscriptions SET reminded_1d = 1 WHERE id = ?", (sub_id,))
                if push_notif_fn:
                    push_notif_fn(username, f"🚨 Final Notice: Your {plan_title} expires in 24 hours!", "/subscriptions")
                if dispatch_email_fn:
                    _dispatch_expiry_email(username, plan_title, 1, exp, get_db_fn, dispatch_email_fn)
                if logger_fn:
                    logger_fn(username, 'SUB_REMINDER_1D', f"Sent 1-day expiry reminder for {plan_title}")

            # Milestone 4: Expired (0 Days / Negative)
            elif seconds_left <= 0:
                grace_limit = exp + timedelta(days=3)
                if now <= grace_limit:
                    # In 3-day grace period
                    if s.get('status') != 'in_grace_period':
                        c.execute("UPDATE subscriptions SET status = 'in_grace_period' WHERE id = ?", (sub_id,))
                    if not s.get('reminded_0d'):
                        c.execute("UPDATE subscriptions SET reminded_0d = 1 WHERE id = ?", (sub_id,))
                        if push_notif_fn:
                            push_notif_fn(username, f"🔔 Your {plan_title} is now in a 3-day grace period. Renew to keep your streaming perks.", "/subscriptions")
                        if dispatch_email_fn:
                            _dispatch_expiry_email(username, plan_title, 0, exp, get_db_fn, dispatch_email_fn)
                        if logger_fn:
                            logger_fn(username, 'SUB_GRACE_PERIOD', f"Activated 3-day grace period for {plan_title}")
                else:
                    # Hard expiration
                    c.execute("UPDATE subscriptions SET status = 'expired' WHERE id = ?", (sub_id,))
                    if push_notif_fn:
                        push_notif_fn(username, f"Your {plan_title} has expired. Your account has returned to standard visitor mode. All tickets & data remain safe.", "/subscriptions")
                    if logger_fn:
                        logger_fn(username, 'SUB_EXPIRED', f"Subscription expired for {plan_title}")

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[SUBSCRIPTION LIFECYCLE WORKER ERROR] {e}")

def _dispatch_expiry_email(username, plan_title, days_left, exp_dt, get_db_fn, dispatch_email_fn):
    """Dispatches a formatted expiry reminder email."""
    try:
        conn = get_db_fn(row_factory=True)
        c = conn.cursor()
        c.execute("SELECT email, full_name FROM users WHERE username = ?", (username,))
        u = c.fetchone()
        conn.close()
        if not u or not u['email']:
            return

        recipient_email = u['email']
        recipient_name = u['full_name'] or username
        exp_str = exp_dt.strftime('%d %b %Y')

        if days_left == 0:
            subject = f"🔔 Action Required: Your {plan_title} has reached expiry (Grace Period Active)"
            status_banner = "Your subscription has entered a temporary 3-day grace period."
        else:
            subject = f"⏳ Reminder: Your {plan_title} expires in {days_left} day{'s' if days_left != 1 else ''}"
            status_banner = f"Your subscription is scheduled to expire on <strong>{exp_str}</strong>."

        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #070709; color: #ffffff; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background: #0f172a; border-radius: 12px; padding: 30px; border: 1px solid rgba(0, 139, 227, 0.3);">
                <h2 style="color: #008be3; margin-top: 0;">Events Booking Subscription Alert</h2>
                <p>Hello <strong>{recipient_name}</strong>,</p>
                <p>{status_banner}</p>
                <div style="background: rgba(255, 255, 255, 0.05); padding: 15px; border-radius: 8px; margin: 20px 0;">
                    <p style="margin: 0; font-size: 14px; color: #94a3b8;">Subscription: <strong style="color: #fff;">{plan_title}</strong></p>
                    <p style="margin: 5px 0 0; font-size: 14px; color: #94a3b8;">Expiry Date: <strong style="color: #38bdf8;">{exp_str}</strong></p>
                </div>
                <p>Renew now to continue enjoying zero-ad live broadcasts, multi-camera feeds, and complimentary tickets for premier summits.</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="http://127.0.0.1:5000/subscriptions" style="background: linear-gradient(135deg, #008be3, #0062a3); color: #ffffff; text-decoration: none; padding: 12px 28px; border-radius: 30px; font-weight: bold; display: inline-block;">
                        Renew Subscription Now
                    </a>
                </div>
                <p style="color: #64748b; font-size: 12px; margin-bottom: 0;">
                    If you choose not to renew, your account will smoothly revert to the standard free plan. All your previously booked tickets, certificates, and event history will remain completely preserved.
                </p>
            </div>
        </body>
        </html>
        """
        text = f"Hello {recipient_name},\n\nYour {plan_title} subscription expires on {exp_str}. Renew at http://127.0.0.1:5000/subscriptions to maintain continuous VIP streaming access.\n\nEvents Booking Team"
        dispatch_email_fn(recipient_email, subject, html, text)
    except Exception as e:
        print(f"[DISPATCH EXPIRY EMAIL ERROR] {e}")
