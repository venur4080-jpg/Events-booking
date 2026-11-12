"""
test_platform_pillars.py - Comprehensive integration tests for:
1. Distorted SVG CAPTCHA (login/register/forgot), brute-force 429 rate limiting & CSRF enforcement
2. RFC-6238 TOTP 2FA setup/login/backup codes & active session revocation
3. Priority Waitlist join & automatic FIFO/VIP promotion on unregister
4. Self-service cryptographic Ticket Transfer & old QR invalidation
5. Call for Speakers (CfP) submission & host accept -> auto agenda session creation
6. Recurring Event Series generation & discounted Season Pass checkout
7. Ticket Add-Ons inventory, tiered cancellation refunds to Event Wallet & wallet redemption
8. Outgoing Host Webhooks (HMAC-SHA256) & FastAPI /api/v1/events + realtime live broadcast
"""
import os
os.environ['TESTING'] = '1'
import sys
import json
import sqlite3
import unittest
from datetime import datetime, timedelta

_backend_dir = os.path.dirname(os.path.abspath(__file__))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from app import (
    app,
    init_db,
    get_totp_code,
    reset_all_login_rate_limits,
    sign_webhook_payload,
)

DB_PATH = os.path.join(_backend_dir, 'users.db')


class PlatformPillarsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['ENFORCE_CSRF'] = False
        reset_all_login_rate_limits()
        self.client = self.app.test_client()

    def tearDown(self):
        self.app.config['ENFORCE_CSRF'] = False
        reset_all_login_rate_limits()

    def _create_test_user(self, username, email, uid, pwd='Password123!', role='user', is_admin=0):
        from flask_bcrypt import Bcrypt
        bcrypt = Bcrypt()
        pwd_hash = bcrypt.generate_password_hash(pwd).decode('utf-8')
        conn = sqlite3.connect(DB_PATH, timeout=15)
        c = conn.cursor()
        c.execute("DELETE FROM users WHERE username = ?", (username,))
        c.execute(
            """INSERT INTO users (username, password, full_name, email, phone, college_id, user_id, role, is_admin, is_active)
               VALUES (?, ?, ?, ?, '9876543210', 'COL-PILLAR', ?, ?, ?, 1)""",
            (username, pwd_hash, username.title(), email, uid, role, is_admin)
        )
        conn.commit()
        conn.close()

    def _create_test_event(self, title="Pillar Test Event", date_str=None, price="₹1000", seats_total=50, seats_filled=0, refund_policy="flexible", allow_transfer=1):
        if not date_str:
            future = datetime.now() + timedelta(days=10)
            date_str = future.strftime("%b %d, %Y")
        conn = sqlite3.connect(DB_PATH, timeout=15)
        c = conn.cursor()
        c.execute(
            """INSERT INTO events (title, date, price, seats_total, seats_filled, venue, venue_address, desc, purpose, outcome, color, image, refund_policy, allow_transfer)
               VALUES (?, ?, ?, ?, ?, 'Main Hall', 'Tech Campus', 'Pillar test description', 'Networking', 'Learn', '#008be3', 'https://example.com/e.jpg', ?, ?)""",
            (title, date_str, price, seats_total, seats_filled, refund_policy, allow_transfer)
        )
        eid = c.lastrowid
        conn.commit()
        conn.close()
        return eid

    def test_01_svg_captcha_registration_forgot_rate_limit_and_csrf(self):
        reset_all_login_rate_limits()
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'<svg', resp.data)
        with self.client.session_transaction() as sess:
            login_cap = sess.get('captcha_answer', '')
            reg_cap = sess.get('reg_captcha_answer', '')
        self.assertEqual(len(login_cap), 5)
        self.assertEqual(len(reg_cap), 5)

        try:
            # 1. Registration rejects wrong reg_captcha
            resp_bad_reg = self.client.post('/', data={
                'action': 'register',
                'reg_username': 'pillar_reg_user',
                'reg_password': 'Password123!',
                'reg_confirm_password': 'Password123!',
                'first_name': 'Pillar',
                'last_name': 'User',
                'email': 'pillar_reg@example.com',
                'phone': '9876543210',
                'address': '123 Main St',
                'city': 'Bangalore',
                'state': 'Karnataka',
                'pincode': '560001',
                'reg_captcha': '99999' if reg_cap != '99999' else '11111'
            })
            self.assertIn(b'Invalid or missing registration CAPTCHA', resp_bad_reg.data)

            # 2. Valid reg_captcha creates account
            self.client.get('/')
            with self.client.session_transaction() as sess:
                reg_cap2 = sess['reg_captcha_answer']
            resp_ok_reg = self.client.post('/', data={
                'action': 'register',
                'reg_username': 'pillar_reg_user',
                'reg_password': 'Password123!',
                'reg_confirm_password': 'Password123!',
                'first_name': 'Pillar',
                'last_name': 'User',
                'email': 'pillar_reg@example.com',
                'phone': '9876543210',
                'address': '123 Main St',
                'city': 'Bangalore',
                'state': 'Karnataka',
                'pincode': '560001',
                'reg_captcha': reg_cap2
            })
            self.assertIn(b'Registration successful', resp_ok_reg.data)

            # 3. Brute-force 6th wrong attempt triggers 429 rate limit
            for attempt in range(6):
                with self.client.session_transaction() as sess:
                    sess['captcha_answer'] = '54321'
                r_bf = self.client.post('/', data={
                    'action': 'login',
                    'username': 'pillar_reg@example.com',
                    'password': 'WrongPassword!',
                    'captcha': '54321'
                })
                if attempt < 5:
                    self.assertEqual(r_bf.status_code, 200)
                else:
                    self.assertEqual(r_bf.status_code, 429)
                    self.assertIn(b'Too many failed login attempts', r_bf.data)

            reset_all_login_rate_limits()

            # 4. Strict CSRF check when ENFORCE_CSRF=True
            self.app.config['ENFORCE_CSRF'] = True
            self.client.get('/')
            with self.client.session_transaction() as sess:
                csrf_tok = sess.get('_csrf_token', '')
                cap_tok = sess.get('captcha_answer', '')
            self.assertTrue(len(csrf_tok) >= 16)

            r_no_csrf = self.client.post('/', data={
                'action': 'login',
                'username': 'pillar_reg@example.com',
                'password': 'Password123!',
                'captcha': cap_tok
            })
            self.assertEqual(r_no_csrf.status_code, 403)

            with self.client.session_transaction() as sess:
                sess['captcha_answer'] = cap_tok
            r_with_csrf = self.client.post('/', data={
                'action': 'login',
                'username': 'pillar_reg@example.com',
                'password': 'Password123!',
                'captcha': cap_tok,
                'csrf_token': csrf_tok
            }, follow_redirects=False)
            self.assertEqual(r_with_csrf.status_code, 303)
        finally:
            self.app.config['ENFORCE_CSRF'] = False
            conn = sqlite3.connect(DB_PATH, timeout=15)
            conn.cursor().execute("DELETE FROM users WHERE username = 'pillar_reg_user'")
            conn.commit()
            conn.close()

    def test_02_totp_2fa_setup_login_backup_code_and_session_revoke(self):
        uname = 'pillar_2fa_user'
        self._create_test_user(uname, 'pillar_2fa@example.com', 'UID-8101')
        try:
            with self.client.session_transaction() as sess:
                sess['loggedin'] = True
                sess['username'] = uname
                sess['role'] = 'user'
                sess['session_token'] = 'cur-tok-1'

            r_setup = self.client.post('/api/settings/2fa/setup')
            self.assertEqual(r_setup.status_code, 200)
            sdata = r_setup.get_json()
            self.assertTrue(sdata['ok'])
            secret = sdata['secret']
            backup_code = sdata['backup_codes'][0]
            self.assertTrue(sdata['qr_data_uri'].startswith('data:image/png;base64,'))

            otp = get_totp_code(secret)
            r_enable = self.client.post('/api/settings/2fa/verify-enable', json={'code': otp})
            self.assertEqual(r_enable.status_code, 200)
            self.assertTrue(r_enable.get_json()['ok'])

            # Logout and sign in -> redirected to /verify-2fa
            self.client.get('/logout')
            self.client.get('/')
            with self.client.session_transaction() as sess:
                cap = sess['captcha_answer']
            r_login = self.client.post('/', data={
                'action': 'login',
                'username': 'pillar_2fa@example.com',
                'password': 'Password123!',
                'captcha': cap
            }, follow_redirects=False)
            self.assertEqual(r_login.status_code, 303)
            self.assertIn('/verify-2fa', r_login.headers.get('Location', ''))

            with self.client.session_transaction() as sess:
                self.assertFalse(sess.get('loggedin'))

            # Wrong TOTP stays blocked
            r_bad_otp = self.client.post('/verify-2fa', data={'code': '000000'})
            self.assertEqual(r_bad_otp.status_code, 200)
            self.assertIn(b'Invalid authentication code', r_bad_otp.data)

            # Valid backup code works & is consumed
            r_ok_2fa = self.client.post('/verify-2fa', data={'code': backup_code}, follow_redirects=False)
            self.assertEqual(r_ok_2fa.status_code, 303)
            self.assertIn('/dashboard', r_ok_2fa.headers.get('Location', ''))

            # Insert second active session and revoke others
            conn = sqlite3.connect(DB_PATH, timeout=15)
            conn.cursor().execute(
                "INSERT INTO user_login_sessions (session_token, username, ip_address, user_agent, is_active) VALUES ('old-other-tok', ?, '10.0.0.5', 'OtherDevice', 1)",
                (uname,)
            )
            conn.commit()
            conn.close()

            r_rev = self.client.post('/settings/sessions/revoke-others', headers={'Accept': 'application/json'})
            self.assertEqual(r_rev.status_code, 200)
            self.assertGreaterEqual(r_rev.get_json()['revoked_count'], 1)

            conn = sqlite3.connect(DB_PATH, timeout=15)
            row = conn.cursor().execute("SELECT is_active FROM user_login_sessions WHERE session_token = 'old-other-tok'").fetchone()
            conn.close()
            self.assertEqual(row[0], 0)
        finally:
            conn = sqlite3.connect(DB_PATH, timeout=15)
            c = conn.cursor()
            c.execute("DELETE FROM user_2fa_settings WHERE username = ?", (uname,))
            c.execute("DELETE FROM user_login_sessions WHERE username = ?", (uname,))
            c.execute("DELETE FROM users WHERE username = ?", (uname,))
            conn.commit()
            conn.close()

    def test_03_waitlist_vip_priority_and_auto_promotion(self):
        self._create_test_user('wl_holder', 'wl_holder@example.com', 'UID-8201')
        self._create_test_user('wl_regular', 'wl_regular@example.com', 'UID-8202')
        self._create_test_user('wl_vip', 'wl_vip@example.com', 'UID-8203')
        eid = self._create_test_event(title="Sold Out Waitlist Event", price="Free", seats_total=1, seats_filled=0)
        try:
            # Holder books the last seat
            with self.client.session_transaction() as sess:
                sess['loggedin'] = True
                sess['username'] = 'wl_holder'
            self.client.post(f'/register/{eid}', data={
                'full_name': 'Holder', 'email': 'wl_holder@example.com', 'phone': '9876543210', 'pass_type': 'in_person'
            })

            # Mark wl_vip as active subscriber
            conn = sqlite3.connect(DB_PATH, timeout=15)
            conn.cursor().execute(
                "INSERT INTO subscriptions (username, plan_type, billing_cycle, price_paid, expires_at, status) VALUES ('wl_vip', 'vip_all', 'monthly', 499, '2029-12-31', 'active')"
            )
            conn.commit()
            conn.close()

            # Regular joins waitlist first
            with self.client.session_transaction() as sess:
                sess['loggedin'] = True
                sess['username'] = 'wl_regular'
            r1 = self.client.post(f'/api/event/{eid}/waitlist/join').get_json()
            self.assertTrue(r1['ok'])
            self.assertEqual(r1['priority_score'], 0)

            # VIP joins second -> overtakes regular at position 1
            with self.client.session_transaction() as sess:
                sess['loggedin'] = True
                sess['username'] = 'wl_vip'
            r2 = self.client.post(f'/api/event/{eid}/waitlist/join').get_json()
            self.assertTrue(r2['ok'])
            self.assertEqual(r2['priority_score'], 10)
            self.assertEqual(r2['position'], 1)

            # Holder unregisters -> VIP is automatically promoted
            with self.client.session_transaction() as sess:
                sess['loggedin'] = True
                sess['username'] = 'wl_holder'
            self.client.post(f'/unregister/{eid}', data={'reason': 'Schedule change'})

            with self.client.session_transaction() as sess:
                sess['loggedin'] = True
                sess['username'] = 'wl_vip'
            st_vip = self.client.get(f'/api/event/{eid}/waitlist/status').get_json()
            self.assertEqual(st_vip['status'], 'promoted')
        finally:
            conn = sqlite3.connect(DB_PATH, timeout=15)
            c = conn.cursor()
            c.execute("DELETE FROM event_waitlist WHERE event_id = ?", (eid,))
            c.execute("DELETE FROM registrations WHERE event_id = ?", (eid,))
            c.execute("DELETE FROM live_stream_passes WHERE event_id = ?", (eid,))
            c.execute("DELETE FROM events WHERE id = ?", (eid,))
            c.execute("DELETE FROM subscriptions WHERE username = 'wl_vip'")
            c.execute("DELETE FROM users WHERE username IN ('wl_holder', 'wl_regular', 'wl_vip')")
            conn.commit()
            conn.close()

    def test_04_ticket_transfer_and_old_qr_invalidation(self):
        self._create_test_user('trf_sender', 'trf_sender@example.com', 'UID-8301')
        self._create_test_user('trf_recipient', 'trf_recipient@example.com', 'UID-8302')
        eid = self._create_test_event(title="Transferable Summit", price="Free", allow_transfer=1)
        try:
            with self.client.session_transaction() as sess:
                sess['loggedin'] = True
                sess['username'] = 'trf_sender'
            self.client.post(f'/register/{eid}', data={
                'full_name': 'Sender', 'email': 'trf_sender@example.com', 'phone': '9876543210', 'pass_type': 'in_person'
            })
            conn = sqlite3.connect(DB_PATH, timeout=15)
            old_code = conn.cursor().execute("SELECT ticket_code FROM registrations WHERE username='trf_sender' AND event_id=?", (eid,)).fetchone()[0]
            conn.close()

            r_trf = self.client.post(f'/api/ticket/{old_code}/transfer', json={'recipient_identifier': 'trf_recipient'})
            self.assertEqual(r_trf.status_code, 200)
            tdata = r_trf.get_json()
            self.assertTrue(tdata['ok'])
            new_code = tdata['new_ticket_code']
            self.assertTrue(new_code.startswith('TRF-'))

            # Host verifies OLD ticket -> REJECTED as transferred
            with self.client.session_transaction() as sess:
                sess['loggedin'] = True
                sess['username'] = 'admin'
                sess['role'] = 'host'
                sess['is_admin'] = True
            r_old_scan = self.client.post('/api/verify_ticket', json={'code': old_code})
            self.assertEqual(r_old_scan.status_code, 400)
            self.assertTrue(r_old_scan.get_json().get('is_transferred'))

            # Host verifies NEW ticket -> SUCCEEDS
            r_new_scan = self.client.post('/api/verify_ticket', json={'code': new_code})
            self.assertEqual(r_new_scan.status_code, 200)
            self.assertTrue(r_new_scan.get_json()['ok'])
        finally:
            conn = sqlite3.connect(DB_PATH, timeout=15)
            c = conn.cursor()
            c.execute("DELETE FROM registrations WHERE event_id = ?", (eid,))
            c.execute("DELETE FROM live_stream_passes WHERE event_id = ?", (eid,))
            c.execute("DELETE FROM events WHERE id = ?", (eid,))
            c.execute("DELETE FROM users WHERE username IN ('trf_sender', 'trf_recipient')")
            conn.commit()
            conn.close()

    def test_05_cfp_submission_and_auto_agenda_creation(self):
        self._create_test_user('cfp_speaker', 'cfp_speaker@example.com', 'UID-8401')
        eid = self._create_test_event(title="CfP Dev Conference")
        try:
            with self.client.session_transaction() as sess:
                sess['loggedin'] = True
                sess['username'] = 'cfp_speaker'
                sess['role'] = 'user'
            r_sub = self.client.post(f'/event/{eid}/cfp', data={
                'speaker_name': 'Dr. Ada Lovelace',
                'speaker_email': 'cfp_speaker@example.com',
                'talk_title': 'Deterministic Systems at Scale',
                'abstract': 'Architectural blueprint for zero-downtime systems.',
                'track_preference': 'Architecture Track',
                'session_duration_min': '45'
            }, follow_redirects=True)
            self.assertEqual(r_sub.status_code, 200)

            conn = sqlite3.connect(DB_PATH, timeout=15)
            prop_id = conn.cursor().execute("SELECT id FROM event_speaker_proposals WHERE event_id = ?", (eid,)).fetchone()[0]
            conn.close()

            with self.client.session_transaction() as sess:
                sess['loggedin'] = True
                sess['username'] = 'admin'
                sess['role'] = 'host'
                sess['is_admin'] = True
            r_rev = self.client.post(f'/api/event/{eid}/cfp/{prop_id}/review', json={'decision': 'accepted'})
            self.assertEqual(r_rev.status_code, 200)
            self.assertTrue(r_rev.get_json()['agenda_created'])

            conn = sqlite3.connect(DB_PATH, timeout=15)
            ag_row = conn.cursor().execute("SELECT title, speaker_name FROM event_agenda_sessions WHERE event_id = ?", (eid,)).fetchone()
            conn.close()
            self.assertIsNotNone(ag_row)
            self.assertEqual(ag_row[0], 'Deterministic Systems at Scale')
        finally:
            conn = sqlite3.connect(DB_PATH, timeout=15)
            c = conn.cursor()
            c.execute("DELETE FROM event_agenda_sessions WHERE event_id = ?", (eid,))
            c.execute("DELETE FROM event_agenda_tracks WHERE event_id = ?", (eid,))
            c.execute("DELETE FROM event_speaker_proposals WHERE event_id = ?", (eid,))
            c.execute("DELETE FROM events WHERE id = ?", (eid,))
            c.execute("DELETE FROM users WHERE username = 'cfp_speaker'")
            conn.commit()
            conn.close()

    def test_06_recurring_event_series_and_season_pass(self):
        self._create_test_user('series_buyer', 'series_buyer@example.com', 'UID-8501')
        sid = None
        created_eids = []
        try:
            with self.client.session_transaction() as sess:
                sess['loggedin'] = True
                sess['username'] = 'admin'
                sess['role'] = 'host'
                sess['is_admin'] = True
            r_add = self.client.post('/add_event', data={
                'title': 'Weekly AI Clinic',
                'category': 'AI & Machine Learning',
                'date': 'Nov 20, 2027',
                'time': '10:00 AM',
                'end_time': '12:00 PM',
                'price': '₹400',
                'seats_total': '60',
                'color': '#008be3',
                'image': 'https://example.com/ai.jpg',
                'venue': 'Lab 1',
                'venue_address': 'Bangalore',
                'purpose': 'Hands-on clinics',
                'outcome': 'Build RAG agents.',
                'recurrence_rule': 'weekly',
                'occurrence_count': '3',
                'series_discount': '25',
                'addon_name[]': ['Clinic Swag Pack'],
                'addon_price[]': ['150'],
                'addon_stock[]': ['40'],
            }, follow_redirects=False)
            self.assertIn(r_add.status_code, (200, 302, 303))

            conn = sqlite3.connect(DB_PATH, timeout=15)
            c = conn.cursor()
            srow = c.execute("SELECT id, total_sessions FROM event_series WHERE title = 'Weekly AI Clinic Series' ORDER BY id DESC LIMIT 1").fetchone()
            self.assertIsNotNone(srow)
            sid = srow[0]
            self.assertEqual(srow[1], 3)
            created_eids = [r[0] for r in c.execute("SELECT id FROM events WHERE series_id = ?", (sid,)).fetchall()]
            addon_cnt = c.execute("SELECT COUNT(*) FROM event_addons WHERE event_id IN ({})".format(','.join('?' for _ in created_eids)), tuple(created_eids)).fetchone()[0] if created_eids else 0
            conn.close()
            self.assertEqual(len(created_eids), 3)
            self.assertEqual(addon_cnt, 3)

            with self.client.session_transaction() as sess:
                sess['loggedin'] = True
                sess['username'] = 'series_buyer'
                sess['role'] = 'user'
            r_page = self.client.get(f'/series/{sid}')
            self.assertEqual(r_page.status_code, 200)
            r_book = self.client.post(f'/api/series/{sid}/book-season-pass', json={'use_wallet_credits': False})
            self.assertEqual(r_book.status_code, 200)
            bdata = r_book.get_json()
            self.assertTrue(bdata['ok'])
            self.assertEqual(bdata['booked_count'], 3)
            self.assertAlmostEqual(bdata['total_paid'], 900.0, places=2)
        finally:
            conn = sqlite3.connect(DB_PATH, timeout=15)
            c = conn.cursor()
            for eid in created_eids:
                c.execute("DELETE FROM event_addons WHERE event_id = ?", (eid,))
                c.execute("DELETE FROM registrations WHERE event_id = ?", (eid,))
                c.execute("DELETE FROM live_stream_passes WHERE event_id = ?", (eid,))
                c.execute("DELETE FROM events WHERE id = ?", (eid,))
            if sid:
                c.execute("DELETE FROM event_series WHERE id = ?", (sid,))
            c.execute("DELETE FROM users WHERE username = 'series_buyer'")
            conn.commit()
            conn.close()

    def test_07_addons_tiered_wallet_refund_and_redemption(self):
        self._create_test_user('wallet_user', 'wallet_user@example.com', 'UID-8601')
        eid_flex = self._create_test_event(title="Flexible Paid Expo", price="₹1000", refund_policy="flexible")
        eid_strict = self._create_test_event(title="Strict Concert", price="₹500", refund_policy="strict")
        try:
            with self.client.session_transaction() as sess:
                sess['loggedin'] = True
                sess['username'] = 'admin'
                sess['role'] = 'host'
                sess['is_admin'] = True
            r_addon = self.client.post(f'/api/event/{eid_flex}/addons', json={'name': 'Event Hoodie', 'price': 200, 'stock_total': 5})
            aid = r_addon.get_json()['addon_id']

            with self.client.session_transaction() as sess:
                sess['loggedin'] = True
                sess['username'] = 'wallet_user'
                sess['role'] = 'user'

            # Register with 2 hoodies -> 1000 + 2*200 = 1400
            self.client.post(f'/register/{eid_flex}', data={
                'full_name': 'Wallet User', 'email': 'wallet_user@example.com', 'phone': '9876543210',
                'pass_type': 'in_person', f'addon_qty_{aid}': '2'
            })

            conn = sqlite3.connect(DB_PATH, timeout=15)
            paid, add_tot = conn.cursor().execute("SELECT amount_paid, addons_total FROM registrations WHERE username='wallet_user' AND event_id=?", (eid_flex,)).fetchone()
            sold = conn.cursor().execute("SELECT stock_sold FROM event_addons WHERE id = ?", (aid,)).fetchone()[0]
            conn.close()
            self.assertAlmostEqual(paid, 1400.0, places=2)
            self.assertAlmostEqual(add_tot, 400.0, places=2)
            self.assertEqual(sold, 2)

            # Unregister >24h before event under 'flexible' policy -> 100% credit to wallet
            self.client.post(f'/unregister/{eid_flex}', data={'reason': 'Testing refund'})
            w_data = self.client.get('/api/wallet').get_json()
            self.assertAlmostEqual(w_data['balance'], 1400.0, places=2)

            # Strict event refund preview is 0
            r_prev = self.client.get(f'/api/event/{eid_strict}/refund-preview?amount_paid=500').get_json()
            self.assertEqual(r_prev['refund_amount'], 0.0)

            # Spend wallet credits on Strict event
            self.client.post(f'/register/{eid_strict}', data={
                'full_name': 'Wallet User', 'email': 'wallet_user@example.com', 'phone': '9876543210',
                'pass_type': 'in_person', 'use_wallet_credits': '1'
            })
            w_after = self.client.get('/api/wallet').get_json()
            self.assertAlmostEqual(w_after['balance'], 900.0, places=2)
        finally:
            conn = sqlite3.connect(DB_PATH, timeout=15)
            c = conn.cursor()
            c.execute("DELETE FROM registration_addons WHERE event_id IN (?, ?)", (eid_flex, eid_strict))
            c.execute("DELETE FROM event_addons WHERE event_id IN (?, ?)", (eid_flex, eid_strict))
            c.execute("DELETE FROM registrations WHERE event_id IN (?, ?)", (eid_flex, eid_strict))
            c.execute("DELETE FROM live_stream_passes WHERE event_id IN (?, ?)", (eid_flex, eid_strict))
            c.execute("DELETE FROM wallet_transactions WHERE username = 'wallet_user'")
            c.execute("DELETE FROM user_wallet WHERE username = 'wallet_user'")
            c.execute("DELETE FROM events WHERE id IN (?, ?)", (eid_flex, eid_strict))
            c.execute("DELETE FROM users WHERE username = 'wallet_user'")
            conn.commit()
            conn.close()

    def test_08_webhooks_hmac_and_fastapi_events_realtime(self):
        with self.client.session_transaction() as sess:
            sess['loggedin'] = True
            sess['username'] = 'admin'
            sess['role'] = 'host'
            sess['is_admin'] = True

        hook_id = None
        try:
            r_cr = self.client.post('/api/host/webhooks/create', json={
                'name': 'Mock Slack Ops',
                'target_url': 'http://mock-webhook.local/slack',
                'subscribed_events': 'ticket.booked,webhook.test'
            })
            self.assertEqual(r_cr.status_code, 200)
            hdata = r_cr.get_json()
            hook_id = hdata['id']
            secret_k = hdata['secret_key']

            r_test = self.client.post(f'/api/host/webhooks/{hook_id}/test')
            self.assertEqual(r_test.status_code, 200)
            tdata = r_test.get_json()
            self.assertTrue(tdata['ok'])
            self.assertEqual(tdata['status_code'], 200)
            self.assertTrue(tdata['signature'].startswith('sha256='))

            conn = sqlite3.connect(DB_PATH, timeout=15)
            payload_json = conn.cursor().execute("SELECT payload_json FROM webhook_deliveries WHERE webhook_id = ? ORDER BY id DESC LIMIT 1", (hook_id,)).fetchone()[0]
            conn.close()
            self.assertEqual(sign_webhook_payload(secret_k, payload_json.encode('utf-8')), tdata['signature'])

            # FastAPI /api/v1/events returns 200 cleanly without ValidationError + realtime broadcast works
            from fastapi.testclient import TestClient
            from fastapi_app import fastapi_app
            fclient = TestClient(fastapi_app)
            ev_resp = fclient.get('/api/v1/events')
            self.assertEqual(ev_resp.status_code, 200)
            self.assertIn('events', ev_resp.json())

            rt_resp = fclient.post('/api/v1/realtime/broadcast-live', json={
                'event_id': 1, 'type': 'poll_updated', 'payload': {'total_votes': 42}
            })
            self.assertEqual(rt_resp.status_code, 200)
            self.assertTrue(rt_resp.json()['success'])
        finally:
            if hook_id:
                conn = sqlite3.connect(DB_PATH, timeout=15)
                c = conn.cursor()
                c.execute("DELETE FROM webhook_deliveries WHERE webhook_id = ?", (hook_id,))
                c.execute("DELETE FROM host_webhooks WHERE id = ?", (hook_id,))
                conn.commit()
                conn.close()

    def test_09_unique_event_images_and_local_assets_exist(self):
        conn = sqlite3.connect(DB_PATH, timeout=15)
        c = conn.cursor()
        c.execute("SELECT image, COUNT(*) FROM events GROUP BY image HAVING COUNT(*) > 1")
        dups = c.fetchall()
        self.assertEqual(dups, [], f"Duplicate event image URLs found: {dups}")

        c.execute("SELECT id, image FROM events WHERE id IN (1, 19, 20, 49, 97, 98, 110, 165, 10000, 10001, 10031)")
        rows = dict(c.fetchall())
        conn.close()

        expected_local = {
            19: '/static/event_images/cricket_league_2026.jpg',
            20: '/static/event_images/football_cup_2026.jpg',
            49: '/static/event_images/candlelight_concert.jpg',
            97: '/static/event_images/solar_agri_expo.jpg',
            98: '/static/event_images/dairy_farming_expo.jpg',
            110: '/static/event_images/smart_city_townhall.jpg',
            165: '/static/event_images/contemporary_art_biennial.jpg',
        }
        repo_root = os.path.dirname(_backend_dir)
        for ev_id, expected_path in expected_local.items():
            self.assertEqual(rows.get(ev_id), expected_path)
            disk_path = os.path.join(repo_root, 'frontend', expected_path.lstrip('/').replace('/', os.sep))
            self.assertTrue(os.path.isfile(disk_path), f"Missing generated asset on disk: {disk_path}")
            static_resp = self.client.get(expected_path)
            self.assertEqual(static_resp.status_code, 200)
            static_resp.close()

        genai_imgs = {rows.get(eid) for eid in (10000, 10001, 10031) if eid in rows}
        self.assertEqual(len(genai_imgs), len([eid for eid in (10000, 10001, 10031) if eid in rows]))

    def test_10_public_event_share_copy_title_and_mandatory_login_before_register(self):
        # 1. Public event link loads cleanly without login, shows Share + Login-to-Register CTAs
        pub_resp = self.client.get('/event/19')
        self.assertEqual(pub_resp.status_code, 200)
        pub_html = pub_resp.get_data(as_text=True)
        self.assertIn('Inter-College Premier Cricket League 2026', pub_html)
        self.assertIn('property="og:url"', pub_html)
        self.assertIn('Share Public Link', pub_html)
        self.assertIn('Copy Event Name', pub_html)
        self.assertIn('Login to Register', pub_html)
        self.assertNotIn('⏻ Logout', pub_html)

        # 2. Attempting to register or group-book while logged out redirects to login with ?next=
        reg_gate = self.client.get('/register/19?type=in_person', follow_redirects=False)
        self.assertIn(reg_gate.status_code, (301, 302, 303))
        self.assertIn('next=', reg_gate.headers.get('Location', ''))
        self.assertIn('register', reg_gate.headers.get('Location', ''))

        grp_gate = self.client.get('/event/19/group-booking', follow_redirects=False)
        self.assertIn(grp_gate.status_code, (301, 302, 303))
        self.assertIn('next=', grp_gate.headers.get('Location', ''))

        # 3. Logging in with ?next=/register/19 redirects back to registration; external URLs are blocked
        self.client.get('/?next=/register/19')
        with self.client.session_transaction() as sess:
            ans = sess['captcha_answer']
        login_res = self.client.post('/', data={
            'action': 'login',
            'username': 'admin@example.com',
            'password': 'password123',
            'captcha': ans,
            'next': '/register/19',
        }, follow_redirects=False)
        self.assertEqual(login_res.status_code, 303)
        self.assertEqual(login_res.headers.get('Location'), '/register/19')

        # Open redirect protection rejects external URLs
        self.client.get('/logout')
        self.client.get('/')
        with self.client.session_transaction() as sess:
            ans2 = sess['captcha_answer']
        ext_res = self.client.post('/', data={
            'action': 'login',
            'username': 'admin@example.com',
            'password': 'password123',
            'captcha': ans2,
            'next': 'https://evil.example/phish',
        }, follow_redirects=False)
        self.assertEqual(ext_res.status_code, 303)
        self.assertEqual(ext_res.headers.get('Location'), '/dashboard')

        # 4. Dashboard & Category cards do not wrap titles in <a> tags and render Share buttons
        dash_html = self.client.get('/dashboard').get_data(as_text=True)
        self.assertIn('class="highlight-card-title event-copy-title"', dash_html)
        self.assertNotIn('<h3 class="highlight-card-title">\n                            <a ', dash_html)
        self.assertIn('shareEventFromBtn(this, event)', dash_html)

        cat_html = self.client.get('/category/Sports').get_data(as_text=True)
        self.assertIn('class="event-title event-copy-title"', cat_html)
        self.assertIn('class="grid-event-card-title event-copy-title"', cat_html)
        self.assertIn('shareEventFromBtn(this, event)', cat_html)


if __name__ == '__main__':
    unittest.main(verbosity=2)
