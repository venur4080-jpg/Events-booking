"""
FastAPI Application Architecture for Events Management System
Integrates native async REST API endpoints, Pydantic validation schemas,
interactive Swagger UI (/docs) and ReDoc (/redoc), with seamless WSGI mounting
of the existing Flask Web Portal.
"""
from typing import List, Optional, Any, Dict
from datetime import datetime
import json
import os
import sys
import sqlite3
from contextlib import asynccontextmanager

from fastapi import FastAPI, APIRouter, HTTPException, Query, Path, status, Request
from fastapi.middleware.cors import CORSMiddleware
from a2wsgi import WSGIMiddleware
from pydantic import BaseModel, Field

# Import existing backend modules, database helpers, and bcrypt
try:
    import backend.app as backend_module
except ImportError:
    import app as backend_module

get_db = backend_module.get_db
get_events_cached = backend_module.get_events
invalidate_events_cache = backend_module.invalidate_events_cache
get_category = backend_module.get_category
get_event_status_info = backend_module.get_event_status_info
check_password_cached = backend_module.check_password_cached
bcrypt = backend_module.bcrypt
flask_app = backend_module.app


# ============================================================================
# PYDANTIC SCHEMAS & DATA CONTRACTS
# ============================================================================

class StandardApiResponse(BaseModel):
    success: bool = True
    message: str = "Operation completed successfully"
    data: Optional[Any] = None


class SystemHealthResponse(BaseModel):
    status: str = "healthy"
    version: str = "2.0.0"
    framework: str = "FastAPI + Flask WSGI Hybrid"
    timestamp: str
    database_connected: bool = True
    events_count: int
    users_count: int


class SystemMetricsResponse(BaseModel):
    total_events: int
    total_users: int
    total_registrations: int
    total_checked_in: int
    overall_occupancy_rate_percent: float
    active_categories: List[str]


class EventResponse(BaseModel):
    id: int
    title: str
    date: str
    time: str = "10:00 AM"
    end_time: str = "05:00 PM"
    desc: str
    price: str = "Free"
    color: str = "#4facfe"
    image: str
    purpose: Optional[str] = ""
    full_details: Optional[str] = ""
    outcome: Optional[str] = ""
    venue: str = "Main Campus Auditorium"
    venue_address: str = "Bangalore, India"
    seats_total: int = 100
    seats_filled: int = 0
    seats_available: int = 100
    featured: int = 0
    category: str = "General"
    is_sold_out: bool = False
    status_label: Optional[str] = "Registration Open"
    status_badge: Optional[str] = "open"


class EventListResponse(BaseModel):
    total: int
    count: int
    page: int
    limit: int
    categories: List[str]
    events: List[EventResponse]


class EventCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=150, example="Hackathon 2026")
    date: str = Field(..., example="Apr 25, 2026")
    time: str = Field(default="10:00 AM", example="10:00 AM")
    end_time: str = Field(default="05:00 PM", example="05:00 PM")
    desc: str = Field(..., example="24-hour coding hackathon for students")
    price: str = Field(default="Free", example="Free")
    color: str = Field(default="#4facfe", example="#4facfe")
    image: str = Field(default="https://images.unsplash.com/photo-1504384308090-c894fdcc538d?auto=format&fit=crop&w=1200&q=80")
    purpose: Optional[str] = Field(default="", example="Rapid prototyping")
    full_details: Optional[str] = Field(default="", example="Complete rules and breakdown")
    outcome: Optional[str] = Field(default="", example="Prizes and certificates")
    venue: str = Field(default="Main Campus Auditorium", example="BIEC Convention Centre")
    venue_address: str = Field(default="Bangalore, Karnataka", example="Tumkur Road, Bangalore")
    seats_total: int = Field(default=100, ge=1, le=50000, example=250)
    featured: int = Field(default=0, ge=0, le=1)


class UserLoginRequest(BaseModel):
    identifier: str = Field(..., example="0001", description="4-digit User ID (e.g. 0001) or Registered Email Address")
    password: str = Field(..., example="password123", min_length=3)


class UserRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, example="student_dev")
    full_name: str = Field(..., min_length=2, max_length=100, example="John Doe")
    email: str = Field(..., example="john.doe@example.com")
    password: str = Field(..., min_length=6, example="password123")
    phone: Optional[str] = Field(default="", example="9876543210")
    college_id: Optional[str] = Field(default="", example="ENG2026-0042")


class UserResponse(BaseModel):
    id: int
    user_id: Optional[str] = None
    username: str
    full_name: str
    email: str
    phone: Optional[str] = ""
    college_id: Optional[str] = ""
    role: str = "user"
    is_admin: int = 0
    profile_photo: Optional[str] = None


class UserProfileResponse(BaseModel):
    user: UserResponse
    registered_events_count: int
    upcoming_events_count: int


class BookingCreateRequest(BaseModel):
    event_id: int = Field(..., example=1)
    username: str = Field(..., example="student_dev")
    full_name: str = Field(..., example="John Doe")
    email: str = Field(..., example="john.doe@example.com")
    phone: Optional[str] = Field(default="", example="9876543210")
    college_id: Optional[str] = Field(default="", example="ENG2026-0042")
    payment_method: Optional[str] = Field(default="Free Pass", example="Free Pass")
    upi_id: Optional[str] = Field(default="", example="")
    team_name: Optional[str] = Field(default="", example="")
    team_members: Optional[List[Dict[str, str]]] = Field(default=[], example=[])


class BookingResponse(BaseModel):
    id: int
    ticket_code: str
    event_id: int
    event_title: str
    username: str
    full_name: str
    email: str
    payment_method: str
    status: str = "active"
    reg_time: Optional[str] = None
    team_name: Optional[str] = ""
    checked_in: int = 0


class TicketVerificationResponse(BaseModel):
    valid: bool
    ticket_code: str
    status: str
    event_id: Optional[int] = None
    event_title: Optional[str] = None
    attendee_name: Optional[str] = None
    username: Optional[str] = None
    college_id: Optional[str] = None
    team_name: Optional[str] = None
    checked_in: bool = False
    checkin_time: Optional[str] = None
    message: str


class ReviewCreateRequest(BaseModel):
    event_id: int = Field(..., example=1)
    username: str = Field(..., example="student_dev")
    rating: int = Field(..., ge=1, le=5, example=5)
    comment: Optional[str] = Field(default="", example="Outstanding session and great speaker!")


class ReviewResponse(BaseModel):
    id: int
    event_id: int
    username: str
    rating: int
    comment: Optional[str] = ""
    created_at: Optional[str] = None


class NotificationResponse(BaseModel):
    id: int
    username: str
    message: str
    link: Optional[str] = "#"
    is_read: int = 0
    created_at: Optional[str] = None


# ============================================================================
# FASTAPI APPLICATION INSTANTIATION & LIFESPAN
# ============================================================================

tags_metadata = [
    {
        "name": "Health & Diagnostics",
        "description": "System health check, diagnostics, and real-time database connection metrics.",
    },
    {
        "name": "Events",
        "description": "Event catalog operations: filtering by category, search, pagination, and details.",
    },
    {
        "name": "Authentication & Users",
        "description": "User authentication by 4-digit User ID / Email, registration, and profile queries.",
    },
    {
        "name": "Bookings & Registrations",
        "description": "Event registrations, ticket issuance, seat quota tracking, and QR validation.",
    },
    {
        "name": "Reviews & Feedback",
        "description": "Event ratings, feedback submissions, and student reviews.",
    },
    {
        "name": "Notifications",
        "description": "User notifications, system alerts, and status changes.",
    },
    {
        "name": "Admin & Metrics",
        "description": "Platform aggregate statistics, occupancy rates, and analytics.",
    },
]

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database on startup
    backend_module.init_db()
    yield

fastapi_app = FastAPI(
    title="Events Booking API",
    description="""
## Smart Events Booking Platform API
**Powered by FastAPI (ASGI Engine) + Flask Web Portal (WSGI Engine)**

### Features:
- 🚀 **Native Async REST API**: High-throughput endpoints for mobile, frontend, and external clients.
- ⚡ **Interactive Swagger & ReDoc Docs**: Complete OpenAPI 3.1.0 specifications with live request testing.
- 🎟️ **Event Ticketing & QR Pass Verification**: Instant ticket validation and gate check-in.
- 📊 **Real-Time Analytics & Quota Tracking**: Dynamic seat tracking with 2-hour cutoff rule.
- 🔐 **Dual Auth**: Secure login via 4-digit unique User ID (e.g. `0001`) or verified Email.
    """,
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=tags_metadata,
    lifespan=lifespan,
    contact={
        "name": "Events Organizing Team",
        "email": "venu.rachakondaa@gmail.com",
    },
    license_info={
        "name": "MIT License",
    }
)

# Enable CORS for frontend clients / cross-origin API consumers
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create API router under /api/v1
api_v1 = APIRouter(prefix="/api/v1")


# ============================================================================
# 1. HEALTH & SYSTEM DIAGNOSTICS ENDPOINTS
# ============================================================================

@api_v1.get(
    "/health",
    response_model=SystemHealthResponse,
    tags=["Health & Diagnostics"],
    summary="Health check & server diagnostics",
    description="Returns current server status, database connectivity, and total entity counts."
)
async def get_system_health():
    try:
        conn = get_db(timeout=5.0)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM events")
        events_cnt = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM users")
        users_cnt = c.fetchone()[0]
        conn.close()
        db_ok = True
    except Exception as e:
        db_ok = False
        events_cnt = 0
        users_cnt = 0

    return SystemHealthResponse(
        status="healthy" if db_ok else "degraded",
        version="2.0.0",
        framework="FastAPI + Flask Hybrid Engine",
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        database_connected=db_ok,
        events_count=events_cnt,
        users_count=users_cnt
    )


@api_v1.get(
    "/metrics",
    response_model=SystemMetricsResponse,
    tags=["Admin & Metrics"],
    summary="Platform analytics & metrics",
    description="Aggregate counts of events, registrations, check-ins, and seat occupancy."
)
async def get_system_metrics():
    conn = get_db(timeout=5.0)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM events")
    total_events = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM registrations WHERE status='active' OR status IS NULL")
    total_regs = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM registrations WHERE checked_in=1")
    total_checked_in = c.fetchone()[0]
    
    c.execute("SELECT SUM(seats_total), SUM(seats_filled) FROM events")
    seat_row = c.fetchone()
    total_seats = seat_row[0] or 1
    filled_seats = seat_row[1] or 0
    occupancy_pct = round((filled_seats / total_seats) * 100, 2)
    conn.close()

    events = get_events_cached()
    categories = sorted(list(set(get_category(e.get('title', '')) for e in events)))

    return SystemMetricsResponse(
        total_events=total_events,
        total_users=total_users,
        total_registrations=total_regs,
        total_checked_in=total_checked_in,
        overall_occupancy_rate_percent=occupancy_pct,
        active_categories=categories
    )


# ============================================================================
# 2. EVENTS CATALOG ENDPOINTS
# ============================================================================

@api_v1.get(
    "/categories",
    response_model=List[str],
    tags=["Events"],
    summary="List all event categories"
)
async def get_categories():
    events = get_events_cached()
    categories = sorted(list(set(get_category(e.get('title', '')) for e in events)))
    return categories


@api_v1.get(
    "/events",
    response_model=EventListResponse,
    tags=["Events"],
    summary="List and filter events catalog",
    description="Retrieve all events with search, category filtering, featured filter, and pagination."
)
async def list_events(
    search: Optional[str] = Query(default=None, description="Keyword search across title, description, and venue"),
    category: Optional[str] = Query(default=None, description="Filter by event category"),
    featured: Optional[bool] = Query(default=None, description="Filter only featured events"),
    upcoming_only: Optional[bool] = Query(default=False, description="Filter only open upcoming events"),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=50, ge=1, le=100, description="Items per page")
):
    raw_events = get_events_cached()
    all_categories = sorted(list(set(get_category(e.get('title', '')) for e in raw_events)))
    filtered = []

    for e in raw_events:
        cat = get_category(e.get('title', ''))
        e_dict = dict(e)
        e_dict['category'] = cat
        timing = get_event_status_info(e_dict)
        e_dict['status_label'] = timing.get('status_label', 'Registration Open')
        e_dict['status_badge'] = timing.get('status_badge', 'open')
        e_dict['is_sold_out'] = timing.get('is_sold_out', False)
        
        seats_tot = e_dict.get('seats_total') or 100
        seats_fil = e_dict.get('seats_filled') or 0
        e_dict['seats_available'] = max(0, seats_tot - seats_fil)

        # Filters
        if category and category.lower() != 'all' and cat.lower() != category.lower():
            continue
        if featured is not None and bool(e_dict.get('featured', 0)) != featured:
            continue
        if upcoming_only and (timing.get('is_expired') or not timing.get('is_open')):
            continue
        if search:
            q = search.lower()
            t = str(e_dict.get('title', '')).lower()
            d = str(e_dict.get('desc', '')).lower()
            v = str(e_dict.get('venue', '')).lower()
            p = str(e_dict.get('purpose', '')).lower()
            if q not in t and q not in d and q not in v and q not in p:
                continue

        filtered.append(e_dict)

    total_count = len(filtered)
    start_idx = (page - 1) * limit
    paged_events = filtered[start_idx:start_idx + limit]

    return EventListResponse(
        total=total_count,
        count=len(paged_events),
        page=page,
        limit=limit,
        categories=all_categories,
        events=paged_events
    )


@api_v1.get(
    "/events/{event_id}",
    response_model=EventResponse,
    tags=["Events"],
    summary="Get single event details"
)
async def get_single_event(
    event_id: int = Path(..., description="The unique ID of the event")
):
    ev = backend_module.get_event(event_id)
    if not ev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Event with ID {event_id} not found")
    
    ev_dict = dict(ev)
    ev_dict['category'] = get_category(ev_dict.get('title', ''))
    timing = get_event_status_info(ev_dict)
    ev_dict['status_label'] = timing.get('status_label', 'Registration Open')
    ev_dict['status_badge'] = timing.get('status_badge', 'open')
    ev_dict['is_sold_out'] = timing.get('is_sold_out', False)
    
    seats_tot = ev_dict.get('seats_total') or 100
    seats_fil = ev_dict.get('seats_filled') or 0
    ev_dict['seats_available'] = max(0, seats_tot - seats_fil)
    
    return ev_dict


@api_v1.post(
    "/events",
    response_model=StandardApiResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Events"],
    summary="Create a new event"
)
async def create_event(payload: EventCreateRequest):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        INSERT INTO events (
            title, date, time, end_time, desc, price, color, image,
            purpose, full_details, outcome, venue, venue_address,
            seats_total, seats_filled, featured
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
    """, (
        payload.title, payload.date, payload.time, payload.end_time,
        payload.desc, payload.price, payload.color, payload.image,
        payload.purpose or "", payload.full_details or "", payload.outcome or "",
        payload.venue, payload.venue_address, payload.seats_total, payload.featured
    ))
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    invalidate_events_cache()

    return StandardApiResponse(
        success=True,
        message=f"Event '{payload.title}' successfully created with ID {new_id}",
        data={"event_id": new_id}
    )


@api_v1.delete(
    "/events/{event_id}",
    response_model=StandardApiResponse,
    tags=["Events"],
    summary="Delete an event"
)
async def delete_event(event_id: int = Path(...)):
    ev = backend_module.get_event(event_id)
    if not ev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Event with ID {event_id} not found")
    
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM events WHERE id=?", (event_id,))
    c.execute("DELETE FROM registrations WHERE event_id=?", (event_id,))
    c.execute("DELETE FROM reviews WHERE event_id=?", (event_id,))
    conn.commit()
    conn.close()
    invalidate_events_cache()

    return StandardApiResponse(
        success=True,
        message=f"Event ID {event_id} and associated records successfully removed",
        data={"event_id": event_id}
    )


# ============================================================================
# 3. AUTHENTICATION & USER MANAGEMENT ENDPOINTS
# ============================================================================

@api_v1.post(
    "/auth/login",
    response_model=StandardApiResponse,
    tags=["Authentication & Users"],
    summary="User Login (User ID or Email)",
    description="Authenticates users by either their 4-digit User ID (e.g., '0001') or registered Email address."
)
async def api_login(payload: UserLoginRequest):
    identifier = payload.identifier.strip().lower()
    raw_password = payload.password

    conn = get_db(row_factory=True)
    c = conn.cursor()
    # Support UID-0001, 0001, email, and username formats
    uid_variations = [
        identifier,
        f"uid-{identifier}",
        identifier.replace("uid-", ""),
        f"{identifier.zfill(4)}" if identifier.isdigit() else identifier,
        f"uid-{identifier.zfill(4)}" if identifier.isdigit() else identifier,
    ]
    
    placeholders = ",".join(["?"] * len(uid_variations))
    c.execute(f"""
        SELECT * FROM users 
        WHERE LOWER(user_id) IN ({placeholders}) 
           OR LOWER(email) = ? 
           OR LOWER(username) = ?
    """, (*[v.lower() for v in uid_variations], identifier, identifier))
    user_row = c.fetchone()
    conn.close()

    if not user_row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials. Please enter your 4-digit User ID (e.g. 0001) or Email address."
        )

    user_dict = dict(user_row)
    hashed_pwd = user_dict.get('password', '')

    if not check_password_cached(hashed_pwd, raw_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password. Please verify and try again."
        )

    # Sanitize password from returned user object
    user_dict.pop('password', None)

    return StandardApiResponse(
        success=True,
        message="Authentication successful",
        data={
            "user": user_dict,
            "session_token": f"sess_{user_dict.get('id')}_{int(datetime.now().timestamp())}"
        }
    )


@api_v1.post(
    "/auth/register",
    response_model=StandardApiResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Authentication & Users"],
    summary="Register a new user account"
)
async def api_register(payload: UserRegisterRequest):
    conn = get_db(row_factory=True)
    c = conn.cursor()

    # Check for existing email or username
    c.execute("SELECT id FROM users WHERE LOWER(username) = ?", (payload.username.lower(),))
    if c.fetchone():
        conn.close()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username is already taken")

    c.execute("SELECT id FROM users WHERE LOWER(email) = ?", (payload.email.lower(),))
    if c.fetchone():
        conn.close()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="An account with this email already exists")

    # Generate sequential 4-digit User ID
    c.execute("SELECT MAX(id) FROM users")
    max_id_row = c.fetchone()
    next_num = (max_id_row[0] or 0) + 1
    new_user_id = f"{next_num:04d}"

    hashed_pwd = bcrypt.generate_password_hash(payload.password).decode('utf-8')
    created_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    c.execute("""
        INSERT INTO users (
            username, full_name, email, password, phone, college_id,
            user_id, role, is_admin, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'user', 0, ?)
    """, (
        payload.username.strip(), payload.full_name.strip(), payload.email.strip().lower(),
        hashed_pwd, payload.phone or "", payload.college_id or "",
        new_user_id, created_str
    ))
    new_db_id = c.lastrowid
    conn.commit()
    conn.close()

    return StandardApiResponse(
        success=True,
        message="Account created successfully! You can log in using your User ID or Email.",
        data={
            "id": new_db_id,
            "user_id": new_user_id,
            "username": payload.username,
            "email": payload.email,
            "full_name": payload.full_name
        }
    )


@api_v1.get(
    "/auth/profile/{identifier}",
    response_model=UserProfileResponse,
    tags=["Authentication & Users"],
    summary="Get user profile by User ID, Email, or Username"
)
async def get_user_profile(identifier: str = Path(...)):
    clean_id = identifier.strip().lower()
    conn = get_db(row_factory=True)
    c = conn.cursor()
    c.execute("""
        SELECT * FROM users 
        WHERE LOWER(user_id)=? OR LOWER(email)=? OR LOWER(username)=?
    """, (clean_id, clean_id, clean_id))
    user_row = c.fetchone()

    if not user_row:
        conn.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user_dict = dict(user_row)
    user_dict.pop('password', None)
    username = user_dict.get('username')

    c.execute("SELECT COUNT(*) FROM registrations WHERE username=? AND (status='active' OR status IS NULL)", (username,))
    active_regs_cnt = c.fetchone()[0]

    c.execute("""
        SELECT COUNT(*) FROM registrations r 
        JOIN events e ON r.event_id=e.id 
        WHERE r.username=? AND (r.status='active' OR r.status IS NULL)
    """, (username,))
    upcoming_cnt = c.fetchone()[0]

    conn.close()

    return UserProfileResponse(
        user=user_dict,
        registered_events_count=active_regs_cnt,
        upcoming_events_count=upcoming_cnt
    )


# ============================================================================
# 4. BOOKINGS & REGISTRATIONS ENDPOINTS
# ============================================================================

@api_v1.post(
    "/registrations/book",
    response_model=StandardApiResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Bookings & Registrations"],
    summary="Register for an event & issue ticket",
    description="Checks event quota, duplicates, 2-hour cutoff rule, updates seats_filled, and issues a verified ticket code."
)
async def book_event_ticket(payload: BookingCreateRequest):
    ev = backend_module.get_event(payload.event_id)
    if not ev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    timing = get_event_status_info(ev)
    if timing.get('is_expired') or not timing.get('is_open'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=timing.get('status_reason') or "Event registration is closed."
        )

    conn = get_db(row_factory=True)
    c = conn.cursor()

    # Check for existing active registration
    c.execute("""
        SELECT id FROM registrations 
        WHERE username = ? AND event_id = ? AND (status = 'active' OR status IS NULL)
    """, (payload.username, payload.event_id))
    existing = c.fetchone()
    if existing:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You are already registered for '{ev.get('title')}'."
        )

    # Calculate additional seats if team booking
    team_members_json = json.dumps(payload.team_members) if payload.team_members else "[]"
    team_count = 1 + len(payload.team_members or []) if payload.team_name else 1

    cur_filled = ev.get('seats_filled') or 0
    tot_seats = ev.get('seats_total') or 100
    if cur_filled + team_count > tot_seats:
        conn.close()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not enough seats available.")

    reg_time_str = datetime.now().strftime("%d %b %Y, %I:%M %p")
    c.execute("""
        INSERT INTO registrations (
            event_id, username, full_name, email, phone, college_id,
            payment_method, upi_id, team_name, team_members, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active')
    """, (
        payload.event_id, payload.username, payload.full_name, payload.email,
        payload.phone or "", payload.college_id or "", payload.payment_method or "Free Pass",
        payload.upi_id or "", payload.team_name or "", team_members_json
    ))
    new_reg_id = c.lastrowid
    ticket_code = f"TKT-{payload.event_id:03d}-{new_reg_id:05d}"
    c.execute("UPDATE registrations SET ticket_code=? WHERE id=?", (ticket_code, new_reg_id))

    # Update seats filled in events
    c.execute("UPDATE events SET seats_filled = seats_filled + ? WHERE id = ?", (team_count, payload.event_id))

    # Add notification for user
    c.execute("""
        INSERT INTO notifications (username, message, link)
        VALUES (?, ?, ?)
    """, (
        payload.username,
        f"Registration confirmed for '{ev.get('title')}'. Ticket Code: {ticket_code}",
        f"/download_ticket/{payload.event_id}"
    ))

    conn.commit()
    conn.close()
    invalidate_events_cache()
    backend_module.invalidate_user_regs(payload.username)

    return StandardApiResponse(
        success=True,
        message=f"Registration confirmed for '{ev.get('title')}'! Ticket #{ticket_code} generated.",
        data={
            "registration_id": new_reg_id,
            "ticket_code": ticket_code,
            "event_title": ev.get('title'),
            "seats_booked": team_count
        }
    )


@api_v1.get(
    "/registrations/user/{username}",
    response_model=List[BookingResponse],
    tags=["Bookings & Registrations"],
    summary="Get all registrations for a user"
)
async def get_user_registrations(username: str = Path(...)):
    conn = get_db(row_factory=True)
    c = conn.cursor()
    c.execute("""
        SELECT r.id, r.event_id, e.title as event_title, r.username, r.full_name, r.email,
               r.payment_method, r.status, r.team_name, r.checked_in, r.ticket_code,
               r.timestamp as reg_time
        FROM registrations r
        JOIN events e ON r.event_id = e.id
        WHERE r.username = ?
        ORDER BY r.id DESC
    """, (username,))
    rows = c.fetchall()
    conn.close()

    results = []
    for row in rows:
        r_dict = dict(row)
        if not r_dict.get('ticket_code'):
            r_dict['ticket_code'] = f"TKT-{r_dict.get('event_id'):03d}-{r_dict.get('id'):05d}"
        results.append(r_dict)

    return results


@api_v1.get(
    "/registrations/verify/{ticket_code}",
    response_model=TicketVerificationResponse,
    tags=["Bookings & Registrations"],
    summary="Verify QR Pass / Ticket Code",
    description="Decodes and validates ticket code for gate security and check-in kiosks."
)
async def verify_ticket(ticket_code: str = Path(...)):
    clean_code = ticket_code.strip().upper()
    conn = get_db(row_factory=True)
    c = conn.cursor()
    c.execute("""
        SELECT r.*, e.title as event_title
        FROM registrations r
        JOIN events e ON r.event_id = e.id
        WHERE UPPER(r.ticket_code) = ? OR UPPER(r.ticket_code) LIKE ?
    """, (clean_code, f"%{clean_code}%"))
    reg = c.fetchone()
    
    # Fallback search by ID if formatted like TKT-001-00042
    if not reg and clean_code.startswith("TKT-"):
        parts = clean_code.split('-')
        if len(parts) >= 3:
            try:
                ev_id = int(parts[1])
                reg_id = int(parts[2])
                c.execute("""
                    SELECT r.*, e.title as event_title
                    FROM registrations r
                    JOIN events e ON r.event_id = e.id
                    WHERE r.id = ? AND r.event_id = ?
                """, (reg_id, ev_id))
                reg = c.fetchone()
            except Exception:
                pass

    conn.close()

    if not reg:
        return TicketVerificationResponse(
            valid=False,
            ticket_code=clean_code,
            status="not_found",
            message="Invalid or unrecognized ticket pass. Entry Denied."
        )

    reg_dict = dict(reg)
    status_val = reg_dict.get('status') or 'active'

    if status_val == 'cancelled':
        return TicketVerificationResponse(
            valid=False,
            ticket_code=clean_code,
            status="revoked",
            event_id=reg_dict.get('event_id'),
            event_title=reg_dict.get('event_title'),
            attendee_name=reg_dict.get('full_name'),
            message="This ticket pass was REVOKED/CANCELLED. Entry Denied."
        )

    return TicketVerificationResponse(
        valid=True,
        ticket_code=clean_code,
        status="confirmed",
        event_id=reg_dict.get('event_id'),
        event_title=reg_dict.get('event_title'),
        attendee_name=reg_dict.get('full_name'),
        username=reg_dict.get('username'),
        college_id=reg_dict.get('college_id'),
        team_name=reg_dict.get('team_name'),
        checked_in=bool(reg_dict.get('checked_in', 0)),
        checkin_time=reg_dict.get('checkin_time'),
        message="Official Verified Admission Pass. Admission Approved."
    )


@api_v1.post(
    "/registrations/checkin/{ticket_code}",
    response_model=StandardApiResponse,
    tags=["Bookings & Registrations"],
    summary="Check in attendee at gate scanner"
)
async def checkin_ticket(ticket_code: str = Path(...)):
    clean_code = ticket_code.strip().upper()
    conn = get_db(row_factory=True)
    c = conn.cursor()
    c.execute("""
        SELECT r.id, r.event_id, r.checked_in, r.full_name, e.title as event_title
        FROM registrations r
        JOIN events e ON r.event_id = e.id
        WHERE UPPER(r.ticket_code) = ? OR UPPER(r.ticket_code) LIKE ?
    """, (clean_code, f"%{clean_code}%"))
    reg = c.fetchone()

    if not reg:
        conn.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    reg_dict = dict(reg)
    if reg_dict.get('checked_in'):
        conn.close()
        return StandardApiResponse(
            success=True,
            message=f"Attendee '{reg_dict.get('full_name')}' was already checked in.",
            data={"already_checked_in": True}
        )

    now_str = datetime.now().strftime("%d %b %Y, %I:%M %p")
    c.execute("UPDATE registrations SET checked_in = 1, checkin_time = ? WHERE id = ?", (now_str, reg_dict.get('id')))
    conn.commit()
    conn.close()
    backend_module.invalidate_checkins_cache()

    return StandardApiResponse(
        success=True,
        message=f"Check-in verified for {reg_dict.get('full_name')} at {now_str}!",
        data={
            "checked_in": True,
            "checkin_time": now_str,
            "attendee_name": reg_dict.get('full_name'),
            "event_title": reg_dict.get('event_title')
        }
    )


# ============================================================================
# 5. REVIEWS & FEEDBACK ENDPOINTS
# ============================================================================

@api_v1.get(
    "/reviews/{event_id}",
    response_model=List[ReviewResponse],
    tags=["Reviews & Feedback"],
    summary="Get all reviews for an event"
)
async def get_event_reviews(event_id: int = Path(...)):
    conn = get_db(row_factory=True)
    c = conn.cursor()
    c.execute("""
        SELECT id, event_id, username, rating, comment, timestamp as created_at
        FROM reviews
        WHERE event_id = ?
        ORDER BY id DESC
    """, (event_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


@api_v1.post(
    "/reviews",
    response_model=StandardApiResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Reviews & Feedback"],
    summary="Submit a review and star rating"
)
async def create_event_review(payload: ReviewCreateRequest):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        INSERT INTO reviews (event_id, username, rating, comment)
        VALUES (?, ?, ?, ?)
    """, (payload.event_id, payload.username, payload.rating, payload.comment or ""))
    new_id = c.lastrowid
    conn.commit()
    conn.close()

    return StandardApiResponse(
        success=True,
        message="Thank you for your review and rating!",
        data={"review_id": new_id}
    )


# ============================================================================
# 6. NOTIFICATIONS ENDPOINTS
# ============================================================================

@api_v1.get(
    "/notifications/{username}",
    response_model=List[NotificationResponse],
    tags=["Notifications"],
    summary="Get notifications for a user"
)
async def get_user_notifications(username: str = Path(...)):
    conn = get_db(row_factory=True)
    c = conn.cursor()
    c.execute("""
        SELECT id, username, message, link, is_read, created_at
        FROM notifications
        WHERE username = ?
        ORDER BY id DESC LIMIT 50
    """, (username,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


@api_v1.patch(
    "/notifications/{notification_id}/read",
    response_model=StandardApiResponse,
    tags=["Notifications"],
    summary="Mark notification as read"
)
async def mark_notification_read(notification_id: int = Path(...)):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE notifications SET is_read = 1 WHERE id = ?", (notification_id,))
    conn.commit()
    conn.close()
    return StandardApiResponse(success=True, message="Notification marked as read")


# ============================================================================
# MOUNT ROUTERS AND FLASK WSGI APPLICATION
# ============================================================================

# Include API v1 Router in FastAPI app
fastapi_app.include_router(api_v1)

# Seamlessly mount the Flask WSGI application for all server-rendered HTML views
# (FastAPI matches /docs, /redoc, /openapi.json, and /api/v1/* first,
# and transparently falls back to Flask for all web pages and static assets)
fastapi_app.mount("/", WSGIMiddleware(flask_app, workers=256))
