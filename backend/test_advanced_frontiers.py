import unittest
import os
import json
import sqlite3
from backend.app import app, get_db

class AdvancedFrontiersTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id, title FROM events LIMIT 1")
        ev = c.fetchone()
        self.event_id = ev[0] if ev else 1

        c.execute("SELECT ticket_code FROM registrations WHERE event_id = ? AND status = 'active' LIMIT 1", (self.event_id,))
        tkt = c.fetchone()
        if not tkt:
            self.ticket_code = "TKT-001-88888"
            c.execute("""INSERT INTO registrations (username, event_id, full_name, email, phone, ticket_code, seat_code, amount_paid, status)
                         VALUES ('test_host', ?, 'Frontier Delegate', 'frontier@test.io', '+91 9999988888', ?, 'B-04', 699.0, 'active')""",
                      (self.event_id, self.ticket_code))
            conn.commit()
        else:
            self.ticket_code = tkt[0]
        conn.close()

    def login_as(self, username='test_host', is_admin=1):
        with self.client.session_transaction() as sess:
            sess['loggedin'] = True
            sess['username'] = username
            sess['user_id'] = 'UID-7777'
            sess['is_admin'] = is_admin
            sess['role'] = 'host'

    def test_01_magic_event_generation(self):
        """Test AI Co-Pilot 1-prompt full event synthesis"""
        self.login_as()
        prompt = "Bangalore GenAI Hackathon & Cloud Summit with ₹799 Early Bird passes and mentor clinics"
        res = self.client.post('/api/ai/magic-generate-event', json={'prompt': prompt})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['ok'])
        self.assertIn('event_id', data)
        self.assertIn('redirect_url', data)
        # Clean up synthetic test event so users.db stays clean across repeated test runs
        new_id = data.get('event_id')
        if new_id and new_id > 10031:
            conn = get_db()
            c = conn.cursor()
            for tbl in ('event_pricing_tiers', 'event_agenda_sessions', 'event_agenda_tracks', 'event_coupons'):
                try:
                    c.execute(f"DELETE FROM {tbl} WHERE event_id = ?", (new_id,))
                except Exception:
                    pass
            c.execute("DELETE FROM events WHERE id = ?", (new_id,))
            conn.commit()
            conn.close()

    def test_02_whatsapp_ticket_card(self):
        """Test WhatsApp ticket delivery with formatted QR link and directions"""
        res = self.client.get(f'/ticket/{self.ticket_code}/whatsapp?format=json')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['ok'])
        self.assertIn('whatsapp_url', data)
        self.assertIn('OFFICIAL EVENT PASS', data['message'])

    def test_03_urgent_broadcast_messenger(self):
        """Test host emergency broadcast dispatch"""
        self.login_as()
        # View broadcast page
        res_page = self.client.get(f'/event/{self.event_id}/broadcast')
        self.assertEqual(res_page.status_code, 200)
        self.assertIn(b'Urgent Attendee Broadcast Messenger', res_page.data)

        # Dispatch alert
        res_post = self.client.post(f'/api/event/{self.event_id}/send-broadcast', json={
            'headline': 'Stage Hall Relocation',
            'message_body': 'Keynote moved to Auditorium A. Doors open in 10 minutes.',
            'channel': 'all'
        })
        self.assertEqual(res_post.status_code, 200)
        data = res_post.get_json()
        self.assertTrue(data['ok'])
        self.assertIn('recipient_count', data)

    def test_04_offline_turnstile_manifest(self):
        """Test 100% offline turnstile PWA cache manifest generation"""
        res = self.client.get(f'/api/kiosk/{self.event_id}/offline-manifest')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['ok'])
        self.assertIn('tickets', data)
        self.assertIn('manifest_version', data)

    def test_05_embed_booking_widget(self):
        """Test external website embeddable booking card"""
        res = self.client.get(f'/embed/event/{self.event_id}')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Book Passes Now', res.data)
        self.assertIn(b'Powered by Events Booking Ecosystem', res.data)

    def test_06_stage_trivia_and_buzzer(self):
        """Test Kahoot-style stage projector view and attendee buzzer scoring"""
        self.login_as(username='Venu R')
        # Big-screen view
        res_stage = self.client.get(f'/event/{self.event_id}/stage-trivia')
        self.assertEqual(res_stage.status_code, 200)
        self.assertIn(b'Live Trivia Arena', res_stage.data)

        # Attendee buzzer join
        res_ctrl = self.client.get(f'/event/{self.event_id}/trivia-join')
        self.assertEqual(res_ctrl.status_code, 200)
        self.assertIn(b'Attendee Buzzer', res_ctrl.data)

        # Submit answer buzz
        res_buzz = self.client.post(f'/api/event/{self.event_id}/trivia-submit', json={
            'question_id': 1,
            'option': 'A',
            'time_taken_ms': 2500
        })
        self.assertEqual(res_buzz.status_code, 200)
        data = res_buzz.get_json()
        self.assertTrue(data['ok'])
        self.assertTrue(data['is_correct'])
        self.assertGreater(data['points_awarded'], 500)

if __name__ == '__main__':
    unittest.main()
