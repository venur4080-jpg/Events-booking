"""
backend/test_subscriptions.py
Comprehensive automated test suite for the Enterprise Subscription Management Module.
Self-contained tests ensuring 100% reliability across all subscription features.
"""

import os
os.environ['TESTING'] = '1'
import unittest
import json
import sqlite3
from datetime import datetime, timedelta
import sys

_backend_dir = os.path.dirname(os.path.abspath(__file__))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from app import app, init_db, get_db
from subscription_service import (
    SUBSCRIPTION_PLANS, TIER_LIMITS,
    get_user_subscription, get_user_subscription_status,
    get_user_subscription_history, get_user_payment_history,
    calculate_subscription_refund, check_subscription_feature_access,
    record_subscription_usage, get_subscription_usage_stats,
    validate_subscription_coupon, generate_subscription_invoice_pdf_bytes,
    run_subscription_lifecycle_checks, get_annual_cancellation_eligibility,
    get_user_pending_cancellation
)

DB_PATH = os.path.join(_backend_dir, 'users.db')

class SubscriptionModuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("DELETE FROM subscriptions WHERE username IN ('test_subscriber', 'test_trial_user')")
        c.execute("DELETE FROM subscription_payments WHERE username IN ('test_subscriber', 'test_trial_user')")
        c.execute("DELETE FROM subscription_usage WHERE username IN ('test_subscriber', 'test_trial_user')")
        c.execute("""
            INSERT OR IGNORE INTO users (username, password, full_name, email, role, is_admin, is_active, user_id, trial_used)
            VALUES ('test_subscriber', 'hash123', 'Test Subscriber', 'sub@example.com', 'user', 0, 1, 'UID-9001', 0)
        """)
        c.execute("""
            INSERT OR IGNORE INTO users (username, password, full_name, email, role, is_admin, is_active, user_id, trial_used)
            VALUES ('test_trial_user', 'hash123', 'Trial User', 'trial@example.com', 'user', 0, 1, 'UID-9002', 0)
        """)
        c.execute("UPDATE users SET is_active = 1, trial_used = 0, cancellation_count = 0, is_banned = 0, ban_reason = '' WHERE username IN ('test_subscriber', 'test_trial_user')")
        conn.commit()
        conn.close()

    def _login_as(self, client, username='test_subscriber', is_admin=0):
        with client.session_transaction() as sess:
            sess['loggedin'] = True
            sess['username'] = username
            sess['role'] = 'host' if is_admin else 'user'
            sess['is_admin'] = is_admin
            sess['user_id'] = 'UID-0001' if is_admin else 'UID-9001'

    def _create_active_sub(self, username='test_subscriber', plan_type='super', billing_cycle='yearly', price=1499.0, days=365, started_at=None, expires_at=None, price_paid=None):
        if price_paid is not None: price = price_paid
        if expires_at is None:
            exp_str = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
        else:
            exp_str = expires_at.strftime('%Y-%m-%d %H:%M:%S') if hasattr(expires_at, 'strftime') else str(expires_at)
        
        start_str = started_at.strftime('%Y-%m-%d %H:%M:%S') if hasattr(started_at, 'strftime') else (str(started_at) if started_at else datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

        pay_id = f"PAY-TEST-{int(datetime.now().timestamp())}"
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            INSERT INTO subscriptions 
            (username, plan_type, billing_cycle, price_paid, max_quality, max_event_price_inr, 
             max_screens, status, started_at, expires_at, payment_id, payment_method, auto_renew, invoice_number)
            VALUES (?, ?, ?, ?, '2k', NULL, 2, 'active', ?, ?, ?, 'UPI', 1, 'INV-SUB-2026-99999')
        """, (username, plan_type, billing_cycle, price, start_str, exp_str, pay_id))
        sub_id = c.lastrowid
        conn.commit()
        conn.close()
        return sub_id

    def test_01_subscription_plans_configuration(self):
        """Test that Monthly and Annual plans exist with correct pricing, features, savings and duration."""
        self.assertIn('normal', SUBSCRIPTION_PLANS)
        self.assertIn('super', SUBSCRIPTION_PLANS)

        normal = SUBSCRIPTION_PLANS['normal']
        super_plan = SUBSCRIPTION_PLANS['super']

        self.assertEqual(normal['monthly_price'], 149.0)
        self.assertEqual(normal['yearly_price'], 899.0)
        self.assertEqual(normal['yearly_saving_pct'], 50)
        self.assertEqual(normal['max_quality'], '720p')

        self.assertEqual(super_plan['monthly_price'], 299.0)
        self.assertEqual(super_plan['yearly_price'], 1499.0)
        self.assertEqual(super_plan['yearly_saving_pct'], 58)
        self.assertEqual(super_plan['max_quality'], '2k')
        self.assertTrue(super_plan['is_recommended'])
        self.assertTrue(super_plan['is_featured'])

    def test_02_coupon_validation_and_discounts(self):
        """Test subscription coupons: percentage, flat, min amount, and invalid codes."""
        res = validate_subscription_coupon('SAVE20', 'normal', 'yearly', 899.0, get_db)
        self.assertTrue(res['ok'])
        self.assertAlmostEqual(res['discount_amount'], 179.80, places=2)
        self.assertAlmostEqual(res['final_amount'], 719.20, places=2)

        res = validate_subscription_coupon('SUPER100', 'super', 'yearly', 1499.0, get_db)
        self.assertTrue(res['ok'])
        self.assertEqual(res['discount_amount'], 100.0)
        self.assertEqual(res['final_amount'], 1399.0)

        res = validate_subscription_coupon('SUPER100', 'normal', 'yearly', 899.0, get_db)
        self.assertFalse(res['ok'])
        self.assertIn('applies only to Super Pack', res['error'])

        res = validate_subscription_coupon('INVALID_CODE_999', 'normal', 'monthly', 149.0, get_db)
        self.assertFalse(res['ok'])

    def test_03_order_creation_and_annual_rule(self):
        """Test /api/subscription/create-order and enforcement that active Annual blocks Monthly."""
        client = self.app.test_client()
        self._login_as(client, 'test_subscriber')

        resp = client.post('/api/subscription/create-order', json={
            'plan_type': 'super',
            'billing_cycle': 'yearly',
            'coupon_code': 'SAVE20'
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['ok'])
        self.assertIn('order_id', data)
        self.assertGreater(data['discount_amount'], 0)
        self.assertAlmostEqual(data['amount_inr'], 1199.20, places=1)

    def test_04_payment_verification_and_activation(self):
        """Test verifying payment activates subscription, generates invoice number, and creates payment record."""
        client = self.app.test_client()
        self._login_as(client, 'test_subscriber')

        pay_id = f"PAY-TEST-{int(datetime.now().timestamp())}"
        resp = client.post('/api/subscription/verify-payment', json={
            'order_id': 'order_test_annual_123',
            'payment_id': pay_id,
            'plan_type': 'super',
            'billing_cycle': 'yearly',
            'coupon_code': 'SUPER100',
            'payment_method': 'UPI'
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['ok'])
        self.assertIn('subscription', data)
        sub = data['subscription']
        self.assertEqual(sub['plan_type'], 'super')
        self.assertEqual(sub['billing_cycle'], 'yearly')
        self.assertIn('INV-SUB-2026-', sub['invoice_number'])

        active_sub = get_user_subscription('test_subscriber', get_db)
        self.assertIsNotNone(active_sub)
        self.assertTrue(active_sub['is_active'])
        self.assertEqual(active_sub['plan_type'], 'super')
        self.assertGreater(active_sub['days_left'], 350)

        # Verify annual block rule: User CANNOT now buy a monthly plan while annual is active!
        block_resp = client.post('/api/subscription/create-order', json={
            'plan_type': 'normal',
            'billing_cycle': 'monthly'
        })
        self.assertEqual(block_resp.status_code, 400)
        bdata = block_resp.get_json()
        self.assertFalse(bdata['ok'])
        self.assertTrue(bdata.get('annual_conflict') or 'Already Subscribed' in bdata.get('error', ''))

    def test_05_download_subscription_invoice_pdf(self):
        """Test downloading the generated PDF invoice with correct MIME type and valid PDF header."""
        sub_id = self._create_active_sub('test_subscriber', 'super', 'yearly', 1499.0)
        client = self.app.test_client()
        self._login_as(client, 'test_subscriber')

        resp = client.get(f'/subscription/invoice/{sub_id}')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers['Content-Type'], 'application/pdf')
        self.assertTrue(resp.data.startswith(b'%PDF-'))
        self.assertGreater(len(resp.data), 1000)

    def test_06_feature_access_control(self):
        """Test tier-based access control for HD, FHD 2K, multi-camera feeds and VIP badges."""
        self._create_active_sub('test_subscriber', 'super', 'yearly', 1499.0)

        free_allowed, reason, req_tier = check_subscription_feature_access('non_subscriber_user', 'stream_hd', {}, get_db)
        self.assertFalse(free_allowed)
        self.assertEqual(req_tier, 'normal')

        super_hd_allowed, _, _ = check_subscription_feature_access('test_subscriber', 'stream_hd', {}, get_db)
        self.assertTrue(super_hd_allowed)

        super_2k_allowed, _, _ = check_subscription_feature_access('test_subscriber', 'stream_fhd_2k', {}, get_db)
        self.assertTrue(super_2k_allowed)

        super_cam_allowed, _, _ = check_subscription_feature_access('test_subscriber', 'multi_camera', {}, get_db)
        self.assertTrue(super_cam_allowed)

        ev_allowed, _, _ = check_subscription_feature_access('test_subscriber', 'free_event_entry', {'price': '2500'}, get_db)
        self.assertTrue(ev_allowed)

    def test_07_feature_usage_tracking(self):
        """Test recording usage and aggregating stats for dashboard gauges."""
        record_subscription_usage('test_subscriber', 'stream_view', get_db, amount=2)
        record_subscription_usage('test_subscriber', 'multi_camera', get_db, amount=3)
        record_subscription_usage('test_subscriber', 'vip_chat', get_db, amount=5)

        stats = get_subscription_usage_stats('test_subscriber', get_db)
        self.assertGreaterEqual(stats['streams_watched'], 2)
        self.assertGreaterEqual(stats['multicam_switches'], 3)
        self.assertGreaterEqual(stats['vip_chat_messages'], 5)

    def test_08_dynamic_refund_calculator(self):
        """Test refund calculation rules: 48h full refund, 14d pro-rated refund, and expired."""
        now = datetime.now()

        # Monthly 48-hour full refund guarantee
        sub_monthly = {
            'price_paid': 299.0,
            'billing_cycle': 'monthly',
            'started_at': (now - timedelta(hours=10)).strftime('%Y-%m-%d %H:%M:%S'),
            'expires_at': (now + timedelta(days=29)).strftime('%Y-%m-%d %H:%M:%S')
        }
        quote_m = calculate_subscription_refund(sub_monthly, now)
        self.assertTrue(quote_m['is_eligible'])
        self.assertEqual(quote_m['refund_amount'], 299.0)
        self.assertIn('Full 100% Refund', quote_m['rule_applied'])

        # Annual 7-day policy: Day 1 daily charge + 5% fee cut, remaining refunded
        sub_recent = {
            'price_paid': 1499.0,
            'billing_cycle': 'yearly',
            'started_at': (now - timedelta(hours=10)).strftime('%Y-%m-%d %H:%M:%S'),
            'expires_at': (now + timedelta(days=364)).strftime('%Y-%m-%d %H:%M:%S')
        }
        quote = calculate_subscription_refund(sub_recent, now)
        self.assertTrue(quote['is_eligible'])
        self.assertAlmostEqual(quote['refund_amount'], 1419.94, places=1)
        self.assertIn('7-Day Policy', quote['rule_applied'])

        sub_prorated = {
            'price_paid': 1499.0,
            'billing_cycle': 'yearly',
            'started_at': (now - timedelta(days=6)).strftime('%Y-%m-%d %H:%M:%S'),
            'expires_at': (now + timedelta(days=359)).strftime('%Y-%m-%d %H:%M:%S')
        }
        quote_p = calculate_subscription_refund(sub_prorated, now)
        self.assertTrue(quote_p['is_eligible'])
        self.assertGreater(quote_p['refund_amount'], 1300.0)
        self.assertTrue('7-Day Policy' in quote_p['rule_applied'] or 'Pro-Rated' in quote_p['rule_applied'])

        sub_old = {
            'price_paid': 1499.0,
            'billing_cycle': 'yearly',
            'started_at': (now - timedelta(days=25)).strftime('%Y-%m-%d %H:%M:%S'),
            'expires_at': (now + timedelta(days=340)).strftime('%Y-%m-%d %H:%M:%S')
        }
        quote_old = calculate_subscription_refund(sub_old, now)
        self.assertFalse(quote_old['is_eligible'])
        self.assertEqual(quote_old['refund_amount'], 0.0)

    def test_09_auto_renewal_toggle(self):
        """Test toggling auto-renewal status via /api/subscription/toggle-auto-renew."""
        self._create_active_sub('test_subscriber', 'super', 'yearly', 1499.0)
        client = self.app.test_client()
        self._login_as(client, 'test_subscriber')

        resp = client.post('/api/subscription/toggle-auto-renew')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['ok'])
        self.assertFalse(data['auto_renew'])

        resp2 = client.post('/api/subscription/toggle-auto-renew')
        self.assertTrue(resp2.get_json()['auto_renew'])

    def test_10_cancellation_end_of_period_vs_immediate(self):
        """Test end-of-period cancellation and immediate cancellation."""
        self._create_active_sub('test_subscriber', 'super', 'yearly', 1499.0)
        client = self.app.test_client()
        self._login_as(client, 'test_subscriber')

        # 1. End of period cancellation (keeps active, disables auto-renew)
        resp = client.post('/api/subscription/cancel', json={
            'cancel_type': 'end_of_period',
            'reason': 'Too expensive',
            'feedback': 'Good platform though'
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['cancel_type'], 'end_of_period')

        sub = get_user_subscription('test_subscriber', get_db)
        self.assertIsNotNone(sub)
        self.assertEqual(sub['auto_renew'], 0)

        # 2. Immediate cancellation (terminates access immediately, records refund)
        resp_imm = client.post('/api/subscription/cancel', json={
            'cancel_type': 'immediate',
            'reason': 'Accidental purchase',
            'feedback': 'Please refund'
        })
        self.assertEqual(resp_imm.status_code, 200)
        data_imm = resp_imm.get_json()
        self.assertTrue(data_imm['ok'])
        self.assertEqual(data_imm['cancel_type'], 'immediate')

        sub_after = get_user_subscription('test_subscriber', get_db)
        self.assertIsNone(sub_after)

    def test_11_free_trial_redemption(self):
        """Test 7-day Normal Pack free trial redemption and one-time limit."""
        client = self.app.test_client()
        self._login_as(client, 'test_trial_user')

        resp = client.post('/api/subscription/claim-trial')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['ok'])

        sub = get_user_subscription('test_trial_user', get_db)
        self.assertIsNotNone(sub)
        self.assertEqual(sub['plan_type'], 'normal')
        self.assertEqual(sub['price_paid'], 0.0)
        self.assertEqual(sub['is_trial'], 1)

        resp2 = client.post('/api/subscription/claim-trial')
        self.assertEqual(resp2.status_code, 400)

    def test_12_subscription_lifecycle_milestones_and_grace_period(self):
        """Test scheduled background worker milestone reminders without duplicates."""
        now = datetime.now()
        exp_7d = (now + timedelta(days=5, hours=2)).strftime('%Y-%m-%d %H:%M:%S')

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            INSERT INTO subscriptions 
            (username, plan_type, billing_cycle, price_paid, max_quality, status, expires_at, reminded_7d)
            VALUES ('test_trial_user', 'normal', 'monthly', 149.0, '720p', 'active', ?, 0)
        """, (exp_7d,))
        conn.commit()
        conn.close()

        notifs_sent = []
        def mock_push(username, msg, link):
            notifs_sent.append((username, msg))

        run_subscription_lifecycle_checks(get_db, push_notif_fn=mock_push)
        self.assertTrue(any('expires in' in m[1] for m in notifs_sent))

        notifs_sent.clear()
        run_subscription_lifecycle_checks(get_db, push_notif_fn=mock_push)
        self.assertEqual(len(notifs_sent), 0)

    def test_13_admin_subscription_portal(self):
        """Test admin subscriptions dashboard, granting complimentary subscription, and expiry extension."""
        client = self.app.test_client()
        self._login_as(client, 'admin', is_admin=1)

        resp = client.get('/admin/subscriptions')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Subscription', resp.data)

        resp_grant = client.post('/admin/subscriptions/grant', data={
            'username': 'test_subscriber',
            'plan_type': 'super',
            'duration_days': '90'
        }, follow_redirects=True)
        self.assertEqual(resp_grant.status_code, 200)

        granted_sub = get_user_subscription('test_subscriber', get_db)
        self.assertIsNotNone(granted_sub)
        self.assertEqual(granted_sub['plan_type'], 'super')
        self.assertEqual(granted_sub['payment_method'], 'Admin Complimentary')
        self.assertGreater(granted_sub['days_left'], 80)

        resp_ext = client.post('/admin/subscriptions/extend', data={
            'subscription_id': str(granted_sub['id']),
            'extra_days': '30'
        }, follow_redirects=True)
        self.assertEqual(resp_ext.status_code, 200)

        extended_sub = get_user_subscription('test_subscriber', get_db)
        self.assertGreater(extended_sub['days_left'], 110)


    # =========================================================================
    # ANNUAL-TO-MONTHLY SUBSCRIPTION SWITCHING TESTS (6 SCENARIOS)
    # =========================================================================

    def test_14_annual_user_selects_monthly_within_7_days(self):
        """Test Scenario 1: Annual user selects Monthly within 7 days.
        Backend rejects direct switch/purchase with annual_conflict, displays 7-day eligibility,
        and leaves Annual subscription unchanged."""
        client = self.app.test_client()
        self._login_as(client, 'test_subscriber')

        # Create active annual subscription created 2 days ago
        now = datetime.now()
        sub_id = self._create_active_sub(
            username='test_subscriber',
            plan_type='super',
            billing_cycle='yearly',
            started_at=now - timedelta(days=2),
            expires_at=now + timedelta(days=363)
        )

        # Attempt to create order for Monthly plan
        resp = client.post('/api/subscription/create-order', json={
            'plan_type': 'normal',
            'billing_cycle': 'monthly'
        })
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertFalse(data['ok'])
        self.assertTrue(data.get('annual_conflict'))
        self.assertEqual(data.get('error'), 'Already Subscribed to Annual Plan!')
        self.assertTrue(data.get('is_eligible'))
        self.assertEqual(data.get('days_remaining'), 5)
        self.assertIn('within 7 days', data.get('message'))

        # Ensure existing Annual subscription is still intact and active
        sub = get_user_subscription('test_subscriber', get_db)
        self.assertIsNotNone(sub)
        self.assertEqual(sub['id'], sub_id)
        self.assertEqual(sub['billing_cycle'], 'yearly')
        self.assertEqual(sub['status'], 'active')

    def test_15_annual_user_selects_monthly_after_7_days(self):
        """Test Scenario 2: Annual user selects Monthly after 7 days.
        Backend rejects with annual_conflict, reports eligibility expired,
        and prevents cancellation with refund."""
        client = self.app.test_client()
        self._login_as(client, 'test_subscriber')

        # Create active annual subscription created 10 days ago (past 7-day window)
        now = datetime.now()
        sub_id = self._create_active_sub(
            username='test_subscriber',
            plan_type='super',
            billing_cycle='yearly',
            started_at=now - timedelta(days=10),
            expires_at=now + timedelta(days=355)
        )

        # Attempt to create order for Monthly plan
        resp = client.post('/api/subscription/create-order', json={
            'plan_type': 'normal',
            'billing_cycle': 'monthly'
        })
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertFalse(data['ok'])
        self.assertTrue(data.get('annual_conflict'))
        self.assertFalse(data.get('is_eligible'))
        self.assertIn('Eligibility period expired', data.get('remaining_str'))

        # Verify that immediate cancellation with refund is blocked
        resp_cancel = client.post('/api/subscription/cancel', json={
            'cancel_type': 'immediate',
            'reason': 'Want refund after 10 days'
        })
        self.assertEqual(resp_cancel.status_code, 400)
        cancel_data = resp_cancel.get_json()
        self.assertFalse(cancel_data['ok'])
        self.assertFalse(cancel_data.get('can_cancel_with_refund', True))

        # Ensure Annual subscription remains active
        sub = get_user_subscription('test_subscriber', get_db)
        self.assertIsNotNone(sub)
        self.assertEqual(sub['id'], sub_id)
        self.assertEqual(sub['status'], 'active')

    def test_16_user_cancels_annual_subscription_within_7_days(self):
        """Test Scenario 3: User cancels Annual subscription within 7 days.
        Immediate cancellation processes eligible refund and terminates subscription."""
        client = self.app.test_client()
        self._login_as(client, 'test_subscriber')

        now = datetime.now()
        sub_id = self._create_active_sub(
            username='test_subscriber',
            plan_type='super',
            billing_cycle='yearly',
            started_at=now - timedelta(days=1),
            expires_at=now + timedelta(days=364)
        )

        resp = client.post('/api/subscription/cancel', json={
            'cancel_type': 'immediate',
            'reason': 'Switching to Monthly Plan'
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['ok'])
        self.assertGreater(data.get('refund_amount', 0), 0)

        # Verify database record
        conn = get_db(row_factory=True)
        c = conn.cursor()
        c.execute("SELECT status, cancel_type, refund_status FROM subscriptions WHERE id = ?", (sub_id,))
        row = dict(c.fetchone())
        conn.close()
        self.assertEqual(row['status'], 'cancelled')
        self.assertEqual(row['cancel_type'], 'immediate')
        self.assertEqual(row['refund_status'], 'processed')

        # Active subscription query now returns None (terminated)
        self.assertIsNone(get_user_subscription('test_subscriber', get_db))

    def test_17_user_attempts_monthly_purchase_while_cancellation_is_pending(self):
        """Test Scenario 4: User attempts Monthly purchase while cancellation is pending.
        Backend rejects purchase requests until cancellation reaches final terminated state."""
        client = self.app.test_client()
        self._login_as(client, 'test_subscriber')

        now = datetime.now()
        sub_id = self._create_active_sub(
            username='test_subscriber',
            plan_type='super',
            billing_cycle='yearly',
            started_at=now - timedelta(days=2),
            expires_at=now + timedelta(days=363)
        )

        # Simulate pending cancellation state
        conn = get_db()
        c = conn.cursor()
        c.execute("UPDATE subscriptions SET status = 'cancellation_pending', refund_status = 'pending' WHERE id = ?", (sub_id,))
        conn.commit()
        conn.close()

        # Attempt to create order for Monthly plan
        resp = client.post('/api/subscription/create-order', json={
            'plan_type': 'normal',
            'billing_cycle': 'monthly'
        })
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertFalse(data['ok'])
        self.assertTrue(data.get('pending_cancellation'))
        self.assertIn('pending', data.get('error').lower())

        # Attempt direct payment verification for Monthly plan
        resp_pay = client.post('/api/subscription/verify-payment', json={
            'order_id': 'ORD-PENDING-99',
            'plan_type': 'normal',
            'billing_cycle': 'monthly'
        })
        self.assertEqual(resp_pay.status_code, 400)
        pay_data = resp_pay.get_json()
        self.assertTrue(pay_data.get('pending_cancellation'))

    def test_18_user_purchases_monthly_after_successful_cancellation(self):
        """Test Scenario 5: User purchases Monthly after successful cancellation.
        Once the Annual subscription is terminated, user can purchase Monthly plan cleanly."""
        client = self.app.test_client()
        self._login_as(client, 'test_subscriber')

        # Previous Annual subscription is already cancelled and terminated
        now = datetime.now()
        sub_id = self._create_active_sub(
            username='test_subscriber',
            plan_type='super',
            billing_cycle='yearly',
            started_at=now - timedelta(days=1),
            expires_at=now + timedelta(days=364)
        )
        conn = get_db()
        c = conn.cursor()
        c.execute("UPDATE subscriptions SET status = 'cancelled', cancel_type = 'immediate', refund_status = 'processed' WHERE id = ?", (sub_id,))
        conn.commit()
        conn.close()

        # 1. Create order for Normal Monthly plan
        resp_order = client.post('/api/subscription/create-order', json={
            'plan_type': 'normal',
            'billing_cycle': 'monthly'
        })
        self.assertEqual(resp_order.status_code, 200)
        order_data = resp_order.get_json()
        self.assertTrue(order_data['ok'])

        # 2. Verify payment for Normal Monthly plan
        resp_pay = client.post('/api/subscription/verify-payment', json={
            'order_id': order_data['order_id'],
            'plan_type': 'normal',
            'billing_cycle': 'monthly',
            'payment_method': 'Simulated UPI'
        })
        self.assertEqual(resp_pay.status_code, 200)
        pay_data = resp_pay.get_json()
        self.assertTrue(pay_data['ok'])

        # 3. Verify user's current subscription is now Normal Monthly
        curr_sub = get_user_subscription('test_subscriber', get_db)
        self.assertIsNotNone(curr_sub)
        self.assertEqual(curr_sub['plan_type'], 'normal')
        self.assertEqual(curr_sub['billing_cycle'], 'monthly')
        self.assertEqual(curr_sub['status'], 'active')

    def test_19_existing_annual_subscription_remains_unchanged_on_dismiss(self):
        """Test Scenario 6: Existing Annual subscription remains unchanged when user dismisses popup.
        Selecting 'Keep Annual Subscription' preserves all active perks, billing cycle, and expiration."""
        client = self.app.test_client()
        self._login_as(client, 'test_subscriber')

        now = datetime.now()
        sub_id = self._create_active_sub(
            username='test_subscriber',
            plan_type='super',
            billing_cycle='yearly',
            started_at=now - timedelta(days=3),
            expires_at=now + timedelta(days=362)
        )

        sub_before = get_user_subscription('test_subscriber', get_db)
        self.assertEqual(sub_before['id'], sub_id)
        self.assertEqual(sub_before['billing_cycle'], 'yearly')
        self.assertEqual(sub_before['status'], 'active')

        # User views subscription status and retains annual plan
        resp = client.get('/api/subscription/annual-status')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['ok'])
        self.assertTrue(data['is_annual'])

        # Verify annual sub in database is 100% identical and active
        sub_after = get_user_subscription('test_subscriber', get_db)
        self.assertEqual(sub_after['id'], sub_before['id'])
        self.assertEqual(sub_after['plan_type'], sub_before['plan_type'])
        self.assertEqual(sub_after['billing_cycle'], sub_before['billing_cycle'])
        self.assertEqual(sub_after['expires_at'], sub_before['expires_at'])
        self.assertEqual(sub_after['status'], 'active')


    def test_20_annual_user_monthly_purchase_strictly_blocked(self):
        """Requirement 1: User bought Annual sub -> disable/block Monthly sub purchases."""
        client = self.app.test_client()
        self._login_as(client, 'test_subscriber')

        now = datetime.now()
        self._create_active_sub(
            username='test_subscriber',
            plan_type='super',
            billing_cycle='yearly',
            started_at=now - timedelta(days=2),
            expires_at=now + timedelta(days=363)
        )

        resp = client.post('/api/subscription/create-order', json={
            'plan_type': 'normal',
            'billing_cycle': 'monthly'
        })
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertFalse(data['ok'])
        self.assertTrue(data.get('annual_conflict'))
        self.assertIn('Already Subscribed to Annual Plan!', data.get('error'))

    def test_21_monthly_user_upgrading_to_annual_gets_credit_deducted(self):
        """Requirement 2: User bought Monthly sub -> reduce Annual sub amount by monthly plan price for upgrade."""
        client = self.app.test_client()
        self._login_as(client, 'test_subscriber')

        now = datetime.now()
        # Active Normal Monthly subscription paid ₹149.0
        self._create_active_sub(
            username='test_subscriber',
            plan_type='normal',
            billing_cycle='monthly',
            price=149.0,
            started_at=now - timedelta(days=5),
            expires_at=now + timedelta(days=25)
        )

        # Create order for Super Annual (base price ₹1499.0)
        resp_order = client.post('/api/subscription/create-order', json={
            'plan_type': 'super',
            'billing_cycle': 'yearly'
        })
        self.assertEqual(resp_order.status_code, 200)
        order_data = resp_order.get_json()
        self.assertTrue(order_data['ok'])
        # Upgrading gives ₹149.0 monthly credit: ₹1499 - ₹149 = ₹1350
        self.assertEqual(order_data.get('upgrade_credit'), 149.0)
        self.assertEqual(order_data.get('amount_inr'), 1350.0)

        # Complete payment verification
        resp_pay = client.post('/api/subscription/verify-payment', json={
            'order_id': order_data['order_id'],
            'plan_type': 'super',
            'billing_cycle': 'yearly',
            'payment_method': 'UPI'
        })
        self.assertEqual(resp_pay.status_code, 200)

        # Verify new subscription is active Super Annual
        curr_sub = get_user_subscription('test_subscriber', get_db)
        self.assertIsNotNone(curr_sub)
        self.assertEqual(curr_sub['plan_type'], 'super')
        self.assertEqual(curr_sub['billing_cycle'], 'yearly')
        self.assertEqual(curr_sub['price_paid'], 1350.0)

    def test_22_annual_cancellation_daily_charge_deduction(self):
        """Requirement 4: Annual cancellation within 7 days applies daily charges + fee and refunds remaining."""
        client = self.app.test_client()
        self._login_as(client, 'test_subscriber')

        now = datetime.now()
        # Active Super Annual subscription created 3 days ago (price ₹1499.0)
        sub_id = self._create_active_sub(
            username='test_subscriber',
            plan_type='super',
            billing_cycle='yearly',
            price=1499.0,
            started_at=now - timedelta(days=3),
            expires_at=now + timedelta(days=362)
        )

        resp = client.post('/api/subscription/cancel', json={
            'cancel_type': 'immediate',
            'reason': 'Switching to monthly within 7 days'
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['ok'])
        # 3 days usage fee (~₹12.32) + 5% fee (₹74.95) = ₹87.27 cut -> ~₹1411.73 refunded
        refund = data.get('refund_amount', 0.0)
        self.assertGreater(refund, 1380.0)
        self.assertLess(refund, 1450.0)

    def test_23_annual_cancellation_locked_after_7_days(self):
        """Requirement 4 (continued): Annual cancellation with refund is locked after 7 days."""
        client = self.app.test_client()
        self._login_as(client, 'test_subscriber')

        now = datetime.now()
        # Active Super Annual subscription created 12 days ago (> 7-day window)
        self._create_active_sub(
            username='test_subscriber',
            plan_type='super',
            billing_cycle='yearly',
            price=1499.0,
            started_at=now - timedelta(days=12),
            expires_at=now + timedelta(days=353)
        )

        resp = client.post('/api/subscription/cancel', json={
            'cancel_type': 'immediate',
            'reason': 'Attempting cancellation after 12 days'
        })
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertFalse(data['ok'])
        self.assertTrue(data.get('is_locked'))
        self.assertFalse(data.get('can_cancel_with_refund', True))

    def test_24_no_account_suspension_on_cancellations(self):
        """Verify that multiple subscription cancellations do NOT suspend or ban the user's account."""
        client = self.app.test_client()
        self._login_as(client, 'test_subscriber')

        now = datetime.now()

        # Cancellation 1
        sub1 = self._create_active_sub(username='test_subscriber', started_at=now - timedelta(days=1))
        r1 = client.post('/api/subscription/cancel', json={'cancel_type': 'immediate', 'reason': 'Cancel 1'})
        self.assertEqual(r1.status_code, 200)
        d1 = r1.get_json()
        self.assertFalse(d1.get('account_banned', False))

        # Cancellation 2
        sub2 = self._create_active_sub(username='test_subscriber', started_at=now - timedelta(days=1))
        r2 = client.post('/api/subscription/cancel', json={'cancel_type': 'immediate', 'reason': 'Cancel 2'})
        self.assertEqual(r2.status_code, 200)
        d2 = r2.get_json()
        self.assertFalse(d2.get('account_banned', False))

        # Cancellation 3 -> User must NOT be suspended or banned!
        sub3 = self._create_active_sub(username='test_subscriber', started_at=now - timedelta(days=1))
        r3 = client.post('/api/subscription/cancel', json={'cancel_type': 'immediate', 'reason': 'Cancel 3'})
        self.assertEqual(r3.status_code, 200)
        d3 = r3.get_json()
        self.assertFalse(d3.get('account_banned', False))
        self.assertNotIn('permanently suspended', d3.get('message', '').lower())

        # Verify user record in database remains active and not banned
        conn = get_db(row_factory=True)
        c = conn.cursor()
        c.execute("SELECT is_banned, is_active FROM users WHERE username = 'test_subscriber'")
        urow = dict(c.fetchone())
        conn.close()
        self.assertEqual(urow['is_banned'], 0)
        self.assertEqual(urow['is_active'], 1)

    def test_25_super_user_cannot_downgrade_to_normal(self):
        """Check the flow: User with active Super VIP cannot purchase Normal pack (already covered)."""
        client = self.app.test_client()
        self._login_as(client, 'test_subscriber')

        now = datetime.now()
        # User has active Super Annual
        self._create_active_sub(
            username='test_subscriber',
            plan_type='super',
            billing_cycle='yearly',
            price_paid=1499.0,
            started_at=now - timedelta(days=2),
            expires_at=now + timedelta(days=363)
        )

        # Attempt to create order for Normal Pack (Yearly or Monthly)
        r_create = client.post('/api/subscription/create-order', json={
            'plan_type': 'normal',
            'billing_cycle': 'yearly'
        })
        self.assertEqual(r_create.status_code, 400)
        d_create = r_create.get_json()
        self.assertFalse(d_create.get('ok'))
        self.assertIn('Super VIP', d_create.get('error'))

        # Attempt to verify payment for Normal Pack
        r_verify = client.post('/api/subscription/verify-payment', json={
            'plan_type': 'normal',
            'billing_cycle': 'yearly',
            'payment_id': 'PAY-TEST-DOWNGRADE'
        })
        self.assertEqual(r_verify.status_code, 400)
        d_verify = r_verify.get_json()
        self.assertFalse(d_verify.get('ok'))
        self.assertIn('Super VIP', d_verify.get('error'))

    def test_26_subscriptions_page_shows_covered_for_super_vip_user(self):
        """Verify that for an active Super Annual VIP user, subscriptions page does not offer 'Subscribe Yearly • ₹899' on Normal pack."""
        client = self.app.test_client()
        self._login_as(client, 'test_subscriber')

        now = datetime.now()
        self._create_active_sub(
            username='test_subscriber',
            plan_type='super',
            billing_cycle='yearly',
            price_paid=1499.0,
            started_at=now - timedelta(days=1),
            expires_at=now + timedelta(days=364)
        )

        r = client.get('/plans')
        self.assertEqual(r.status_code, 200)
        html = r.get_data(as_text=True)

        # Must show covered status for Normal pack
        self.assertIn('Covered by Active Super VIP', html)
        self.assertIn('Included in Super VIP Pass', html)

        # Must have cycle selectors on both cards
        self.assertIn('normalCycleSelector', html)
        self.assertIn('superCycleSelector', html)

if __name__ == '__main__':

    unittest.main()
