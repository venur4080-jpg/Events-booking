import pytest
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from app import app, get_events, get_event_status_info, validate_username_rules, get_db
from datetime import datetime, timedelta

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_ical_download(client):
    events = get_events()
    assert len(events) > 0
    event_id = events[0]['id']
    resp = client.get(f'/event/{event_id}/calendar.ics')
    assert resp.status_code == 200
    assert 'text/calendar' in resp.mimetype
    data = resp.get_data(as_text=True)
    assert 'BEGIN:VCALENDAR' in data
    assert 'BEGIN:VEVENT' in data
    assert 'END:VEVENT' in data
    assert 'END:VCALENDAR' in data
    assert 'SUMMARY:' in data
    assert 'DTSTART:' in data
    assert 'DTEND:' in data

def test_og_image_generation(client):
    events = get_events()
    assert len(events) > 0
    event_id = events[0]['id']
    resp = client.get(f'/event/{event_id}/og-image')
    assert resp.status_code == 200
    assert 'image/svg+xml' in resp.mimetype
    data = resp.get_data(as_text=True)
    assert '<svg' in data
    assert '</svg>' in data
    assert 'Events Booking' in data

def test_dashboard_countdown_and_past_events(client):
    with client.session_transaction() as sess:
        sess['loggedin'] = True
        sess['username'] = 'admin'
        sess['role'] = 'host'
    resp = client.get('/dashboard')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'id="eventCountdownBanner"' in html
    assert 'data-upcoming-events=' in html
    assert 'cdBannerTitle' in html
    assert 'cdBannerSubtitle' in html
    assert 'initCountdownTimer' in html
    assert 'Concluded Event Archives' not in html

def test_expired_events_routing():
    now = datetime.now()
    # Past event (yesterday)
    past_ev = {
        'id': 9991,
        'title': 'Past Concluded Hackathon',
        'date': (now - timedelta(days=2)).strftime('%b %d, %Y'),
        'time': '10:00 AM',
        'end_time': '05:00 PM',
        'venue': 'Campus Lab',
        'seats_total': 50,
        'seats_filled': 10
    }
    status = get_event_status_info(past_ev, ref_now=now)
    assert status['is_expired'] is True
    assert status['status_label'] == 'Event Ended'

    # Future event (tomorrow)
    future_ev = {
        'id': 9992,
        'title': 'Future AI Summit',
        'date': (now + timedelta(days=2)).strftime('%b %d, %Y'),
        'time': '10:00 AM',
        'end_time': '05:00 PM',
        'venue': 'Main Hall',
        'seats_total': 100,
        'seats_filled': 20
    }
    status_f = get_event_status_info(future_ev, ref_now=now)
    assert status_f['is_expired'] is False
    assert status_f['is_open'] is True

    # Today's event whose cutoff has passed
    today_cutoff_ev = {
        'id': 9993,
        'title': 'Today Passed Cutoff Event',
        'date': now.strftime('%b %d, %Y'),
        'time': (now + timedelta(hours=1)).strftime('%I:%M %p'),  # starts in 1h, cutoff was 1h ago
        'end_time': (now + timedelta(hours=6)).strftime('%I:%M %p'),
        'venue': 'Main Hall',
        'seats_total': 100,
        'seats_filled': 20
    }
    status_c = get_event_status_info(today_cutoff_ev, ref_now=now)
    assert status_c['is_expired'] is True
    assert status_c['is_cutoff_reached'] is True
    assert status_c['is_open'] is False

def test_history_and_dashboard_expired_events_routing(client):
    with client.session_transaction() as sess:
        sess['loggedin'] = True
        sess['username'] = 'admin'
        sess['role'] = 'host'

    resp = client.get('/dashboard')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'pastEventsContainer' in html
    assert 'pastEventsSection' in html
    assert 'checkAndTransitionExpiredEvents' in html

    resp_hist = client.get('/history')
    assert resp_hist.status_code == 200
    hist_html = resp_hist.get_data(as_text=True)
    assert 'checkAndTransitionExpiredBookings' in hist_html
    assert 'filterBookings(\'past\'' in hist_html

    resp_api = client.get('/api/events')
    assert resp_api.status_code == 200
    api_json = json.loads(resp_api.get_data(as_text=True))
    assert 'events' in api_json
    if len(api_json['events']) > 0:
        ev0 = api_json['events'][0]
        assert 'is_expired' in ev0
        assert 'end_dt_ms' in ev0
        assert 'cutoff_dt_ms' in ev0

def test_username_validation_rules():
    # Valid usernames (lowercase letters, numbers, allowed symbols: _, ., -)
    assert validate_username_rules('alex_99')[0] is True
    assert validate_username_rules('dev.venu')[0] is True
    assert validate_username_rules('coder-pro_01')[0] is True
    assert validate_username_rules('admin')[0] is True
    assert validate_username_rules('venu_r')[0] is True

    # Invalid usernames: uppercase letters disallowed
    ok, err = validate_username_rules('Alex_99')
    assert ok is False
    assert 'small (lowercase)' in err.lower() or 'lowercase' in err.lower()

    # Invalid usernames: spaces disallowed
    ok, err = validate_username_rules('venu r')
    assert ok is False
    assert 'spaces' in err.lower()

    # Invalid usernames: disallowed symbols disallowed
    ok, err = validate_username_rules('alex@dev')
    assert ok is False
    assert 'allowed symbols' in err.lower()

    ok, err = validate_username_rules('alex#99')
    assert ok is False

    # Invalid usernames: length constraint
    ok, err = validate_username_rules('ab')
    assert ok is False
    assert 'at least 3 characters' in err.lower()

    # Invalid usernames: must start with letter or number
    ok, err = validate_username_rules('_alex')
    assert ok is False
    assert 'must start with a small letter' in err.lower()

def test_check_username_endpoint(client):
    # Format error check
    resp = client.get('/api/check-username?username=Invalid User')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['available'] is False
    assert 'spaces' in data['message'].lower()

    # Upper case error check
    resp = client.get('/api/check-username?username=AlexDev')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['available'] is False

    # Already taken check
    resp = client.get('/api/check-username?username=admin')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['available'] is False
    assert 'in use' in data['message'].lower()

    # Available check
    resp = client.get('/api/check-username?username=new_valid_coder_99')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['available'] is True
    assert '@new_valid_coder_99' in data['message']

def test_existing_admin_usernames_updated():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT username, role, is_admin FROM users WHERE username IN ('admin', 'venu_r')")
    rows = {r[0]: {'role': r[1], 'is_admin': r[2]} for r in c.fetchall()}
    assert 'admin' in rows, "Admin user must exist"
    assert rows['admin']['role'] == 'host'
    assert 'venu_r' in rows, "venu_r user must exist and be updated from Venu R"
    assert rows['venu_r']['role'] == 'host'

def test_legacy_session_auto_sync_and_profile_access(client):
    # Simulate a user browser that was logged in as 'Venu R' prior to username migration
    with client.session_transaction() as sess:
        sess['loggedin'] = True
        sess['username'] = 'Venu R'  # Legacy username with space and capital letters
        sess['role'] = 'host'
        sess['is_admin'] = 1

    # Access /profile - must return 200 OK without "User profile not found"
    resp = client.get('/profile')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'User profile not found' not in html
    assert 'venu_r' in html or 'Venu R' in html

    # Access /settings - must return 200 OK without 404
    resp_settings = client.get('/settings')
    assert resp_settings.status_code == 200
    html_settings = resp_settings.get_data(as_text=True)
    assert 'User profile not found' not in html_settings

def test_navbar_realtime_clock_no_title_tooltip(client):
    with client.session_transaction() as sess:
        sess['loggedin'] = True
        sess['username'] = 'venu_r'
        sess['role'] = 'host'
    
    resp = client.get('/dashboard')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'class="nav-clock-widget"' in html
    assert 'class="clock-time"' in html
    assert 'class="clock-date"' in html
    # Verify no title tooltip on the clock widget
    assert 'title="Current Real Time (System Clock)"' not in html

def test_navbar_welcome_message_no_handle_pill(client):
    with client.session_transaction() as sess:
        sess['loggedin'] = True
        sess['username'] = 'venu_r'
        sess['user_display_name'] = 'Venu R'
        sess['role'] = 'host'
    
    resp = client.get('/dashboard')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'Welcome,' in html
    assert 'Venu R' in html
    # Ensure @handle pill is not shown in the navbar welcome message
    assert 'navbar-handle-pill' not in html
    assert '@venu_r' not in html[:html.find('nav-links') + 600]

def test_settings_2fa_button_sizing(client):
    with client.session_transaction() as sess:
        sess['loggedin'] = True
        sess['username'] = 'venu_r'
        sess['user_display_name'] = 'Venu R'
        sess['role'] = 'host'
    
    resp = client.get('/settings')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'btn-enable-2fa' in html
    assert 'btn-verify-2fa' in html
    # Ensure Enable Authenticator 2FA does not use oversized unique-save-btn
    assert 'class="unique-save-btn">Enable Authenticator 2FA' not in html

def test_user_agent_parsing_and_session_display(client):
    from app import parse_device_info, get_db

    # 1. Test parser directly
    d1 = parse_device_info('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    assert d1['name'] == 'Chrome on Windows'
    assert d1['icon'] == '💻'

    d2 = parse_device_info('Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1')
    assert d2['name'] == 'Safari on iPhone'
    assert d2['icon'] == '📱'

    d3 = parse_device_info('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0')
    assert d3['name'] == 'Edge on macOS'

    d4 = parse_device_info('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/158.0.0.0 Safari/537.36 Edg/158.0.0.0')
    assert d4['name'] == 'Edge on Windows'

    # 2. Insert test login session into DB for venu_r
    import secrets
    test_tok = f"tok_ua_test_{secrets.token_hex(8)}"
    conn = get_db()
    c = conn.cursor()
    c.execute(
        """INSERT INTO user_login_sessions (session_token, username, ip_address, user_agent, device_name, login_method, is_active)
           VALUES (?, 'venu_r', '127.0.0.1', ?, ?, 'password', 1)""",
        (test_tok, 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/158.0.0.0 Safari/537.36 Edg/158.0.0.0', 'Edge on Windows')
    )
    conn.commit()
    conn.close()

    # 3. Access /settings and verify rendered table
    with client.session_transaction() as sess:
        sess['loggedin'] = True
        sess['username'] = 'venu_r'
        sess['user_display_name'] = 'Venu R'
        sess['role'] = 'host'
    
    resp = client.get('/settings')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'Edge on Windows' in html
    assert 'AppleWebKi</td>' not in html  # Must not display truncated raw UA in table cell
    assert 'AppleWebKi</span>' not in html
    assert 'ua-parser.min.js' in html

def test_admin_only_access_and_host_restrictions(client):
    # Setup a non-admin host user in db
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (username, password, role, is_admin, email, full_name) VALUES ('test_host_1', 'pass123', 'host', 0, 'host1@test.com', 'Test Host One')")
    c.execute("UPDATE users SET role = 'host', is_admin = 0 WHERE username = 'test_host_1'")
    conn.commit()
    c.execute("SELECT id FROM users WHERE username = 'test_host_1'")
    h_uid = c.fetchone()[0]
    conn.close()

    # Non-admin host attempts to access admin panel routes
    with client.session_transaction() as sess:
        sess['loggedin'] = True
        sess['username'] = 'test_host_1'
        sess['role'] = 'host'
        sess['is_admin'] = False

    resp = client.get('/admin/users', follow_redirects=False)
    assert resp.status_code == 302  # Blocked from admin users

    resp2 = client.post(f'/admin/users/{h_uid}/promote', follow_redirects=False)
    assert resp2.status_code == 302  # Blocked from promote

    resp3 = client.post(f'/admin/users/{h_uid}/demote', follow_redirects=False)
    assert resp3.status_code == 302  # Blocked from demote

    resp4 = client.post(f'/admin/users/{h_uid}/delete', follow_redirects=False)
    assert resp4.status_code == 302  # Blocked from delete

    resp5 = client.get(f'/admin/user/{h_uid}', follow_redirects=False)
    assert resp5.status_code == 302  # Blocked from admin user dossier


def test_host_my_events_and_event_attribution(client):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM events WHERE created_by IN ('organizer_bob', 'host_clara') OR title LIKE '%Admin Mega Gala%'")
    c.execute("INSERT OR IGNORE INTO users (username, password, role, is_admin, email, full_name) VALUES ('organizer_bob', 'pass123', 'host', 0, 'bob@test.com', 'Organizer Bob')")
    c.execute("UPDATE users SET role = 'host', is_admin = 0 WHERE username = 'organizer_bob'")
    
    # Create an event created by organizer_bob and one created by admin with distinct image paths
    c.execute("""INSERT INTO events (title, date, time, end_time, desc, price, venue, seats_total, seats_filled, image, created_by, updated_by)
                 VALUES ('Bob Secret Summit', 'Dec 25, 2026', '10:00 AM', '04:00 PM', 'Bob desc', 'Free', 'Bob Hall', 100, 5, '/static/event_images/test_bob_summit.jpg', 'organizer_bob', 'organizer_bob')""")
    bob_eid = c.lastrowid

    c.execute("""INSERT INTO events (title, date, time, end_time, desc, price, venue, seats_total, seats_filled, image, created_by, updated_by)
                 VALUES ('Admin Mega Gala', 'Dec 28, 2026', '11:00 AM', '05:00 PM', 'Admin desc', 'Free', 'Grand Arena', 500, 20, '/static/event_images/test_admin_gala.jpg', 'admin', 'admin')""")
    admin_eid = c.lastrowid
    conn.commit()
    conn.close()

    try:
        # Organizer Bob visits /host/my-events
        with client.session_transaction() as sess:
            sess['loggedin'] = True
            sess['username'] = 'organizer_bob'
            sess['role'] = 'host'
            sess['is_admin'] = False

        resp = client.get('/host/my-events')
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert 'Bob Secret Summit' in html
        assert 'Admin Mega Gala' not in html  # Isolation: Bob does not see Admin's event in My Hosted Events

        # Bob attempts to delete Admin's event -> must be rejected
        del_resp = client.post(f'/delete_event/{admin_eid}', follow_redirects=False)
        assert del_resp.status_code == 302  # Redirected with error

        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id FROM events WHERE id = ?", (admin_eid,))
        assert c.fetchone() is not None  # Admin event was NOT deleted!

        # Bob can delete his own event
        del_own = client.post(f'/delete_event/{bob_eid}', follow_redirects=False)
        assert del_own.status_code == 302
        c.execute("SELECT id FROM events WHERE id = ?", (bob_eid,))
        assert c.fetchone() is None  # Bob's own event was successfully deleted
        conn.close()
    finally:
        conn = get_db()
        c = conn.cursor()
        c.execute("DELETE FROM events WHERE id IN (?, ?)", (bob_eid, admin_eid))
        conn.commit()
        conn.close()


def test_admin_user_profile_dossier_and_events_count(client):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM events WHERE created_by = 'host_clara'")
    c.execute("INSERT OR IGNORE INTO users (username, password, role, is_admin, email, full_name) VALUES ('host_clara', 'pass123', 'host', 0, 'clara@test.com', 'Clara Schumann')")
    c.execute("UPDATE users SET role = 'host', is_admin = 0 WHERE username = 'host_clara'")
    
    # Add 2 events for Clara with distinct images
    c.execute("""INSERT INTO events (title, date, time, end_time, desc, price, venue, seats_total, seats_filled, image, created_by, updated_by)
                 VALUES ('Clara Chamber Night', 'Jan 15, 2027', '07:00 PM', '10:00 PM', 'Chamber concert', '₹499', 'Symphony Hall', 80, 12, '/static/event_images/test_clara_1.jpg', 'host_clara', 'host_clara')""")
    e1 = c.lastrowid
    c.execute("""INSERT INTO events (title, date, time, end_time, desc, price, venue, seats_total, seats_filled, image, created_by, updated_by)
                 VALUES ('Clara Piano Masterclass', 'Jan 16, 2027', '02:00 PM', '05:00 PM', 'Masterclass', '₹999', 'Studio A', 30, 8, '/static/event_images/test_clara_2.jpg', 'host_clara', 'host_clara')""")
    e2 = c.lastrowid
    conn.commit()
    c.execute("SELECT id FROM users WHERE username = 'host_clara'")
    clara_uid = c.fetchone()[0]
    conn.close()

    try:
        # Admin visits /admin/users
        with client.session_transaction() as sess:
            sess['loggedin'] = True
            sess['username'] = 'admin'
            sess['role'] = 'host'
            sess['is_admin'] = True

        resp = client.get('/admin/users')
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert 'Events Hosted' in html
        assert f'/admin/user/{clara_uid}' in html
        assert '2 Events' in html  # Clara has 2 hosted events badge

        # Admin visits Clara's profile dossier
        resp_prof = client.get(f'/admin/user/{clara_uid}')
        assert resp_prof.status_code == 200
        prof_html = resp_prof.get_data(as_text=True)
        assert 'Clara Schumann' in prof_html
        assert '@host_clara' in prof_html
        assert 'Clara Chamber Night' in prof_html
        assert 'Clara Piano Masterclass' in prof_html
        assert 'Added: <strong style="color: #38bdf8;">@host_clara</strong>' in prof_html
    finally:
        conn = get_db()
        c = conn.cursor()
        c.execute("DELETE FROM events WHERE id IN (?, ?)", (e1, e2))
        conn.commit()
        conn.close()


def test_instant_role_revocation_on_demotion(client):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (username, password, role, is_admin, email, full_name) VALUES ('host_david', 'pass123', 'host', 0, 'david@test.com', 'David Host')")
    c.execute("UPDATE users SET role = 'host', is_admin = 0 WHERE username = 'host_david'")
    conn.commit()
    c.execute("SELECT id FROM users WHERE username = 'host_david'")
    david_uid = c.fetchone()[0]
    conn.close()

    # David has host session
    with client.session_transaction() as sess:
        sess['loggedin'] = True
        sess['username'] = 'host_david'
        sess['role'] = 'host'
        sess['is_admin'] = False

    # Verify David can initially access /host/my-events
    resp1 = client.get('/host/my-events')
    assert resp1.status_code == 200

    # Admin demotes David to normal user in DB
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET role = 'user' WHERE id = ?", (david_uid,))
    conn.commit()
    conn.close()

    # On David's next request, before_request synchronizes session['role'] to 'user'
    resp2 = client.get('/host/my-events', follow_redirects=False)
    assert resp2.status_code == 302  # Denied! Redirected to dashboard
    with client.session_transaction() as sess:
        assert sess.get('role') == 'user'  # Instant session sync!

    # David visits dashboard as normal user -> sees home page, no Host Management
    resp_dash = client.get('/dashboard')
    assert resp_dash.status_code == 200
    dash_html = resp_dash.get_data(as_text=True)
    assert 'Host Management' not in dash_html  # Host tools completely hidden for demoted user!





