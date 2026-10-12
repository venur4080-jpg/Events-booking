# Events Booking - Hosting & Deployment Guide

This guide covers the 3 primary ways to host and deploy Events Booking.

---

## 1. Instant Public Hosting via Cloudflare Tunnel (Zero-Setup)

Host directly from your computer with a live HTTPS public link:

### Option A: One-Click Launcher (Windows)
Double-click `start_public_hosting.bat`.

### Option B: Manual Command Line
```bash
# Terminal 1 - Start Backend Server
python app.py

# Terminal 2 - Start Cloudflare Public Tunnel
.\cloudflared.exe tunnel --url http://127.0.0.1:5000
```
*Your live public URL (e.g., `https://xxxx-xxxx.trycloudflare.com`) will be printed in Terminal 2.*

---

## 2. Cloud Deployment (Render / Railway / Heroku)

The project includes `Procfile`, `render.yaml`, and `requirements.txt`.

### Deploying to Render (Free Web Service)
1. Push this project repository to **GitHub**.
2. Go to [Render.com](https://render.com) and create a **New Web Service**.
3. Select your GitHub repository.
4. Set the following settings:
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app:asgi_app --host 0.0.0.0 --port $PORT --workers 4`
5. Click **Deploy**.

---

## 3. Docker Deployment (Self-Hosted / AWS / DigitalOcean / VPS)

The project includes a production `Dockerfile` and `.dockerignore`.

### Build & Run Docker Container
```bash
# 1. Build Docker image
docker build -t events-booking .

# 2. Run container on port 5000
docker run -d -p 5000:5000 --name events-booking-app events-booking
```
*Access locally at `http://localhost:5000`.*

---

## Default Administrator Credentials
- **Username**: `admin`
- **Password**: `password123`
