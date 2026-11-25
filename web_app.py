"""RideSync Flask application factory, server-side session rotation, and startup."""

import os
import secrets
import time
from threading import Lock

from flask import Flask, abort, g, redirect, request, url_for
from flask.sessions import SessionInterface, SessionMixin
from werkzeug.datastructures import CallbackDict

from database import ensure_database_ready


class ServerSideSession(CallbackDict, SessionMixin):
    """Server-backed session dict that tracks modification and rotation state."""

    def __init__(self, initial=None, sid=None, new=False):
        def on_update(_self):
            _self.modified = True

        super().__init__(initial or {}, on_update)
        self.sid = sid
        self.new = new
        self.modified = False
        self.rotated = False


class InMemoryServerSessionInterface(SessionInterface):
    """Server-side session store with explicit session ID rotation to prevent fixation."""

    def __init__(self, ttl_seconds=7200):
        self._store = {}
        self._lock = Lock()
        self._ttl = ttl_seconds

    def _generate_sid(self):
        return secrets.token_urlsafe(32)

    def _cleanup_expired(self, now):
        expired = [k for k, v in self._store.items() if v["expires_at"] <= now]
        for key in expired:
            del self._store[key]

    def open_session(self, app, req):
        cookie_name = app.config.get("SESSION_COOKIE_NAME", "ridesync_sid")
        sid = req.cookies.get(cookie_name)
        now = time.time()

        with self._lock:
            self._cleanup_expired(now)
            if sid and sid in self._store:
                entry = self._store[sid]
                if entry["expires_at"] > now:
                    entry["expires_at"] = now + self._ttl
                    return ServerSideSession(dict(entry["data"]), sid=sid, new=False)

        new_sid = self._generate_sid()
        return ServerSideSession({}, sid=new_sid, new=True)

    def rotate_session(self, sess):
        """Invalidate the old session ID and assign a fresh cryptographically random ID."""
        old_sid = getattr(sess, "sid", None)
        with self._lock:
            if old_sid and old_sid in self._store:
                del self._store[old_sid]
        sess.clear()
        sess.sid = self._generate_sid()
        sess.modified = True
        sess.rotated = True

    def destroy_session(self, sess):
        """Remove session data from the server store and rotate to an empty session."""
        self.rotate_session(sess)

    def save_session(self, app, sess, response):
        cookie_name = app.config.get("SESSION_COOKIE_NAME", "ridesync_sid")
        domain = self.get_cookie_domain(app)
        path = self.get_cookie_path(app)

        if not sess:
            with self._lock:
                if sess.sid in self._store:
                    del self._store[sess.sid]
            if sess.modified:
                response.delete_cookie(cookie_name, domain=domain, path=path)
            return

        if not sess.modified and not sess.new:
            return

        now = time.time()
        with self._lock:
            self._store[sess.sid] = {
                "data": dict(sess),
                "expires_at": now + self._ttl,
            }

        httponly = self.get_cookie_httponly(app)
        secure = self.get_cookie_secure(app)
        samesite = self.get_cookie_samesite(app)
        expires = self.get_expiration_time(app, sess)

        response.set_cookie(
            cookie_name,
            sess.sid,
            expires=expires,
            httponly=httponly,
            domain=domain,
            path=path,
            secure=secure,
            samesite=samesite,
        )


def rotate_user_session(sess):
    """Helper called on login/logout to rotate the server-side session ID and CSRF token."""
    from flask import current_app

    interface = current_app.session_interface
    if hasattr(interface, "rotate_session"):
        interface.rotate_session(sess)
    else:
        sess.clear()
    sess["_csrf_token"] = secrets.token_urlsafe(32)


def get_csrf_token():
    """Return the per-session CSRF token, creating one if missing."""
    from flask import session

    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token


def create_app():
    """Create and configure the Flask application."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    app = Flask(
        __name__,
        template_folder=os.path.join(base_dir, "templates"),
        static_folder=os.path.join(base_dir, "static"),
    )

    app.config["SECRET_KEY"] = os.environ.get("RIDESYNC_SECRET_KEY") or secrets.token_hex(32)
    app.config["SESSION_COOKIE_NAME"] = "ridesync_sid"
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = os.environ.get("RIDESYNC_HTTPS", "0") == "1"
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 3600
    app.jinja_env.auto_reload = False

    app.session_interface = InMemoryServerSessionInterface(ttl_seconds=7200)

    @app.before_request
    def _verify_csrf_and_load_context():
        from flask import session

        if request.method == "POST":
            session_token = session.get("_csrf_token")
            submitted_token = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
            if not session_token or not submitted_token or not secrets.compare_digest(session_token, submitted_token):
                abort(403, description="Invalid or missing CSRF token.")

        g.user_id = session.get("user_id")
        g.user_name = session.get("user_name")
        g.admin_id = session.get("admin_id")
        g.admin_name = session.get("admin_name")

    @app.context_processor
    def _inject_template_globals():
        return {
            "csrf_token": get_csrf_token,
            "current_user_id": g.get("user_id"),
            "current_user_name": g.get("user_name"),
            "current_admin_id": g.get("admin_id"),
            "current_admin_name": g.get("admin_name"),
        }

    @app.errorhandler(403)
    def _forbidden(err):
        from flask import flash, render_template

        return render_template("error.html", code=403, title="Access Denied", message=str(err.description or "You are not authorized to perform this action.")), 403

    @app.errorhandler(404)
    def _not_found(_err):
        from flask import render_template

        return render_template("error.html", code=404, title="Page Not Found", message="The requested RideSync page could not be found."), 404

    @app.errorhandler(500)
    def _server_error(_err):
        from flask import render_template

        return render_template("error.html", code=500, title="Server Error", message="An unexpected server error occurred. Please try again."), 500

    from web_routes import register_routes

    register_routes(app)
    return app


def start_server():
    """Initialize database once in terminal, then start Flask without debug reloader."""
    print("\n" + "=" * 60)
    print("RIDESYNC WEB SERVER INITIALIZATION".center(60))
    print("=" * 60)

    if not ensure_database_ready():
        print("\n✗ Database initialization failed. Web server cannot start.")
        raise SystemExit(1)

    app = create_app()
    host = os.environ.get("RIDESYNC_HOST", "127.0.0.1")
    port = int(os.environ.get("RIDESYNC_PORT", "5000"))

    print(f"\n✓ RideSync Web Server running at http://{host}:{port}")
    print("➜ Press CTRL+C to stop the server.\n")

    app.run(host=host, port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    start_server()
