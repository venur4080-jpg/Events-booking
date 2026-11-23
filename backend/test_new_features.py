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


