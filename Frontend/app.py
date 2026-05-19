import os
from pathlib import Path

import requests
from flask import (
    Flask,
    Response,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)


BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
PROXY_TIMEOUT = float(os.getenv("BACKEND_TIMEOUT", "60"))
BASE_DIR = Path(__file__).resolve().parent

DASHBOARD_SCRIPTS = [
    "00_state_filters_nav.js",
    "01_auth.js",
    "02_api_data.js",
    "03_shell.js",
    "04_import_badges_export.js",
    "05_view_global.js",
    "06_view_individual.js",
    "07_view_departments.js",
    "08_view_ml_alerts_archives.js",
    "09_audit_about.js",
    "10_admin_core_departments.js",
    "11_admin_interns.js",
    "12_admin_accounts_password.js",
    "13_ui_boot.js",
]

app = Flask(__name__)
app.secret_key = os.getenv("FRONTEND_SECRET_KEY", "dev-change-me")

HOP_BY_HOP_HEADERS = {
    "connection",
    "content-encoding",
    "content-length",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}


def _backend_request(method, path, **kwargs):
    return requests.request(
        method=method,
        url=f"{BACKEND_URL}{path}",
        timeout=PROXY_TIMEOUT,
        allow_redirects=False,
        **kwargs,
    )


def _current_auth():
    return session.get("auth")


@app.get("/")
def index():
    if _current_auth():
        return redirect(url_for("dashboard"))
    return redirect(url_for("login_page"))


@app.get("/login")
def login_page():
    if _current_auth():
        return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.post("/login")
def login():
    credentials = request.get_json(silent=True) or request.form.to_dict()
    username = (credentials.get("username") or "").strip()
    password = credentials.get("password") or ""

    if not username or not password:
        return jsonify({"detail": "Identifiant et mot de passe requis"}), 400

    try:
        login_response = _backend_request(
            "POST",
            "/auth/login",
            json={"username": username, "password": password},
        )
    except requests.RequestException as exc:
        return jsonify({"detail": f"Backend indisponible: {exc}"}), 502

    try:
        payload = login_response.json()
    except ValueError:
        payload = {"detail": login_response.text or "Réponse backend invalide"}

    if not login_response.ok:
        return jsonify(payload), login_response.status_code

    session["auth"] = {
        "access_token": payload["access_token"],
        "role": payload.get("role"),
        "department_id": payload.get("department_id"),
        "username": username,
    }
    return jsonify({"redirect": url_for("dashboard")})


@app.post("/logout")
def logout():
    session.clear()
    return jsonify({"redirect": url_for("login_page")})


@app.get("/dashboard")
def dashboard():
    auth = _current_auth()
    if not auth:
        return redirect(url_for("login_page"))
    return render_template("dashboard.html", auth=auth, dashboard_scripts=DASHBOARD_SCRIPTS)


@app.get("/assets/dashboard/<path:filename>")
def dashboard_script(filename):
    if not _current_auth():
        return redirect(url_for("login_page"))
    if filename not in DASHBOARD_SCRIPTS:
        return Response("Not found", status=404)
    response = send_from_directory(
        BASE_DIR / "private" / "dashboard",
        filename,
        mimetype="text/javascript",
    )
    response.headers["Content-Type"] = "text/javascript; charset=utf-8"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/scanner")
def scanner():
    return render_template("scanner.html")


@app.route(
    "/<path:path>",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)
def proxy_backend(path):
    frontend_only_paths = {"login", "logout", "dashboard", "scanner"}
    if path in frontend_only_paths or path.startswith("static/"):
        return Response("Not found", status=404)

    target_url = f"{BACKEND_URL}/{path}"
    headers = {
        key: value
        for key, value in request.headers
        if key.lower() not in {"host", "content-length"}
    }
    auth = _current_auth()
    if auth and "authorization" not in {key.lower() for key in headers}:
        headers["Authorization"] = f"Bearer {auth['access_token']}"

    try:
        backend_response = _backend_request(
            method=request.method,
            path=f"/{path}",
            params=request.args,
            headers=headers,
            data=request.get_data(),
            cookies=request.cookies,
        )
    except requests.RequestException as exc:
        return Response(
            f'{{"detail":"Backend indisponible: {exc}"}}',
            status=502,
            mimetype="application/json",
        )

    response_headers = [
        (key, value)
        for key, value in backend_response.headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS
    ]
    return Response(
        backend_response.content,
        status=backend_response.status_code,
        headers=response_headers,
    )


if __name__ == "__main__":
    host = os.getenv("FRONTEND_HOST", "127.0.0.1")
    port = int(os.getenv("FRONTEND_PORT", "5000"))
    app.run(host=host, port=port, debug=True)
