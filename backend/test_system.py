"""
test_system.py - Automated verification test suite for Events Booking.
Tests authentication, registration, seats tracking, notifications, audit logs,
admin controls, AI assistant responses, and PDF ticket generation.
"""
import os
os.environ['TESTING'] = '1'
import unittest
import json
import sqlite3
from datetime import datetime
import sys
_backend_dir = os.path.dirname(os.path.abspath(__file__))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)
from app import app, init_db, get_events, generate_certificate_pdf_bytes

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'users.db')

class EventManagementSystemTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def _get_upcoming_event(self):
        events = get_events()
        now = datetime.now()
        for e in events:
            date_str = e.get('date', '')
            for fmt in ("%b %d, %Y", "%Y-%m-%d", "%d %b %Y", "%B %d, %Y"):
                try:
                    ev_date = datetime.strptime(date_str, fmt)
                    if ev_date >= now:
                        return e
                except Exception:
                    pass
        return events[0] if events else None
        return events[-1] if events else None

    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_01_database_tables_and_columns(self):
        """Verify all tables and critical columns exist in the database."""
        conn = sqlite3.connect(DB_PATH, timeout=15)
        c = conn.cursor()
        
        # Check tables
        tables = ['users', 'events', 'registrations', 'notifications', 'reviews', 'audit_log', 'razorpay_orders']
        for tbl in tables:
            c.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{tbl}'")
            self.assertIsNotNone(c.fetchone(), f"Table '{tbl}' should exist in database.")

        # Check events columns
        c.execute("PRAGMA table_info(events)")
        event_cols = [row[1] for row in c.fetchall()]
        for col in ['seats_total', 'seats_filled', 'featured', 'venue']:
            self.assertIn(col, event_cols, f"Column '{col}' should exist in events table.")

        # Check users columns
        c.execute("PRAGMA table_info(users)")
        user_cols = [row[1] for row in c.fetchall()]
        self.assertIn('is_admin', user_cols, "Column 'is_admin' should exist in users table.")
        conn.close()

    def test_02_admin_login_and_dashboard_access(self):
        """Test admin login and access to admin panel dashboard."""
        with self.client.session_transaction() as sess:
            sess['loggedin'] = True
            sess['username'] = 'admin'
        
        # Admin dashboard
        resp = self.client.get('/admin')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Overview', resp.data)
        self.assertIn(b'Total Users', resp.data)

        # Admin users page
        resp_users = self.client.get('/admin/users')
        self.assertEqual(resp_users.status_code, 200)
        self.assertIn(b'Users', resp_users.data)

        # Admin events page
        resp_events = self.client.get('/admin/events')
        self.assertEqual(resp_events.status_code, 200)
        self.assertIn(b'Events', resp_events.data)

        # Admin audit log
        resp_audit = self.client.get('/admin/audit')
        self.assertEqual(resp_audit.status_code, 200)
        self.assertIn(b'Audit', resp_audit.data)

    def test_03_registration_flow_and_audit(self):
        """Test event registration, seat increment, notification, and audit log."""
        ev = self._get_upcoming_event()
        self.assertIsNotNone(ev, "There should be at least one upcoming event in database.")
        ev_id = ev['id']

        test_user = 'test_student_user'
        with self.client.session_transaction() as sess:
            sess['loggedin'] = True
            sess['username'] = test_user

        # Register for event
        resp = self.client.post(f'/register/{ev_id}', data={
            'full_name': 'Test Student',
            'email': 'student@test.com',
            'phone': '9876543210',
            'college_id': 'COL-2026-001',
            'payment_method': 'UPI',
            'upi_id': 'test@upi'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Registration Successful', resp.data)

        # Verify registration in DB
        conn = sqlite3.connect(DB_PATH, timeout=15)
        c = conn.cursor()
        c.execute("SELECT * FROM registrations WHERE username=? AND event_id=?", (test_user, ev_id))
        reg = c.fetchone()
        self.assertIsNotNone(reg, "Registration row should exist.")

        # Verify notification created
        c.execute("SELECT * FROM notifications WHERE username=?", (test_user,))
        notif = c.fetchone()
        self.assertIsNotNone(notif, "Notification should be generated for the user.")

        # Verify audit log entry
        c.execute("SELECT * FROM audit_log WHERE username=? AND action='register_event'", (test_user,))
        audit = c.fetchone()
        self.assertIsNotNone(audit, "Audit log should record the registration.")
        conn.close()

        # Verify PDF ticket download
        resp_ticket = self.client.get(f'/download_ticket/{ev_id}')
        self.assertEqual(resp_ticket.status_code, 200)
        self.assertEqual(resp_ticket.headers.get('Content-Type'), 'application/pdf')

        # Clean up registration
        self.client.post(f'/unregister/{ev_id}')

    def test_04_ai_assistant_endpoint(self):
        """Test AI assistant endpoint (/api/chat) with contextual queries."""
        with self.client.session_transaction() as sess:
            sess['loggedin'] = True
            sess['username'] = 'test_student_user'

        # Test query for free events
        resp_free = self.client.post('/api/chat', 
                                     data=json.dumps({'message': 'Are there any free events?'}),
                                     content_type='application/json')
        self.assertEqual(resp_free.status_code, 200)
        data_free = resp_free.get_json()
        self.assertIn('reply', data_free)
        self.assertTrue(len(data_free['reply']) > 10)

        # Test query for how to register
        resp_reg = self.client.post('/api/chat', 
                                    data=json.dumps({'message': 'How do I register for hackathons?'}),
                                    content_type='application/json')
        self.assertEqual(resp_reg.status_code, 200)
        data_reg = resp_reg.get_json()
        self.assertIn('reply', data_reg)
        self.assertIn('register', data_reg['reply'].lower())

        # Test query for ticket download
        resp_ticket = self.client.post('/api/chat', 
                                       data=json.dumps({'message': 'Where can I download my ticket?'}),
                                       content_type='application/json')
        self.assertEqual(resp_ticket.status_code, 200)
        data_ticket = resp_ticket.get_json()
        self.assertIn('reply', data_ticket)
        self.assertIn('ticket', data_ticket['reply'].lower())

    def test_05_admin_user_role_management(self):
        """Test promoting, demoting and exporting users via admin panel."""
        conn = sqlite3.connect(DB_PATH, timeout=15)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES ('demouser', 'dummyhash', 'user')")
        c.execute("SELECT id FROM users WHERE username='demouser'")
        user_id = c.fetchone()[0]
        conn.commit()
        conn.close()

        with self.client.session_transaction() as sess:
            sess['loggedin'] = True
            sess['username'] = 'admin'

        # Promote to host
        resp_promote = self.client.post(f'/admin/users/{user_id}/promote', follow_redirects=True)
        self.assertEqual(resp_promote.status_code, 200)

        conn = sqlite3.connect(DB_PATH, timeout=15)
        c = conn.cursor()
        c.execute("SELECT role FROM users WHERE id=?", (user_id,))
        self.assertEqual(c.fetchone()[0], 'host')
        conn.close()

        # Demote to user
        resp_demote = self.client.post(f'/admin/users/{user_id}/demote', follow_redirects=True)
        self.assertEqual(resp_demote.status_code, 200)
        
        conn = sqlite3.connect(DB_PATH, timeout=15)
        c = conn.cursor()
        c.execute("SELECT role FROM users WHERE id=?", (user_id,))
        self.assertEqual(c.fetchone()[0], 'user')

        # Export users CSV
        resp_export = self.client.get('/admin/export/users')
        self.assertEqual(resp_export.status_code, 200)
        self.assertIn('text/csv', resp_export.headers.get('Content-Type'))
        self.assertIn(b'Username', resp_export.data)

        # Clean up test user
        conn = sqlite3.connect(DB_PATH, timeout=15)
        c = conn.cursor()
        c.execute("DELETE FROM users WHERE id=?", (user_id,))
        conn.commit()
        conn.close()

    def test_06_team_registration_and_ticket(self):
        """Test Team Registration with teammates and team PDF ticket generation."""
        ev = self._get_upcoming_event()
        self.assertIsNotNone(ev, "There should be at least one upcoming event in database.")
        ev_id = ev['id']

        team_leader = 'test_team_lead'
        with self.client.session_transaction() as sess:
            sess['loggedin'] = True
            sess['username'] = team_leader

        # Register Team of 3
        resp = self.client.post(f'/register/{ev_id}', data={
            'reg_type': 'team',
            'team_name': 'Code Warriors',
            'member_count': '3',
            'full_name': 'Lead Dev',
            'email': 'lead@test.com',
            'phone': '9876543211',
            'college_id': 'COL-2026-T01',
            'member_2_name': 'Alice Smith',
            'member_2_email': 'alice@test.com',
            'member_2_phone': '9876543212',
            'member_2_college': 'COL-2026-T02',
            'member_3_name': 'Bob Jones',
            'member_3_email': 'bob@test.com',
            'member_3_phone': '9876543213',
            'member_3_college': 'COL-2026-T03',
            'payment_method': 'UPI',
            'upi_id': 'team@upi'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Code Warriors', resp.data)

        # Verify DB entry with team details
        conn = sqlite3.connect(DB_PATH, timeout=15)
        c = conn.cursor()
        c.execute("SELECT team_name, team_members FROM registrations WHERE username=? AND event_id=?", (team_leader, ev_id))
        row = c.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], 'Code Warriors')
        members = json.loads(row[1])
        self.assertEqual(len(members), 2)
        conn.close()

        # Verify PDF Ticket contains team info
        resp_ticket = self.client.get(f'/download_ticket/{ev_id}')
        self.assertEqual(resp_ticket.status_code, 200)
        self.assertEqual(resp_ticket.headers.get('Content-Type'), 'application/pdf')

        # Clean up
        self.client.post(f'/unregister/{ev_id}')

        # Test 5-member team registration
        resp5 = self.client.post(f'/register/{ev_id}', data={
            'reg_type': 'team',
            'team_name': 'Quantum Five',
            'member_count': '5',
            'full_name': 'Lead Dev',
            'email': 'lead@test.com',
            'phone': '9876543211',
            'college_id': 'COL-2026-T01',
            'member_2_name': 'Alice',
            'member_2_email': 'alice@test.com',
            'member_2_phone': '9876543212',
            'member_2_college': 'COL-2026-T02',
            'member_3_name': 'Bob',
            'member_3_email': 'bob@test.com',
            'member_3_phone': '9876543213',
            'member_3_college': 'COL-2026-T03',
            'member_4_name': 'Charlie',
            'member_4_email': 'charlie@test.com',
            'member_4_phone': '9876543214',
            'member_4_college': 'COL-2026-T04',
            'member_5_name': 'Diana',
            'member_5_email': 'diana@test.com',
            'member_5_phone': '9876543215',
            'member_5_college': 'COL-2026-T05',
            'payment_method': 'UPI',
            'upi_id': 'team5@upi'
        }, follow_redirects=True)
        self.assertEqual(resp5.status_code, 200)
        self.assertIn(b'Quantum Five', resp5.data)

        # Verify DB has 4 teammates
        conn = sqlite3.connect(DB_PATH, timeout=15)
        c = conn.cursor()
        c.execute("SELECT team_name, team_members FROM registrations WHERE username=? AND event_id=?", (team_leader, ev_id))
        row = c.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], 'Quantum Five')
        members = json.loads(row[1])
        self.assertEqual(len(members), 4)
        conn.close()

        # Clean up
        self.client.post(f'/unregister/{ev_id}')

    def test_07_live_ticket_scanner_checkin(self):
        """Test Live Ticket QR Scanner verification API and check-in status."""
        ev = self._get_upcoming_event()
        self.assertIsNotNone(ev, "There should be at least one upcoming event in database.")
        ev_id = ev['id']

        attendee_user = 'scanner_test_attendee'
        with self.client.session_transaction() as sess:
            sess['loggedin'] = True
            sess['username'] = attendee_user

        # Register attendee
        self.client.post(f'/register/{ev_id}', data={
            'full_name': 'Scanner Test Attendee',
            'email': 'scan@test.com',
            'phone': '9876543299',
            'college_id': 'COL-2026-SCAN',
            'payment_method': 'UPI',
            'upi_id': 'scan@upi'
        })

        # Switch to Admin/Host session for scanning
        # Verify ticket view page renders without error
        with self.client.session_transaction() as sess:
            sess['loggedin'] = True
            sess['username'] = attendee_user
        resp_ticket_view = self.client.get(f'/ticket/view/{ev_id}')
        self.assertEqual(resp_ticket_view.status_code, 200)
        self.assertIn(b'Tamper-Evident Holographic Pass', resp_ticket_view.data)

        # Admin login for scanner
        with self.client.session_transaction() as sess:
            sess['loggedin'] = True
            sess['username'] = 'admin'

        # Scanner page access
        resp_scan_page = self.client.get('/scan_ticket')
        self.assertEqual(resp_scan_page.status_code, 200)

        # 1. Verify valid ticket by attendee username
        resp_verify = self.client.post('/api/verify_ticket', 
                                       data=json.dumps({'code': attendee_user}),
                                       content_type='application/json')
        self.assertEqual(resp_verify.status_code, 200)
        data = resp_verify.get_json()
        self.assertTrue(data['ok'])
        self.assertFalse(data['already_checked_in'])
        self.assertEqual(data['username'], attendee_user)

        # 2. Verify duplicate check-in warning
        resp_dup = self.client.post('/api/verify_ticket', 
                                    data=json.dumps({'code': attendee_user}),
                                    content_type='application/json')
        self.assertEqual(resp_dup.status_code, 200)
        data_dup = resp_dup.get_json()
        self.assertTrue(data_dup['ok'])
        self.assertTrue(data_dup['already_checked_in'])

        # 3. Check public verification page /verify/<ticket_code>
        tkt_code = f"TKT-{ev_id:03d}-{data['reg_id']:05d}"
        resp_verify_page = self.client.get(f'/verify/{tkt_code}')
        self.assertEqual(resp_verify_page.status_code, 200)
        self.assertIn(b'ALREADY CHECKED IN', resp_verify_page.data)

        # 4. Check recent checkins API
        resp_recent = self.client.get('/api/recent_checkins')
        self.assertEqual(resp_recent.status_code, 200)
        recent_data = resp_recent.get_json()
        self.assertTrue(len(recent_data['checkins']) > 0)

        # 5. Attendee who is scanned/checked in attempts to unregister -> Must be BLOCKED
        with self.client.session_transaction() as sess:
            sess['loggedin'] = True
            sess['username'] = attendee_user
        resp_unreg_blocked = self.client.post(f'/unregister/{ev_id}', data={
            'reason': 'Schedule conflict / Personal emergency',
            'feedback': 'Cannot attend due to sudden emergency.'
        }, headers={'X-Requested-With': 'XMLHttpRequest'})
        self.assertEqual(resp_unreg_blocked.status_code, 400)
        self.assertIn('scanned', resp_unreg_blocked.get_json().get('error', '').lower())

        # 6. Create another un-scanned attendee to test cancellation and revoked pass detection
        revoked_user = 'test_scanner_revoked_user'
        with self.client.session_transaction() as sess:
            sess['loggedin'] = True
            sess['username'] = revoked_user
        resp_reg2 = self.client.post(f'/register/{ev_id}', data={
            'full_name': 'Revoked Attendee',
            'email': 'revoked@test.com',
            'phone': '9876543210',
            'college_id': 'USN-REV-01',
            'payment_method': 'Free Pass',
            'upi_id': ''
        })
        self.assertEqual(resp_reg2.status_code, 200)

        conn = sqlite3.connect(DB_PATH, timeout=15)
        c = conn.cursor()
        c.execute("SELECT id FROM registrations WHERE username = ? AND event_id = ?", (revoked_user, ev_id))
        row2 = c.fetchone()
        conn.close()
        reg2_id = row2[0]
        tkt_code2 = f"TKT-{ev_id:03d}-{reg2_id:05d}"

        # Revoked attendee unregisters from event
        with self.client.session_transaction() as sess:
            sess['loggedin'] = True
            sess['username'] = revoked_user
        resp_unreg2 = self.client.post(f'/unregister/{ev_id}', data={
            'reason': 'Schedule conflict / Personal emergency',
            'feedback': 'Cannot attend due to sudden emergency.'
        })
        self.assertIn(resp_unreg2.status_code, [200, 302])

        # 7. Scanner attempts to scan the revoked ticket -> Must be DENIED with HTTP 400
        with self.client.session_transaction() as sess:
            sess['loggedin'] = True
            sess['username'] = 'admin'
        resp_revoked_scan = self.client.post('/api/verify_ticket',
                                            data=json.dumps({'code': tkt_code2}),
                                            content_type='application/json')
        self.assertEqual(resp_revoked_scan.status_code, 400)
        revoked_data = resp_revoked_scan.get_json()
        self.assertFalse(revoked_data['ok'])
        self.assertTrue(revoked_data.get('is_cancelled'))
        self.assertIn('REVOKED', revoked_data.get('error', '').upper())

        # 8. Public verification page now shows REVOKED status
        resp_verify_revoked = self.client.get(f'/verify/{tkt_code2}')
        self.assertEqual(resp_verify_revoked.status_code, 200)
        self.assertIn(b'TICKET REVOKED', resp_verify_revoked.data)

    def test_08_profile_edit_and_save(self):
        """Test saving profile changes directly with email and phone updates."""
        test_user = 'test_profile_user'
        conn = sqlite3.connect(DB_PATH, timeout=15)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO users (username, password, full_name, email, phone, is_admin) VALUES (?, ?, ?, ?, ?, ?)",
                  (test_user, 'pass_hash', 'Profile Tester', 'initial@test.com', '9876543210', 0))
        conn.commit()
        conn.close()

        with self.client.session_transaction() as sess:
            sess['loggedin'] = True
            sess['username'] = test_user

        # 1. Access profile page
        resp_profile = self.client.get('/profile')
        self.assertEqual(resp_profile.status_code, 200)

        # 2. Save Profile with updated email and mobile phone directly
        new_email = 'newupdated@gmail.com'
        new_phone = '9123456789'
        resp_save = self.client.post('/profile', data={
            'first_name': 'Updated',
            'last_name': 'User',
            'email': new_email,
            'phone': new_phone,
            'college_id': 'COL-PRO-123',
            'country': 'India',
            'state': 'Karnataka',
            'city': 'Bangalore',
            'pincode': '560001'
        }, follow_redirects=True)
        self.assertEqual(resp_save.status_code, 200)

        # 7. Confirm database update
        conn = sqlite3.connect(DB_PATH, timeout=15)
        c = conn.cursor()
        c.execute("SELECT email, phone, city, college_id FROM users WHERE username=?", (test_user,))
        user_row = c.fetchone()
        self.assertIsNotNone(user_row)
        self.assertEqual(user_row[0], new_email)
        self.assertEqual(user_row[1], new_phone)
        self.assertEqual(user_row[2], 'Bangalore')
        self.assertEqual(user_row[3], 'COL-PRO-123')
        # Clean up
        c.execute("DELETE FROM users WHERE username=?", (test_user,))
        conn.commit()
        conn.close()

    def test_09_user_id_and_email_authentication(self):
        """Test authentication strictly via 4-digit User ID and Email, blocking login by name."""
        from flask_bcrypt import Bcrypt
        bcrypt = Bcrypt()
        pwd_hash = bcrypt.generate_password_hash('SecretPass123!').decode('utf-8')
        
        conn = sqlite3.connect(DB_PATH, timeout=15)
        c = conn.cursor()
        c.execute("DELETE FROM users WHERE username='uid_auth_test_user'")
        c.execute("""INSERT INTO users (username, password, full_name, email, phone, college_id, user_id, is_active)
                     VALUES ('uid_auth_test_user', ?, 'Test Auth User', 'uid_auth@example.com', '9876543210', 'COL-UID-999', 'UID-0042', 1)""",
                  (pwd_hash,))
        conn.commit()
        conn.close()

        # 1. Login with registered Email -> SUCCESS
        resp_email = self.client.post('/', data={
            'action': 'login',
            'username': 'uid_auth@example.com',
            'password': 'SecretPass123!'
        }, follow_redirects=False)
        self.assertEqual(resp_email.status_code, 303)
        self.assertIn('/dashboard', resp_email.headers.get('Location', ''))

        # 2. Login with 4-digit User ID '0042' -> SUCCESS
        resp_4digits = self.client.post('/', data={
            'action': 'login',
            'username': '0042',
            'password': 'SecretPass123!'
        }, follow_redirects=False)
        self.assertEqual(resp_4digits.status_code, 303)
        self.assertIn('/dashboard', resp_4digits.headers.get('Location', ''))

        # 3. Login with full UID 'UID-0042' -> SUCCESS
        resp_uid = self.client.post('/', data={
            'action': 'login',
            'username': 'UID-0042',
            'password': 'SecretPass123!'
        }, follow_redirects=False)
        self.assertEqual(resp_uid.status_code, 303)
        self.assertIn('/dashboard', resp_uid.headers.get('Location', ''))

        # 4. Attempt to login with plain username 'uid_auth_test_user' -> BLOCKED with explicit error message
        resp_name = self.client.post('/', data={
            'action': 'login',
            'username': 'uid_auth_test_user',
            'password': 'SecretPass123!'
        }, follow_redirects=True)
        self.assertEqual(resp_name.status_code, 200)
        self.assertIn(b'Invalid credentials. Please enter your User ID or registered Email address.', resp_name.data)

        # 5. Attempt to login with full name 'Test Auth User' -> BLOCKED with explicit error message
        resp_fullname = self.client.post('/', data={
            'action': 'login',
            'username': 'Test Auth User',
            'password': 'SecretPass123!'
        }, follow_redirects=True)
        self.assertEqual(resp_fullname.status_code, 200)
        self.assertIn(b'Invalid credentials. Please enter your User ID or registered Email address.', resp_fullname.data)

        # 6. Forgot Password reset using 4-digit User ID '0042' -> SUCCESS
        resp_forgot_uid = self.client.post('/forgot_password', data={
            'username': '0042',
            'college_id': 'COL-UID-999',
            'phone': '9876543210',
            'new_password': 'BrandNewPass456!',
            'confirm_password': 'BrandNewPass456!'
        }, follow_redirects=True)
        self.assertEqual(resp_forgot_uid.status_code, 200)
        self.assertIn(b'Password reset successful', resp_forgot_uid.data)

        # 7. Login with newly updated password via Email -> SUCCESS
        resp_login_new = self.client.post('/', data={
            'action': 'login',
            'username': 'uid_auth@example.com',
            'password': 'BrandNewPass456!'
        }, follow_redirects=False)
        self.assertEqual(resp_login_new.status_code, 303)

        # Clean up
        conn = sqlite3.connect(DB_PATH, timeout=15)
        c = conn.cursor()
        c.execute("DELETE FROM users WHERE username='uid_auth_test_user'")
        conn.commit()
        conn.close()

    def test_10_checkin_history_page_and_export(self):
        """Test accessing /checkin_history and CSV export as host/admin."""
        with self.client.session_transaction() as sess:
            sess['loggedin'] = True
            sess['username'] = 'admin'

        # Test GET /checkin_history renders with HTTP 200 and required components
        resp = self.client.get('/checkin_history')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Check-in History', resp.data)
        self.assertIn(b'Export Check-ins CSV', resp.data)

        # Test GET /host/export_checkins_csv downloads CSV file
        resp_csv = self.client.get('/host/export_checkins_csv')
        self.assertEqual(resp_csv.status_code, 200)
        self.assertIn('text/csv', resp_csv.headers.get('Content-Type', ''))
        self.assertIn(b'Attendee Name', resp_csv.data)

    def test_11_event_timings_and_today_2hr_cutoff_rule(self):
        """Test 2-hour registration cutoff rule for events held today, timing status calculation, and dashboard calendar data."""
        from app import get_event_status_info, parse_time_string
        from datetime import datetime, timedelta, time as dtime

        today_str = datetime.now().strftime("%b %d, %Y")
        today_date = datetime.now().date()

        # 1. Test helper status calculations for an event at 10:00 AM
        event_sample = {
            'id': 9999,
            'title': 'Cutoff Unit Test Event',
            'date': today_str,
            'time': '10:00 AM',
            'end_time': '05:00 PM',
            'seats_total': 100,
            'seats_filled': 10
        }

        # Case A: Simulated time at 07:30 AM (before 08:00 AM cutoff) -> OPEN
        bh, bm = parse_time_string('07:30 AM')
        t_before = datetime.combine(today_date, dtime(bh, bm))
        status_before = get_event_status_info(event_sample, ref_now=t_before)
        self.assertTrue(status_before['is_today'])
        self.assertTrue(status_before['is_open'])
        self.assertFalse(status_before['is_cutoff_reached'])
        self.assertEqual(status_before['status_badge'], 'today_open')
        self.assertEqual(status_before['cutoff_time_str'], '08:00 AM')

        # Case B: Simulated time at 08:00 AM (exactly 2h cutoff) -> CLOSED
        ch, cm = parse_time_string('08:00 AM')
        t_cutoff = datetime.combine(today_date, dtime(ch, cm))
        status_cutoff = get_event_status_info(event_sample, ref_now=t_cutoff)
        self.assertTrue(status_cutoff['is_today'])
        self.assertFalse(status_cutoff['is_open'])
        self.assertTrue(status_cutoff['is_cutoff_reached'])
        self.assertEqual(status_cutoff['status_badge'], 'today_cutoff')

        # Case C: Simulated time at 09:30 AM (past cutoff, before start) -> CLOSED
        ah, am = parse_time_string('09:30 AM')
        t_after = datetime.combine(today_date, dtime(ah, am))
        status_after = get_event_status_info(event_sample, ref_now=t_after)
        self.assertTrue(status_after['is_today'])
        self.assertFalse(status_after['is_open'])
        self.assertTrue(status_after['is_cutoff_reached'])

        # 2. Test registration route enforcement for a today cutoff event
        conn = sqlite3.connect(DB_PATH, timeout=15)
        c = conn.cursor()
        c.execute("""
            INSERT OR REPLACE INTO events 
            (id, title, date, time, end_time, price, desc, purpose, full_details, outcome, color, image, venue, venue_address, seats_total, seats_filled)
            VALUES (9999, 'Cutoff Test Event Today', ?, '10:00 AM', '05:00 PM', 'Free', 'Test Desc', 'Test Purpose', 'Test Breakdown', 'Test Outcome', '#ff0000', 'https://example.com/img.jpg', 'Auditorium', 'Bangalore', 100, 0)
        """, (today_str,))
        conn.commit()
        conn.close()

        with self.client.session_transaction() as sess:
            sess['loggedin'] = True
            sess['username'] = 'test_student_user'

        # If current time is past 08:00 AM today, POST /register/9999 should be rejected
        now_dt = datetime.now()
        sh, sm = parse_time_string('10:00 AM')
        cutoff_dt = datetime.combine(today_date, dtime(sh, sm)) - timedelta(hours=2)
        if now_dt >= cutoff_dt:
            resp_reg = self.client.post('/register/9999', data={
                'full_name': 'Test Student',
                'email': 'student@test.com',
                'phone': '9876543210',
                'college_id': 'COL-2026-001'
            }, follow_redirects=True)
            self.assertIn(b'Registration is closed', resp_reg.data)

        # 3. Test Dashboard renders calendar legend with 3 status dots and event time info
        resp_dash = self.client.get('/dashboard')
        self.assertEqual(resp_dash.status_code, 200)
        self.assertIn(b'dot-open', resp_dash.data)
        self.assertIn(b'dot-today', resp_dash.data)
        self.assertIn(b'dot-closed', resp_dash.data)
        self.assertIn(b'data-cutoff-time', resp_dash.data)
        self.assertIn(b'data-is-today', resp_dash.data)

        # 4. Test Live Auto-Update API endpoint (/api/events)
        resp_api = self.client.get('/api/events')
        self.assertEqual(resp_api.status_code, 200)
        api_data = json.loads(resp_api.data.decode('utf-8'))
        self.assertEqual(api_data.get('status'), 'success')
        self.assertIsInstance(api_data.get('events'), list)
        self.assertTrue(len(api_data.get('events')) > 0)
        first_ev = api_data['events'][0]
        self.assertIn('cutoff_time', first_ev)
        self.assertIn('time', first_ev)
        self.assertIn('end_time', first_ev)

        # Clean up test event
        conn = sqlite3.connect(DB_PATH, timeout=15)
        c = conn.cursor()
        c.execute("DELETE FROM events WHERE id=9999")
        conn.commit()
        conn.close()

    def test_12_real_time_locations_and_google_maps(self):
        """Test real-time event locations, physical addresses, and Google Maps integration."""
        with self.client.session_transaction() as sess:
            sess['loggedin'] = True
            sess['username'] = 'test_student_user'

        # 1. Test /api/events exposes venue, venue_address, maps_url, and maps_directions_url
        resp_api = self.client.get('/api/events')
        self.assertEqual(resp_api.status_code, 200)
        api_data = json.loads(resp_api.data.decode('utf-8'))
        events = api_data.get('events', [])
        self.assertTrue(len(events) > 0)
        
        sample_ev = events[0]
        self.assertTrue(bool(sample_ev.get('venue')), "Event must have an authentic venue name")
        self.assertTrue(bool(sample_ev.get('venue_address')), "Event must have a physical street address")
        self.assertIn('google.com/maps/search', sample_ev.get('maps_url', ''))
        self.assertIn('google.com/maps/dir', sample_ev.get('maps_directions_url', ''))

        # 2. Test Dashboard renders Google Maps link on event cards
        resp_dash = self.client.get('/dashboard')
        self.assertEqual(resp_dash.status_code, 200)
        self.assertIn(b'event-venue-link', resp_dash.data)
        self.assertIn(b'google.com/maps', resp_dash.data)

        # 3. Test Event Detail page renders Venue section, Maps Search, Directions, and Copy button
        ev_id = sample_ev.get('id', 1)
        resp_detail = self.client.get(f'/event/{ev_id}')
        self.assertEqual(resp_detail.status_code, 200)
        self.assertIn(b'event-venue-section', resp_detail.data)
        self.assertIn(b'Open in Google Maps', resp_detail.data)
        self.assertIn(b'Get Directions', resp_detail.data)
        self.assertIn(b'Copy Address', resp_detail.data)
        self.assertIn(sample_ev['venue'].encode('utf-8'), resp_detail.data)

        # 4. Test PDF Ticket incorporates venue name and address
        from app import generate_ticket_pdf_bytes
        reg_mock = {
            'id': 101,
            'full_name': 'Map Test Attendee',
            'email': 'attendee@test.com',
            'phone': '9876543210',
            'college_id': 'COL-MAP-01',
            'username': 'test_student_user',
            'status': 'active'
        }
        pdf_bytes = generate_ticket_pdf_bytes(sample_ev, reg_mock)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertTrue(len(pdf_bytes) > 1000)
        self.assertTrue(pdf_bytes.startswith(b'%PDF-'))

    def test_13_registration_and_unregistration_emails(self):
        """
        Test email dispatching functions:
        1. send_registration_confirmation_email
        2. send_unregistration_confirmation_email
        3. send_account_welcome_email
        Ensuring formatting, variables, and parameters are fully resolved without NameError or syntax exceptions.
        """
        from app import (
            send_registration_confirmation_email,
            send_unregistration_confirmation_email,
            send_account_welcome_email,
            get_event,
            generate_ticket_pdf_bytes
        )

        sample_event = get_event(1) or {
            'id': 1,
            'title': 'Email Test Hackathon',
            'date': 'Oct 15, 2026',
            'time': '10:00 AM',
            'venue': 'Campus Tech Dome',
            'venue_address': 'Bangalore, India',
            'price': 'Free'
        }

        reg_data = {
            'id': 99,
            'full_name': 'Email Tester',
            'email': 'attendee@test.com',
            'phone': '9876543210',
            'team_name': 'Code Warriors',
            'ticket_code': 'TKT-001-00099'
        }

        pdf_bytes = generate_ticket_pdf_bytes(sample_event, reg_data)

        # 1. Test Registration Confirmation Email function execution
        try:
            send_registration_confirmation_email(
                recipient_email='attendee@test.com',
                recipient_name='Email Tester',
                event=sample_event,
                reg_info=reg_data,
                pdf_bytes=pdf_bytes
            )
            reg_email_success = True
        except Exception as e:
            reg_email_success = False
            self.fail(f"send_registration_confirmation_email raised an unexpected exception: {e}")
        self.assertTrue(reg_email_success)

        # 2. Test Unregistration Confirmation Email function execution
        try:
            send_unregistration_confirmation_email(
                recipient_email='attendee@test.com',
                recipient_name='Email Tester',
                event=sample_event,
                reg_info=reg_data,
                reason='Schedule conflict',
                feedback='Great event, but conflict on this date.'
            )
            unreg_email_success = True
        except Exception as e:
            unreg_email_success = False
            self.fail(f"send_unregistration_confirmation_email raised an unexpected exception: {e}")
        self.assertTrue(unreg_email_success)

        # 3. Test Account Welcome Email function execution
        try:
            send_account_welcome_email(
                recipient_email='newuser@test.com',
                recipient_name='New Test User',
                username='newtestuser',
                user_id='UID-0099'
            )
            welcome_email_success = True
        except Exception as e:
            welcome_email_success = False
            self.fail(f"send_account_welcome_email raised an unexpected exception: {e}")
        self.assertTrue(welcome_email_success)

    def test_14_certificate_export_and_pwa(self):
        """Test Feature 1 (Certificate PDF & Verification), Feature 2 (CSV Attendee Export), and Feature 4 (PWA)."""
        from app import generate_certificate_pdf_bytes, get_event

        sample_event = get_event(1) or {
            'id': 1,
            'title': 'AI & Web3 Hackathon 2026',
            'date': 'Oct 15, 2026',
            'venue': 'Main Campus Auditorium',
            'venue_address': 'Tech Park Campus, Bangalore',
            'price': 'Free'
        }

        reg_data = {
            'id': 101,
            'full_name': 'Venu R',
            'username': 'admin',
            'college_id': 'COL-2026-001',
            'checkin_time': '15 Oct 2026, 10:30 AM'
        }

        # 1. Test Feature 1: PDF Certificate Generation (A4 Landscape bytes, starts with %PDF)
        cert_pdf_bytes = generate_certificate_pdf_bytes(sample_event, reg_data)
        self.assertIsNotNone(cert_pdf_bytes)
        self.assertTrue(len(cert_pdf_bytes) > 500)
        self.assertTrue(cert_pdf_bytes.startswith(b'%PDF'))

        # 2. Test Feature 1: Public Certificate Verification Page
        resp_verify_cert = self.client.get('/verify_certificate/CERT-001-00101')
        self.assertEqual(resp_verify_cert.status_code, 200)

        # 3. Test Feature 2: CSV Export for Single Event
        with self.client.session_transaction() as sess:
            sess['loggedin'] = True
            sess['username'] = 'admin'
            sess['is_admin'] = 1

        resp_csv = self.client.get('/export_attendees/1')
        self.assertEqual(resp_csv.status_code, 200)
        self.assertEqual(resp_csv.mimetype, 'text/csv')
        self.assertIn('Registration ID', resp_csv.data.decode('utf-8'))

        # Test Feature 2: CSV Export for All Attendees across events
        resp_all_csv = self.client.get('/export_all_attendees')
        self.assertEqual(resp_all_csv.status_code, 200)
        self.assertEqual(resp_all_csv.mimetype, 'text/csv')

        # Test Feature 2: Check-in History CSV Export
        resp_checkin_csv = self.client.get('/host/export_checkins_csv')
        self.assertEqual(resp_checkin_csv.status_code, 200)

        # 4. Test Feature 4: PWA Manifest & Service Worker Routes
        resp_manifest = self.client.get('/manifest.json')
        self.assertEqual(resp_manifest.status_code, 200)
        self.assertIn('Events Booking', resp_manifest.data.decode('utf-8'))

        resp_sw = self.client.get('/sw.js')
        self.assertEqual(resp_sw.status_code, 200)
        self.assertIn('CACHE_NAME', resp_sw.data.decode('utf-8'))

        resp_sw_alias = self.client.get('/service-worker.js')
        self.assertEqual(resp_sw_alias.status_code, 200)

    def test_15_live_stream_access_ticket_unlock_and_paid_pass(self):
        """Test Live Stream Video Projection access, Ticket ID unlocking (Free for in-person attendees), and Virtual Pass Purchase (Paid)."""
        ev = self._get_upcoming_event()
        self.assertIsNotNone(ev)
        ev_id = ev['id']

        # 1. Setup a registered attendee and a non-registered attendee
        conn = sqlite3.connect(DB_PATH, timeout=15)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO users (username, password, full_name, email, is_admin) VALUES ('reg_stream_user', 'hash123', 'Registered Live User', 'reglive@test.com', 0)")
        c.execute("INSERT OR REPLACE INTO users (username, password, full_name, email, is_admin) VALUES ('nonreg_stream_user', 'hash123', 'Online Viewer', 'online@test.com', 0)")
        
        # Register reg_stream_user
        c.execute("DELETE FROM registrations WHERE username=? AND event_id=?", ('reg_stream_user', ev_id))
        c.execute("DELETE FROM live_stream_passes WHERE username=? AND event_id=?", ('nonreg_stream_user', ev_id))
        c.execute("""
            INSERT INTO registrations (event_id, username, full_name, email, phone, college_id, status)
            VALUES (?, 'reg_stream_user', 'Registered Live User', 'reglive@test.com', '9876543210', 'COL-LIVE-01', 'active')
        """, (ev_id,))
        reg_id = c.lastrowid
        ticket_code = f"TKT-{ev_id:03d}-{reg_id:05d}"
        conn.commit()
        conn.close()

        # 2. Test Non-registered user: Should have has_access=False initially
        with self.client.session_transaction() as sess:
            sess['loggedin'] = True
            sess['username'] = 'nonreg_stream_user'

        resp_live_page = self.client.get(f'/event/{ev_id}/live')
        self.assertEqual(resp_live_page.status_code, 200)
        self.assertIn(b'Live Video Projection', resp_live_page.data)

        resp_live_data = self.client.get(f'/api/event/{ev_id}/live/data')
        self.assertEqual(resp_live_data.status_code, 200)
        live_data = resp_live_data.get_json()
        self.assertFalse(live_data['access']['has_access'])

        # 3. Non-registered user tries to post Q&A question -> Forbidden (403)
        resp_q_denied = self.client.post(f'/api/event/{ev_id}/live/questions',
                                         data=json.dumps({'question': 'Can online viewers ask?'}),
                                         content_type='application/json')
        self.assertEqual(resp_q_denied.status_code, 403)

        # 4. Unlock with invalid ticket code -> Fails (400)
        resp_unlock_bad = self.client.post(f'/api/event/{ev_id}/live/unlock-ticket',
                                           data=json.dumps({'ticket_code': 'TKT-999-99999'}),
                                           content_type='application/json')
        self.assertEqual(resp_unlock_bad.status_code, 400)
        self.assertFalse(resp_unlock_bad.get_json()['success'])

        # 5. Unlock with valid registered ticket code -> SUCCESS (Free for in-person registered)
        resp_unlock_ok = self.client.post(f'/api/event/{ev_id}/live/unlock-ticket',
                                          data=json.dumps({'ticket_code': ticket_code}),
                                          content_type='application/json')
        self.assertEqual(resp_unlock_ok.status_code, 200)
        unlock_res = resp_unlock_ok.get_json()
        self.assertTrue(unlock_res['success'])
        self.assertEqual(unlock_res['access_type'], 'registered_ticket')

        # Now live data shows access granted
        resp_live_data_after = self.client.get(f'/api/event/{ev_id}/live/data')
        self.assertTrue(resp_live_data_after.get_json()['access']['has_access'])

        # 6. Now posting question succeeds (200)
        resp_q_ok = self.client.post(f'/api/event/{ev_id}/live/questions',
                                     data=json.dumps({'question': 'Will slides and projection replay be shared?'}),
                                     content_type='application/json')
        self.assertEqual(resp_q_ok.status_code, 200)
        self.assertTrue(resp_q_ok.get_json()['ok'])

        # 7. Test Virtual Pass Purchase for another online user
        with self.client.session_transaction() as sess:
            sess['loggedin'] = True
            sess['username'] = 'virtual_buyer_user'

        conn = sqlite3.connect(DB_PATH, timeout=15)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO users (username, password, full_name, email, is_admin) VALUES ('virtual_buyer_user', 'hash123', 'Virtual Buyer', 'buyer@test.com', 0)")
        c.execute("DELETE FROM live_stream_passes WHERE username=? AND event_id=?", ('virtual_buyer_user', ev_id))
        conn.commit()
        conn.close()

        resp_purchase = self.client.post(f'/api/event/{ev_id}/live/purchase-pass',
                                         data=json.dumps({'payment_method': 'UPI', 'upi_id': 'buyer@okhdfcbank'}),
                                         content_type='application/json')
        self.assertEqual(resp_purchase.status_code, 200)
        purch_res = resp_purchase.get_json()
        self.assertTrue(purch_res['success'])
        self.assertEqual(purch_res['access_type'], 'paid_virtual')
        self.assertTrue(purch_res['pass_code'].startswith('VPASS-'))

        # Check that buyer now has full access to stream and Q&A
        resp_buyer_live = self.client.get(f'/api/event/{ev_id}/live/data')
        self.assertTrue(resp_buyer_live.get_json()['access']['has_access'])

    def test_16_host_live_studio_broadcaster_and_video_upload(self):
        """Test Host Broadcast Studio control endpoints, YouTube/Custom stream config, and video upload."""
        ev = self._get_upcoming_event()
        self.assertIsNotNone(ev)
        ev_id = ev['id']

        # 1. Non-host tries to update stream config -> FORBIDDEN (403)
        with self.client.session_transaction() as sess:
            sess['loggedin'] = True
            sess['username'] = 'regular_student_user'
            sess['role'] = 'user'
            sess['is_admin'] = 0

        resp_forbidden = self.client.post(f'/api/event/{ev_id}/live/stream-config',
                                          data=json.dumps({'stream_status': 'live', 'source_type': 'youtube'}),
                                          content_type='application/json')
        self.assertEqual(resp_forbidden.status_code, 403)

        # 2. Host/Admin updates stream config to YouTube Live -> SUCCESS
        with self.client.session_transaction() as sess:
            sess['loggedin'] = True
            sess['username'] = 'admin'
            sess['is_admin'] = 1

        resp_cfg_get = self.client.get(f'/api/event/{ev_id}/live/stream-config')
        self.assertEqual(resp_cfg_get.status_code, 200)
        self.assertTrue(resp_cfg_get.get_json()['ok'])

        yt_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        resp_set_yt = self.client.post(f'/api/event/{ev_id}/live/stream-config',
                                       data=json.dumps({
                                           'stream_status': 'live',
                                           'source_type': 'youtube',
                                           'stream_url': yt_url,
                                           'stream_title': 'Keynote Live Broadcast',
                                           'stream_announcement': 'Live stream keynote is in progress!'
                                       }),
                                       content_type='application/json')
        self.assertEqual(resp_set_yt.status_code, 200)
        yt_res = resp_set_yt.get_json()
        self.assertTrue(yt_res['ok'])
        self.assertIn('youtube-nocookie.com/embed/dQw4w9WgXcQ', yt_res['config']['stream_url'])

        # 3. Host uploads a projection video file (.mp4) -> SUCCESS
        import io
        fake_video_bytes = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00isommp42\x00\x00\x00\x08free"
        video_file = (io.BytesIO(fake_video_bytes), 'stage_keynote_demo.mp4')
        resp_upload = self.client.post(f'/api/event/{ev_id}/live/upload-stream-video',
                                       data={'video': video_file},
                                       content_type='multipart/form-data')
        self.assertEqual(resp_upload.status_code, 200)
        upload_res = resp_upload.get_json()
        self.assertTrue(upload_res['ok'])
        self.assertTrue(upload_res['video_url'].endswith('.mp4'))
        self.assertEqual(upload_res['config']['source_type'], 'uploaded_video')
        self.assertEqual(upload_res['config']['stream_status'], 'live')

        # 4. Host pins an audience question to the projection screen
        conn = sqlite3.connect(DB_PATH, timeout=15)
        c = conn.cursor()
        c.execute("INSERT INTO live_questions (event_id, username, question, upvotes) VALUES (?, 'attendee_guru', 'How to scale live WebSockets in production?', 5)", (ev_id,))
        qid = c.lastrowid
        conn.commit()
        conn.close()

        resp_pin = self.client.post(f'/api/event/{ev_id}/live/pin-question',
                                   data=json.dumps({'question_id': qid}),
                                   content_type='application/json')
        self.assertEqual(resp_pin.status_code, 200)
        pin_res = resp_pin.get_json()
        self.assertTrue(pin_res['ok'])
        self.assertEqual(pin_res['pinned_question']['id'], qid)

        # 5. Live data endpoint returns the stream config and pinned question to all viewers
        resp_live = self.client.get(f'/api/event/{ev_id}/live/data')
        self.assertEqual(resp_live.status_code, 200)
        live_data = resp_live.get_json()
        self.assertIn('stream_config', live_data)
        self.assertEqual(live_data['stream_config']['source_type'], 'uploaded_video')
        self.assertEqual(live_data['stream_config']['pinned_question']['id'], qid)

    def test_17_category_exploration_pages_and_filtering(self):
        """Verify dedicated category exploration pages, interactive carousel rendering per category, and domain switcher."""
        with self.client.session_transaction() as sess:
            sess['loggedin'] = True
            sess['username'] = 'test_student_user'

        # 1. Test Dashboard contains category explore links
        resp_dash = self.client.get('/dashboard')
        self.assertEqual(resp_dash.status_code, 200)
        self.assertIn(b'/category/Education', resp_dash.data)
        self.assertIn(b'/category/Sports', resp_dash.data)
        self.assertIn(b'/category/all', resp_dash.data)

        # 2. Test dedicated Category page for Education
        resp_edu = self.client.get('/category/Education')
        self.assertEqual(resp_edu.status_code, 200)
        self.assertIn(b'Education', resp_edu.data)
        self.assertIn(b'Back to Dashboard', resp_edu.data)
        self.assertIn(b'carouselContainer', resp_edu.data)

        # 3. Test dedicated Category page for Sports
        resp_sports = self.client.get('/category/Sports')
        self.assertEqual(resp_sports.status_code, 200)
        self.assertIn(b'Sports', resp_sports.data)
        self.assertIn(b'Back to Dashboard', resp_sports.data)

        # 4. Test dedicated Category page for Music Concerts via /explore alias
        resp_music = self.client.get('/explore/Music Concerts')
        self.assertEqual(resp_music.status_code, 200)
        self.assertIn(b'Music Concerts', resp_music.data)

        # 5. Test All Categories exploration
        resp_all = self.client.get('/category/all')
        self.assertEqual(resp_all.status_code, 200)
        self.assertIn(b'All Categories', resp_all.data)

    def test_18_promo_code_validation_and_conflict_detection(self):
        """Verify promo code validation API and schedule conflict detection."""
        # 1. Test invalid promo code
        resp_invalid = self.client.post('/api/promo/validate', json={'code': 'INVALID999', 'price': '₹800'})
        self.assertEqual(resp_invalid.status_code, 404)
        self.assertFalse(resp_invalid.get_json()['ok'])

        # 2. Test percentage promo code TECH2026 (30% off)
        resp_tech = self.client.post('/api/promo/validate', json={'code': 'TECH2026', 'price': '₹800'})
        self.assertEqual(resp_tech.status_code, 200)
        data_tech = resp_tech.get_json()
        self.assertTrue(data_tech['ok'])
        self.assertEqual(data_tech['discount'], 240.0)
        self.assertEqual(data_tech['final_price'], 560)

        # 3. Test full waiver promo code CAMPUS100 (100% off)
        resp_free = self.client.post('/api/promo/validate', json={'code': 'CAMPUS100', 'price': '₹800'})
        self.assertEqual(resp_free.status_code, 200)
        data_free = resp_free.get_json()
        self.assertTrue(data_free['ok'])
        self.assertEqual(data_free['discount'], 800.0)
        self.assertEqual(data_free['final_price'], 0)


from starlette.testclient import TestClient
try:
    from fastapi_app import fastapi_app
except ImportError:
    from backend.fastapi_app import fastapi_app


class FastAPIApiTests(unittest.TestCase):
    """Automated verification test suite for FastAPI async REST API & Swagger UI."""
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(fastapi_app)

    def test_01_swagger_docs_and_redoc(self):
        """Verify Swagger UI (/docs), ReDoc (/redoc), and OpenAPI schema (/openapi.json)."""
        resp_docs = self.client.get('/docs')
        self.assertEqual(resp_docs.status_code, 200)
        self.assertIn('swagger-ui', resp_docs.text.lower())

        resp_redoc = self.client.get('/redoc')
        self.assertEqual(resp_redoc.status_code, 200)

        resp_openapi = self.client.get('/openapi.json')
        self.assertEqual(resp_openapi.status_code, 200)
        schema = resp_openapi.json()
        self.assertEqual(schema['info']['title'], "Events Booking API")
        self.assertIn('/api/v1/events', schema['paths'])
        self.assertIn('/api/v1/auth/login', schema['paths'])
        self.assertIn('/api/v1/health', schema['paths'])

    def test_02_health_and_metrics_endpoints(self):
        """Verify /api/v1/health and /api/v1/metrics endpoints."""
        resp_health = self.client.get('/api/v1/health')
        self.assertEqual(resp_health.status_code, 200)
        h_data = resp_health.json()
        self.assertEqual(h_data['status'], 'healthy')
        self.assertTrue(h_data['database_connected'])
        self.assertTrue(h_data['events_count'] > 0)

        resp_metrics = self.client.get('/api/v1/metrics')
        self.assertEqual(resp_metrics.status_code, 200)
        m_data = resp_metrics.json()
        self.assertTrue(m_data['total_events'] > 0)
        self.assertTrue(isinstance(m_data['active_categories'], list))

    def test_03_events_api_and_filtering(self):
        """Verify /api/v1/events catalog with search, category filter, and single event."""
        resp_events = self.client.get('/api/v1/events')
        self.assertEqual(resp_events.status_code, 200)
        data = resp_events.json()
        self.assertTrue(data['total'] > 0)
        self.assertTrue(len(data['events']) > 0)

        # Filter by search
        resp_search = self.client.get('/api/v1/events?search=Tech')
        self.assertEqual(resp_search.status_code, 200)

        # Single event
        resp_single = self.client.get('/api/v1/events/1')
        self.assertEqual(resp_single.status_code, 200)
        self.assertEqual(resp_single.json()['id'], 1)

        # Categories
        resp_cats = self.client.get('/api/v1/categories')
        self.assertEqual(resp_cats.status_code, 200)
        self.assertTrue(len(resp_cats.json()) > 0)

    def test_04_auth_login_api(self):
        """Verify /api/v1/auth/login with valid and invalid credentials."""
        # Valid login with 0001
        resp_valid_uid = self.client.post('/api/v1/auth/login', json={'identifier': '0001', 'password': 'password123'})
        self.assertEqual(resp_valid_uid.status_code, 200)
        self.assertTrue(resp_valid_uid.json()['success'])

        # Valid login with email
        resp_valid_email = self.client.post('/api/v1/auth/login', json={'identifier': 'admin@example.com', 'password': 'password123'})
        self.assertEqual(resp_valid_email.status_code, 200)
        self.assertTrue(resp_valid_email.json()['success'])

        # Invalid password
        resp_invalid = self.client.post('/api/v1/auth/login', json={'identifier': '0001', 'password': 'wrongpassword'})
        self.assertEqual(resp_invalid.status_code, 401)

    def test_05_ticket_verification_api(self):
        """Verify ticket validation endpoint."""
        resp_ver = self.client.get('/api/v1/registrations/verify/TKT-999-99999')
        self.assertEqual(resp_ver.status_code, 200)
        self.assertFalse(resp_ver.json()['valid'])

    def test_06_flask_app_mounting_fallback(self):
        """Verify that Flask web pages render through FastAPI mount."""
        resp_root = self.client.get('/')
        self.assertEqual(resp_root.status_code, 200)


if __name__ == '__main__':
    unittest.main()



