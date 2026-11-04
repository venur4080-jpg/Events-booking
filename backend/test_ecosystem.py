import unittest
import json
import sqlite3
import io
from backend.app import app, get_db

class EcosystemModulesTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['SECRET_KEY'] = 'test-secret-key-123'
        self.client = self.app.test_client()

        # Pick an event id that exists
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id FROM events LIMIT 1")
        row = c.fetchone()
        self.event_id = row[0] if row else 1

        # Pick or create a test session id
        c.execute("SELECT id FROM event_agenda_sessions WHERE event_id = ? LIMIT 1", (self.event_id,))
        sess_row = c.fetchone()
        if not sess_row:
            c.execute("INSERT INTO event_agenda_sessions (event_id, title, start_time, end_time) VALUES (?, 'Test Session', '10:00 AM', '11:00 AM')", (self.event_id,))
            conn.commit()
            self.session_id = c.lastrowid
        else:
            self.session_id = sess_row[0]

        # Pick or create an active registration for ticket test
        c.execute("SELECT ticket_code FROM registrations WHERE event_id = ? AND ticket_code != '' LIMIT 1", (self.event_id,))
        tkt_row = c.fetchone()
        if not tkt_row:
            self.ticket_number = f"TKT-{self.event_id:03d}-99999"
            c.execute("""INSERT INTO registrations (event_id, username, full_name, email, phone, ticket_code, status, checked_in)
                         VALUES (?, 'test_attendee', 'Test Attendee', 'attendee@test.com', '9876543210', ?, 'confirmed', 0)""",
                      (self.event_id, self.ticket_number))
            conn.commit()
        else:
            self.ticket_number = tkt_row[0]

        conn.close()

    def login_as(self, username='test_subscriber', role='user', is_admin=0):
        with self.client.session_transaction() as sess:
            sess['loggedin'] = True
            sess['username'] = username
            sess['role'] = role
            sess['is_admin'] = is_admin
            sess['user_id'] = 'UID-9999'

    def test_01_event_agenda_page(self):
        """Test GET /event/<event_id>/agenda renders properly"""
        self.login_as()
        res = self.client.get(f'/event/{self.event_id}/agenda')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Multi-Stage Schedule', res.data)
        self.assertIn(b'AI Schedule Concierge', res.data)

    def test_02_toggle_save_agenda(self):
        """Test POST /api/agenda/<session_id>/toggle-save adds & removes bookmark"""
        self.login_as()
        # Save session
        res = self.client.post(f'/api/agenda/{self.session_id}/toggle-save')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['ok'])
        self.assertTrue(data['saved'])

        # Toggle again to remove
        res2 = self.client.post(f'/api/agenda/{self.session_id}/toggle-save')
        data2 = json.loads(res2.data)
        self.assertTrue(data2['ok'])
        self.assertFalse(data2['saved'])

    def test_03_kiosk_page_and_checkin(self):
        """Test on-site kiosk check-in & badge sheet"""
        # Kiosk Page
        res = self.client.get(f'/kiosk/{self.event_id}')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Venue Self Check-in Kiosk', res.data)

        # Kiosk Check-in API
        res_chk = self.client.post('/api/kiosk/checkin-and-print', json={
            'event_id': self.event_id,
            'query': self.ticket_number
        })
        self.assertEqual(res_chk.status_code, 200)
        data = json.loads(res_chk.data)
        self.assertTrue(data['ok'])
        self.assertEqual(data['attendee']['ticket_number'], self.ticket_number)

        # Badge Sheet Print View
        res_badge = self.client.get(f'/kiosk/{self.event_id}/badge-sheet/{self.ticket_number}')
        self.assertEqual(res_badge.status_code, 200)
        self.assertIn(b'OFFICIAL ATTENDEE PASS', res_badge.data)

    def test_04_mobile_wallet_pass(self):
        """Test digital Apple/Google wallet mobile pass template"""
        res = self.client.get(f'/ticket/{self.ticket_number}/mobile-pass')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Apple Wallet', res.data)
        self.assertIn(b'Add to Apple Wallet', res.data)

    def test_05_b2b_expo_and_sponsor_leads(self):
        """Test B2B Expo floor, sponsor lead capture, and CSV export"""
        self.login_as()
        # Expo Floor View
        res_expo = self.client.get(f'/event/{self.event_id}/expo')
        self.assertEqual(res_expo.status_code, 200)
        self.assertIn(b'Expo Hall', res_expo.data)

        # Capture Lead
        res_lead = self.client.post('/api/sponsor/lead-capture', json={
            'ticket_number': self.ticket_number,
            'notes': 'Interested in enterprise cloud partnership'
        })
        self.assertEqual(res_lead.status_code, 200)
        data = json.loads(res_lead.data)
        self.assertTrue(data['ok'])

        # Export Leads CSV
        res_csv = self.client.get('/api/sponsor/leads/export')
        self.assertEqual(res_csv.status_code, 200)
        self.assertIn(b'Attendee Name', res_csv.data)
        self.assertIn(b'Interested in enterprise cloud partnership', res_csv.data)

    def test_06_peer_networking_and_connect(self):
        """Test peer networking matchmaker, 1-on-1 invite, and speed lounge"""
        self.login_as(username='aarav_dev')
        # Networking Hub
        res_net = self.client.get(f'/event/{self.event_id}/networking')
        self.assertEqual(res_net.status_code, 200)
        self.assertIn(b'Smart Peer Networking', res_net.data)

        # Connect Invite
        res_conn = self.client.post('/api/networking/connect', json={
            'event_id': self.event_id,
            'receiver': 'Venu R',
            'message': 'Lets team up for the AI hackathon track!'
        })
        self.assertEqual(res_conn.status_code, 200)
        data = json.loads(res_conn.data)
        self.assertTrue(data['ok'])

        # Speed Networking Lounge
        res_speed = self.client.get(f'/event/{self.event_id}/speed-networking')
        self.assertEqual(res_speed.status_code, 200)
        self.assertIn(b'Virtual Speed Networking Lounge', res_speed.data)

    def test_07_group_squad_registration(self):
        """Test squad bulk booking with automated volume discount"""
        self.login_as(username='squad_lead')
        # Group booking page
        res_grp = self.client.get(f'/event/{self.event_id}/group-booking')
        self.assertEqual(res_grp.status_code, 200)
        self.assertTrue(b'Squad &amp; Group Booking' in res_grp.data or b'Squad' in res_grp.data)

        # Register a 3-member squad
        squad_data = {
            'group_name': 'Cloud Ninjas',
            'attendees': [
                {'name': 'Lead Dev', 'email': 'lead@ninjas.com', 'phone': '9111111111'},
                {'name': 'Frontend Dev', 'email': 'fe@ninjas.com', 'phone': '9222222222'},
                {'name': 'ML Dev', 'email': 'ml@ninjas.com', 'phone': '9333333333'}
            ]
        }
        res_reg = self.client.post(f'/api/event/{self.event_id}/group-register', json=squad_data)
        self.assertEqual(res_reg.status_code, 200)
        data = json.loads(res_reg.data)
        self.assertTrue(data['ok'])
        self.assertEqual(len(data['tickets']), 3)

    def test_08_ai_schedule_concierge(self):
        """Test AI Schedule Concierge optimization algorithm"""
        res_ai = self.client.post('/api/ai/schedule-concierge', json={
            'event_id': self.event_id,
            'interests': 'AI, Cloud, Python'
        })
        self.assertEqual(res_ai.status_code, 200)
        data = json.loads(res_ai.data)
        self.assertTrue(data['ok'])
        self.assertIn('recommended_sessions', data)

if __name__ == '__main__':
    unittest.main()
