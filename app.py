"""
Event Management System - Server Launcher
Allows running `python app.py` directly from the workspace root directory.
"""
import sys
import os

# Set working directory to backend folder for database and asset lookups
workspace_root = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(workspace_root, 'backend')
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

os.chdir(backend_dir)

# Import application from backend package
import backend.app as backend_module
app = backend_module.app
asgi_app = backend_module.asgi_app

if __name__ == '__main__':
    is_dev = '--dev' in sys.argv or os.environ.get('FLASK_ENV') == 'development' or os.environ.get('DEBUG') == '1'

    print("\n" + "=" * 75)
    print("  EVENTS MANAGEMENT SYSTEM - FASTAPI + FLASK HYBRID SERVER")
    print("=" * 75)
    print("  Local Access URL:    http://127.0.0.1:5000")
    print("  Interactive Swagger: http://127.0.0.1:5000/docs")
    print("  ReDoc Documentation: http://127.0.0.1:5000/redoc")
    print("  Default Admin Login: User ID: 0001 (or Email: admin@example.com)  |  Password: password123")
    print("  Engine:              " + ("Flask Dev Server (Debug Mode)" if is_dev else "FastAPI ASGI Server (Uvicorn / IOCP Event Loop)"))
    print("  To Stop Server:      Press CTRL + C in this terminal")
    print("=" * 75)
    print("  Server is actively listening for requests.\n")

    import socket

    def is_port_in_use(port, host='127.0.0.1'):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                return s.connect_ex((host, port)) == 0
        except Exception:
            return False

    if is_port_in_use(5000):
        print("\n" + "=" * 75)
        print("  NOTICE: EVENTS Management System is ALREADY RUNNING on Port 5000!")
        print("=" * 75)
        print("  Local Access URL:    http://127.0.0.1:5000")
        print("  Interactive Swagger: http://127.0.0.1:5000/docs")
        print("  ReDoc Documentation: http://127.0.0.1:5000/redoc")
        print("  Default Admin Login: User ID: 0001 (or Email: admin@example.com)  |  Password: password123")
        print("  Status:              Server is already live and accepting requests.")
        print("=" * 75 + "\n")
        sys.exit(0)

    if is_dev:
        app.run(debug=True, threaded=True, host='127.0.0.1', port=5000)
    else:
        started = False
        try:
            import uvicorn
            uvicorn.run(
                asgi_app,
                host='127.0.0.1',
                port=5000,
                log_level='warning',
                access_log=False,
                limit_concurrency=2500,
                backlog=4096,
                timeout_keep_alive=30,
            )
            started = True
        except (Exception, SystemExit, KeyboardInterrupt) as e:
            if isinstance(e, KeyboardInterrupt):
                raise
            print(f"Uvicorn note: {e}")

        if not started:
            try:
                from waitress import serve
                serve(
                    app,
                    host='127.0.0.1',
                    port=5000,
                    threads=64,
                    connection_limit=500,
                    channel_timeout=60,
                    backlog=500,
                )
                started = True
            except (Exception, SystemExit, KeyboardInterrupt) as e:
                if isinstance(e, KeyboardInterrupt):
                    raise
                print(f"Waitress fallback note: {e}")

        if not started:
            app.run(debug=False, threaded=True, host='127.0.0.1', port=5000)
