import pytest
import sys
import os

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
    assert 'session-device-label' in html




