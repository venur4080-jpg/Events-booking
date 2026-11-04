import unittest
import os
import json
import sqlite3
import re
from backend.app import app, get_db

class ExpansionEcosystemTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

        # Connect to test database and fetch an active event
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id, title FROM events LIMIT 1")
        ev = c.fetchone()
        self.event_id = ev[0] if ev else 1
        
        # Ensure a test registration exists
        c.execute("""SELECT ticket_code FROM registrations WHERE event_id = ? AND status = 'active' LIMIT 1""", (self.event_id,))
        tkt = c.fetchone()
        if not tkt:
            self.ticket_code = "TKT-001-99999"
            c.execute("""INSERT INTO registrations (username, event_id, full_name, email, phone, ticket_code, seat_code, amount_paid, status)
                         VALUES ('test_host', ?, 'Test Delegate', 'delegate@test.io', '+91 9876543210', ?, 'A-14', 499.0, 'active')""",
                      (self.event_id, self.ticket_code))
            conn.commit()
        else:
            self.ticket_code = tkt[0]
        conn.close()

    def login_as(self, username='test_host', is_admin=1):
        with self.client.session_transaction() as sess:
            sess['loggedin'] = True
            sess['username'] = username
            sess['user_id'] = 'UID-9999'
            sess['is_admin'] = is_admin
            sess['role'] = 'host'

    def test_01_apply_coupon_discount(self):
        """Test coupon validation, percentage & flat discounts"""
        # Test valid percentage coupon
        res = self.client.post(f'/api/event/{self.event_id}/apply-coupon', json={
            'coupon_code': 'TECH20',
            'amount': 500.0
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['discount_amount'], 100.0) # 20% of 500 = 100
        self.assertEqual(data['final_amount'], 400.0)

        # Test invalid coupon
        res_invalid = self.client.post(f'/api/event/{self.event_id}/apply-coupon', json={
            'coupon_code': 'FAKECODE99',
            'amount': 500.0
        })
        self.assertEqual(res_invalid.status_code, 404)
        self.assertFalse(res_invalid.get_json()['ok'])

    def test_02_pricing_tiers(self):
        """Test staged pricing waves and remaining allocation"""
        res = self.client.get(f'/api/event/{self.event_id}/pricing-tiers')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['ok'])
        self.assertGreaterEqual(len(data['tiers']), 1)
        self.assertIn('tier_name', data['tiers'][0])

    def test_03_marketing_studio(self):
        """Test AI social flyer generator & drip sequences page"""
        self.login_as()
        res = self.client.get(f'/event/{self.event_id}/marketing-studio')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'AI Marketing &amp; Viral Promo Studio', res.data)
        self.assertIn(b'flyerCanvas', res.data)

    def test_04_referral_stats(self):
        """Test attendee referral link and unlocked perks"""
        self.login_as(username='Venu R')
        res = self.client.get(f'/api/event/{self.event_id}/referral-stats')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['ok'])
        self.assertIn('ref_code', data)
        self.assertIn('share_url', data)

    def test_05_interactive_floorplan(self):
        """Test venue SVG floorplan and seat wayfinding"""
        res = self.client.get(f'/event/{self.event_id}/floorplan?seat=A-14')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Interactive Venue Floorplan', res.data)
        self.assertIn(b'svgMap', res.data)
        self.assertIn(b'routeLine', res.data)

    def test_06_hybrid_livestream(self):
        """Test live video room & multilingual AI speech subtitles"""
        res = self.client.get(f'/event/{self.event_id}/livestream')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Live AI Speech Translation', res.data)
        self.assertIn(b'langSelect', res.data)

    def test_07_host_treasury_and_payout(self):
        """Test treasury financial ledger and payout request"""
        self.login_as()
        # View treasury
        res = self.client.get('/host/treasury')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Host Revenue &amp; Instant Payouts', res.data)
        self.assertIn(b'Gross Ticket Sales', res.data)

        # Submit payout request
        res_pay = self.client.post('/api/host/payout-request', json={
            'amount': 2500.0,
            'payout_method': 'UPI',
            'account_identifier': 'host@upi'
        })
        self.assertEqual(res_pay.status_code, 200)
        self.assertTrue(res_pay.get_json()['ok'])

    def test_08_gst_tax_invoice(self):
        """Test official GST tax invoice generation (SAC 998596)"""
        res = self.client.get(f'/invoice/{self.ticket_code}/gst')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'TAX INVOICE', res.data)
        self.assertIn(b'998596', res.data)
        self.assertIn(b'CGST', res.data)
        self.assertIn(b'SGST', res.data)

    def test_09_post_event_feedback(self):
        """Test verified attendee NPS feedback submission"""
        self.login_as(username='test_attendee')
        res = self.client.post(f'/api/event/{self.event_id}/feedback', json={
            'rating_content': 5,
            'rating_venue': 5,
            'rating_speakers': 5,
            'nps_score': 10,
            'review_text': 'Exceptional conference! The interactive kiosk and mobile passes made check-in a breeze.'
        })
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()['ok'])

    def test_10_host_team_management(self):
        """Test team RBAC staff management and invites"""
        self.login_as()
        # View team
        res = self.client.get('/host/team')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Organization Staff &amp; Role Management', res.data)

        # Invite staff member
        res_inv = self.client.post('/api/host/team/invite', json={
            'email': 'gate_turnstile@events.io',
            'role': 'scanner'
        })
        self.assertEqual(res_inv.status_code, 200)
        self.assertTrue(res_inv.get_json()['ok'])

if __name__ == '__main__':
    unittest.main()
