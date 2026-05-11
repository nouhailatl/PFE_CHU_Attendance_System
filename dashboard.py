import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
from datetime import datetime, timedelta
from database import engine
from utils_stats import compute_attendance_metrics, identify_alerts
import os
from excel_export import export_to_excel

# ── CONFIG ────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CHU Analytics | Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

API_BASE = "http://127.0.0.1:8000"
COLOR_PRIMARY   = "#2563eb"
COLOR_SECONDARY = "#10b981"


# ── AUTH HELPERS ──────────────────────────────────────────────────────────────

def do_login(username: str, password: str) -> dict | None:
    """
    POST /auth/login  →  your exact endpoint in main.py.
    Returns {"access_token", "role", "department_id"} or None.
    """
    try:
        r = requests.post(
            f"{API_BASE}/auth/login",
            json={"username": username, "password": password},   # LoginRequest is JSON, not form
            timeout=5,
        )
        if r.status_code == 200:
            data = r.json()
            return {
                "access_token": data["access_token"],
                "role":         data["role"],           # "super_admin" | "supervisor"
                "department_id": data.get("department_id"),  # None for super_admin
                "username":     username,
            }
    except requests.RequestException:
        pass
    return None


def auth_headers() -> dict:
    """Inject the stored JWT as a Bearer token."""
    return {"Authorization": f"Bearer {st.session_state.auth['access_token']}"}


def is_logged_in() -> bool:
    return st.session_state.get("auth") is not None


def is_super_admin() -> bool:
    return is_logged_in() and st.session_state.auth["role"] == "super_admin"


def get_dept_filter() -> str | None:
    """
    Returns None  → super_admin sees everything.
    Returns a UUID → supervisor sees only their department.
    """
    if is_super_admin():
        return None
    return st.session_state.auth.get("department_id")


def logout():
    st.session_state.pop("auth", None)
    st.rerun()


# ── PROTECTED API CALLS ───────────────────────────────────────────────────────

def api_mark_absences() -> dict:
    r = requests.post(f"{API_BASE}/admin/mark-absences", headers=auth_headers(), timeout=10)
    r.raise_for_status()
    return r.json()


def api_delete_intern(intern_id: str) -> dict:
    """Only callable by super_admin — FastAPI enforces require_super_admin."""
    r = requests.delete(f"{API_BASE}/interns/{intern_id}", headers=auth_headers(), timeout=5)
    r.raise_for_status()
    return r.json()


# ── DATA LOADING ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=60)
def load_all_data():
    df_int    = pd.read_sql("""
        SELECT i.id, i.first_name, i.last_name, d.name AS department, i.department_id
        FROM interns i
        LEFT JOIN departments d ON i.department_id = d.id
    """, engine)
    df_att    = pd.read_sql("SELECT * FROM attendance_events", engine)
    df_daily  = pd.read_sql("SELECT * FROM daily_status", engine)
    df_depts  = pd.read_sql("SELECT * FROM departments", engine)

    if not df_int.empty:
        df_int["name"] = df_int["first_name"] + " " + df_int["last_name"]
    if not df_att.empty:
        df_att["timestamp"] = pd.to_datetime(df_att["timestamp"])
    if not df_daily.empty:
        for col in ["date", "arrival_time", "departure_time"]:
            df_daily[col] = pd.to_datetime(df_daily[col])

    return df_att, df_int, df_depts, df_daily


def filtered_data():
    """
    Apply department filter for supervisors.
    Super admins get all rows; supervisors get only their department.
    """
    df_att, df_int, df_depts, df_daily = load_all_data()
    dept_id = get_dept_filter()

    if dept_id:
        df_int   = df_int[df_int["department_id"] == dept_id]
        intern_ids = set(df_int["id"])
        df_att   = df_att[df_att["intern_id"].isin(intern_ids)]
        df_daily = df_daily[df_daily["intern_id"].isin(intern_ids)]
        df_depts = df_depts[df_depts["id"] == dept_id]

    return df_att, df_int, df_depts, df_daily


# ── CHART THEME ───────────────────────────────────────────────────────────────

def theme(fig):
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="gray",
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


# ── CSS ───────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
[data-testid="stMetricValue"]  { font-size:1.8rem !important; font-weight:700 !important; }
[data-testid="stMetricLabel"]  { text-transform:uppercase; letter-spacing:.05em; opacity:.8; }
[data-testid="stSidebar"]      { border-right:1px solid rgba(128,128,128,.1); }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  LOGIN PAGE
# ══════════════════════════════════════════════════════════════════════════════

def render_login():
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown("""
            <div style="text-align:center;margin-bottom:24px">
                <div style="display:inline-block;background:rgba(37,99,235,.12);
                     border:1px solid rgba(37,99,235,.3);border-radius:100px;
                     padding:6px 18px;margin-bottom:12px">
                    <span style="color:#2563eb;font-size:12px;
                          letter-spacing:.1em;text-transform:uppercase">
                        🔐 Espace Administration
                    </span>
                </div>
                <h2 style="margin:0">CHU Analytics</h2>
                <p style="color:gray;font-size:13px;margin-top:6px">
                    Connectez-vous pour accéder au tableau de bord
                </p>
            </div>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            username  = st.text_input("Identifiant", placeholder="admin")
            password  = st.text_input("Mot de passe", type="password")
            submitted = st.form_submit_button("Se connecter", use_container_width=True)

        if submitted:
            if not username or not password:
                st.error("Veuillez remplir tous les champs.")
            else:
                with st.spinner("Vérification…"):
                    result = do_login(username, password)
                if result:
                    st.session_state.auth = result
                    st.rerun()
                else:
                    st.error("❌ Identifiants incorrects ou serveur inaccessible.")

        # Warn if FastAPI is unreachable
        try:
            requests.get(f"{API_BASE}/docs", timeout=2)
        except requests.RequestException:
            st.warning("⚠️ FastAPI semble hors ligne — lancez `uvicorn main:app --reload`")


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

def render_dashboard():
    auth = st.session_state.auth

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        # User badge
        role_label = "⭐ Super Admin" if auth["role"] == "super_admin" else "👤 Superviseur"
        st.markdown(f"""
            <div style="background:rgba(37,99,235,.1);border:1px solid rgba(37,99,235,.25);
                 border-radius:10px;padding:12px 14px;margin-bottom:16px">
                <div style="font-size:13px;font-weight:600">{auth['username']}</div>
                <div style="font-size:11px;color:#2563eb;margin-top:3px">{role_label}</div>
            </div>
        """, unsafe_allow_html=True)

        st.title("CHU Analytics")
        st.markdown("---")

        # Supervisors only see their own data — hide Dept view (nothing to compare)
        pages = ["Vue Globale", "Vue Individuelle", "Journal des Alertes"]
        if is_super_admin():
            pages = ["Vue Globale", "Vue Individuelle",
                     "Vue Départementale", "Clusters & ML",
                     "Journal des Alertes", "⚙️ Administration"]

        menu = st.radio("Navigation", pages, index=0)
        st.markdown("---")

        if st.button("🚪 Se déconnecter", use_container_width=True):
            logout()

        st.caption("CHU Monitoring v2.1")

    # ── Load data (filtered by role) ──────────────────────────────────────────
    try:
        df_attendance, df_interns, df_departments, df_daily = filtered_data()
    except Exception as e:
        st.error(f"Erreur de connexion à la base de données : {e}")
        st.stop()

    # ══════════════════════════════════════════════════════════════════════════
    #  VUE GLOBALE
    # ══════════════════════════════════════════════════════════════════════════
    if menu == "Vue Globale":
        st.header("Surveillance des Flux")

        today     = datetime.utcnow().date()
        yesterday = today - timedelta(days=1)

        present_today     = df_attendance[df_attendance["timestamp"].dt.date == today]["intern_id"].nunique() if not df_attendance.empty else 0
        present_yesterday = df_attendance[df_attendance["timestamp"].dt.date == yesterday]["intern_id"].nunique() if not df_attendance.empty else 0
        delta = int(present_today - present_yesterday)

        m1, m2, m3 = st.columns(3)
        with m1: st.metric("Total Stagiaires",     len(df_interns))
        with m2: st.metric("Présences Aujourd'hui", present_today, delta=delta)
        with m3: st.metric("Services Opérationnels", len(df_departments))

        st.markdown("---")
        col_dl, _ = st.columns([1, 3])
        with col_dl:
            if st.button("📥 Exporter vers Excel", use_container_width=True):
                # Récupère le department_id depuis le token
                # None pour super_admin, UUID pour supervisor
                dept_id = st.session_state.auth.get("department_id")
                dept_label = ""
                if dept_id:
                    # Nom du département pour le nom du fichier
                    dept_label = "_" + (df_departments[df_departments["id"] == dept_id]["name"].values[0]
                                        if not df_departments.empty else dept_id[:8])

                with st.spinner("Génération du fichier Excel…"):
                    path = export_to_excel(department_id=dept_id)

                with open(path, "rb") as f:
                    st.download_button(
                        label="⬇️ Télécharger le rapport Excel",
                        data=f.read(),
                        file_name=f"CHU_Pointages{dept_label}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )

        col_l, col_r = st.columns(2)

        with col_l:
            with st.container(border=True):
                st.subheader("Évolution Temporelle des Scans")
                if not df_attendance.empty:
                    df_counts = df_attendance.groupby(df_attendance["timestamp"].dt.date).size().reset_index(name="scans")
                    fig = px.area(df_counts, x="timestamp", y="scans", color_discrete_sequence=[COLOR_PRIMARY])
                    st.plotly_chart(theme(fig), use_container_width=True)
                else:
                    st.info("Aucune donnée de scan disponible.")

        with col_r:
            with st.container(border=True):
                st.subheader("Concentration Horaire (Heatmap)")
                if not df_attendance.empty:
                    df_attendance["hour"] = df_attendance["timestamp"].dt.hour
                    df_attendance["day"]  = df_attendance["timestamp"].dt.day_name()
                    days_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
                    hm = df_attendance.groupby(["day","hour"]).size().unstack(fill_value=0)
                    hm = hm.reindex(days_order).fillna(0)
                    fig = px.imshow(hm, labels=dict(x="Heure", y="Jour", color="Scans"), color_continuous_scale="Blues")
                    st.plotly_chart(theme(fig), use_container_width=True)
                else:
                    st.info("Aucune donnée de scan disponible.")

    # ══════════════════════════════════════════════════════════════════════════
    #  VUE INDIVIDUELLE
    # ══════════════════════════════════════════════════════════════════════════
    elif menu == "Vue Individuelle":
        st.header("Analyse Profil 360°")

        if df_interns.empty:
            st.info("Aucun stagiaire trouvé.")
        else:
            selected = st.selectbox("Sélectionner un stagiaire", df_interns["name"].dropna().unique())
            intern_row = df_interns[df_interns["name"] == selected].iloc[0]
            intern_id  = intern_row["id"]

            col_a, col_b = st.columns([1, 2])

            with col_a:
                with st.container(border=True):
                    st.markdown(f"#### {intern_row['name']}")
                    st.markdown(f"**Département :** `{intern_row['department']}`")
                    st.divider()

                    # Pull daily stats for this intern
                    intern_daily = df_daily[df_daily["intern_id"] == intern_id]
                    total_days   = len(intern_daily)
                    present_days = len(intern_daily[intern_daily["status"] != "absent"])
                    rate = round(present_days / total_days * 100, 1) if total_days else 0
                    avg_dur = round(intern_daily["work_duration"].mean(), 2) if not intern_daily.empty else 0

                    st.metric("Taux de présence", f"{rate} %")
                    st.metric("Durée moy. / jour", f"{avg_dur} h")

                    # Risk gauge
                    risk = 100 - rate
                    fig_gauge = go.Figure(go.Indicator(
                        mode="gauge+number",
                        value=risk,
                        title={"text": "Score de risque"},
                        gauge={
                            "axis": {"range": [0, 100]},
                            "bar":  {"color": "#ef4444" if risk > 60 else "#f59e0b" if risk > 30 else "#10b981"},
                            "steps": [
                                {"range": [0,  30], "color": "rgba(16,185,129,.15)"},
                                {"range": [30, 60], "color": "rgba(245,158,11,.15)"},
                                {"range": [60,100], "color": "rgba(239,68,68,.15)"},
                            ],
                        },
                    ))
                    fig_gauge.update_layout(height=220, margin=dict(t=30, b=0, l=10, r=10),
                                            paper_bgcolor="rgba(0,0,0,0)", font_color="gray")
                    st.plotly_chart(fig_gauge, use_container_width=True)

            with col_b:
                with st.container(border=True):
                    st.subheader("Historique des 30 derniers jours")
                    if not intern_daily.empty:
                        display = intern_daily[["date","status","checkin_status","checkout_status","work_duration"]].copy()
                        display = display.sort_values("date", ascending=False).head(30)
                        display.columns = ["Date", "Statut", "Arrivée", "Départ", "Durée (h)"]
                        st.dataframe(display, use_container_width=True, height=400)
                    else:
                        st.info("Aucun historique disponible pour ce stagiaire.")

    # ══════════════════════════════════════════════════════════════════════════
    #  VUE DÉPARTEMENTALE  (super_admin only)
    # ══════════════════════════════════════════════════════════════════════════
    elif menu == "Vue Départementale":
        st.header("Pilotage des Services")

        col_c, col_d = st.columns(2)

        with col_c:
            with st.container(border=True):
                st.subheader("Répartition des Effectifs")
                dist = df_interns["department"].value_counts().reset_index()
                dist.columns = ["Service", "Effectif"]
                fig = px.pie(dist, values="Effectif", names="Service", hole=0.6)
                st.plotly_chart(theme(fig), use_container_width=True)

        with col_d:
            with st.container(border=True):
                st.subheader("Volume d'Activité par Service")
                if not df_attendance.empty:
                    merged = df_attendance.merge(df_interns, left_on="intern_id", right_on="id")
                    act = merged["department"].value_counts().reset_index()
                    act.columns = ["Service", "Total Scans"]
                    fig = px.bar(act, x="Service", y="Total Scans",
                                 color="Total Scans", color_continuous_scale="Blues")
                    st.plotly_chart(theme(fig), use_container_width=True)
                else:
                    st.info("Aucune donnée de scan disponible.")

        # Attendance rate per department
        with st.container(border=True):
            st.subheader("Taux de présence moyen par département")
            if not df_daily.empty and not df_interns.empty:
                merged_d = df_daily.merge(df_interns[["id","department"]], left_on="intern_id", right_on="id")
                dept_rate = merged_d.groupby("department").apply(
                    lambda g: round((g["status"] != "absent").sum() / len(g) * 100, 1)
                ).reset_index()
                dept_rate.columns = ["Département", "Taux (%)"]
                fig = px.bar(dept_rate, x="Département", y="Taux (%)",
                             color="Taux (%)", color_continuous_scale="Greens",
                             range_y=[0, 100])
                st.plotly_chart(theme(fig), use_container_width=True)

    # ══════════════════════════════════════════════════════════════════════════
    #  CLUSTERS & ML  (super_admin only)
    # ══════════════════════════════════════════════════════════════════════════
    elif menu == "Clusters & ML":
        st.header("Intelligence Comportementale")
        with st.container(border=True):
            st.subheader("Segmentation des Profils (K-Means)")
            mock = pd.DataFrame({
                "PCA1":    [1, 2, -1, 0, 5, 2, 3, -1],
                "PCA2":    [2, -1, 0, 3, -2, 1, 4, 0],
                "Segment": ["Régulier","Régulier","À Risque","Désengagé",
                             "Élite","Régulier","Élite","À Risque"],
                "Stagiaire": [f"Stagiaire {c}" for c in "ABCDEFGH"],
            })
            fig = px.scatter(mock, x="PCA1", y="PCA2", color="Segment",
                             hover_name="Stagiaire", size=[10]*8)
            st.plotly_chart(theme(fig), use_container_width=True)
            st.info("Projection PCA — les clusters seront alimentés par le pipeline ML (Semaine 5).")

    # ══════════════════════════════════════════════════════════════════════════
    #  JOURNAL DES ALERTES
    # ══════════════════════════════════════════════════════════════════════════
    elif menu == "Journal des Alertes":
        st.header("Centre de Gestion des Anomalies")

        # Attention flags from daily_status
        if not df_daily.empty:
            alerts_df = df_daily[df_daily["needs_attention"] == True].copy()
            if not alerts_df.empty:
                alerts_df = alerts_df.merge(
                    df_interns[["id","name","department"]],
                    left_on="intern_id", right_on="id", how="left"
                )
                display = alerts_df[["date","name","department","status","checkin_status","checkout_status"]].copy()
                display = display.sort_values("date", ascending=False)
                display.columns = ["Date","Stagiaire","Département","Statut","Check-in","Check-out"]
                st.warning(f"⚠️ {len(display)} événements nécessitant attention")
                st.dataframe(display, use_container_width=True, height=450)
            else:
                st.success("✅ Aucune anomalie détectée — tout est nominal.")
        else:
            st.info("Aucune donnée de pointage disponible.")

        # Super admin: manual absence trigger
        if is_super_admin():
            st.markdown("---")
            st.subheader("Actions administratives")
            if st.button("🔴 Marquer les absences du jour", type="primary"):
                with st.spinner("Traitement en cours…"):
                    try:
                        result = api_mark_absences()
                        st.success(result.get("message", "Opération réussie"))
                        st.cache_data.clear()
                    except requests.HTTPError as e:
                        st.error(f"Erreur {e.response.status_code}: {e.response.json().get('detail','')}")

    # ══════════════════════════════════════════════════════════════════════════
    #  ADMINISTRATION  (super_admin only)
    # ══════════════════════════════════════════════════════════════════════════
    elif menu == "⚙️ Administration":
        st.header("Administration")

        tab1, tab2 = st.tabs(["👥 Gérer les Stagiaires", "🔑 Gérer les Admins"])

        with tab1:
            st.subheader("Liste des stagiaires")
            if not df_interns.empty:
                st.dataframe(
                    df_interns[["name","department","id"]].rename(
                        columns={"name":"Nom","department":"Service","id":"UUID"}
                    ),
                    use_container_width=True, height=300
                )

                st.markdown("---")
                st.subheader("Supprimer un stagiaire")
                del_name = st.selectbox("Sélectionner", df_interns["name"].dropna().unique(), key="del_sel")
                del_id   = df_interns[df_interns["name"] == del_name]["id"].values[0]
                if st.button("🗑️ Supprimer", type="primary"):
                    try:
                        res = api_delete_intern(del_id)
                        st.success(res.get("message","Supprimé"))
                        st.cache_data.clear()
                        st.rerun()
                    except requests.HTTPError as e:
                        st.error(f"Erreur {e.response.status_code}: {e.response.json().get('detail','')}")

        with tab2:
            st.subheader("Comptes administrateurs existants")

            # ── List all admins ───────────────────────────────────────────
            try:
                r = requests.get(f"{API_BASE}/auth/admins", headers=auth_headers(), timeout=5)
                r.raise_for_status()
                admins_list = r.json()

                # Enrich with department name for display
                dept_map = {d["id"]: d["name"] for _, d in df_departments.iterrows()} if not df_departments.empty else {}
                for a in admins_list:
                    a["department"] = dept_map.get(a["department_id"], "—") if a["department_id"] else "Tous"

                df_admins = pd.DataFrame(admins_list)[["username", "role", "department"]]
                df_admins.columns = ["Identifiant", "Rôle", "Département"]
                st.dataframe(df_admins, use_container_width=True, height=200)

                # ── Delete an admin ───────────────────────────────────────
                st.markdown("---")
                st.subheader("Supprimer un compte")
                # Exclude current user from delete list
                deletable = [a for a in admins_list if a["username"] != st.session_state.auth["username"]]
                if deletable:
                    del_choice = st.selectbox(
                        "Compte à supprimer",
                        options=[a["id"] for a in deletable],
                        format_func=lambda aid: next(a["Identifiant"] for a in df_admins.to_dict("records")
                                                      if any(x["id"] == aid and x["username"] == a["Identifiant"]
                                                             for x in deletable)),
                        key="del_admin_sel"
                    )
                    if st.button("🗑️ Supprimer ce compte", key="del_admin_btn"):
                        try:
                            res = requests.delete(f"{API_BASE}/auth/admins/{del_choice}",
                                                  headers=auth_headers(), timeout=5)
                            res.raise_for_status()
                            st.success(res.json().get("message", "Supprimé"))
                            st.rerun()
                        except requests.HTTPError as e:
                            st.error(e.response.json().get("detail", "Erreur"))
                else:
                    st.info("Aucun autre compte à supprimer.")

            except requests.HTTPError as e:
                st.error(f"Impossible de charger les admins : {e}")

            # ── Create new admin / supervisor ─────────────────────────────
            st.markdown("---")
            st.subheader("Créer un nouveau compte")

            with st.form("create_admin_form"):
                new_username = st.text_input("Identifiant")
                new_password = st.text_input("Mot de passe (min. 8 car.)", type="password")
                new_role     = st.selectbox("Rôle", ["supervisor", "super_admin"],
                                            format_func=lambda r: "Superviseur" if r == "supervisor" else "Super Admin")

                # Department selector — only relevant for supervisors
                dept_options = df_departments.to_dict("records") if not df_departments.empty else []
                new_dept     = st.selectbox(
                    "Département (obligatoire pour Superviseur)",
                    options=[""] + [d["id"] for d in dept_options],
                    format_func=lambda did: "— Aucun (Super Admin) —" if did == ""
                                            else next((d["name"] for d in dept_options if d["id"] == did), did)
                )
                submitted = st.form_submit_button("✅ Créer le compte", use_container_width=True)

            if submitted:
                if not new_username or not new_password:
                    st.error("Identifiant et mot de passe requis.")
                elif len(new_password) < 8:
                    st.error("Le mot de passe doit contenir au moins 8 caractères.")
                else:
                    payload = {
                        "username":      new_username,
                        "password":      new_password,
                        "role":          new_role,
                        "department_id": new_dept if new_dept else None,
                    }
                    try:
                        res = requests.post(f"{API_BASE}/auth/create-admin",
                                            json=payload, headers=auth_headers(), timeout=5)
                        res.raise_for_status()
                        st.success(res.json().get("message", "Compte créé"))
                        st.rerun()
                    except requests.HTTPError as e:
                        st.error(e.response.json().get("detail", "Erreur serveur"))

            # ── Change own password ───────────────────────────────────────
            st.markdown("---")
            st.subheader("Changer mon mot de passe")
            with st.form("change_pwd_form"):
                cur_pwd  = st.text_input("Mot de passe actuel", type="password")
                new_pwd  = st.text_input("Nouveau mot de passe", type="password")
                new_pwd2 = st.text_input("Confirmer le nouveau mot de passe", type="password")
                pwd_submitted = st.form_submit_button("🔑 Mettre à jour", use_container_width=True)

            if pwd_submitted:
                if new_pwd != new_pwd2:
                    st.error("Les deux mots de passe ne correspondent pas.")
                elif len(new_pwd) < 8:
                    st.error("Le nouveau mot de passe doit contenir au moins 8 caractères.")
                else:
                    try:
                        res = requests.post(
                            f"{API_BASE}/auth/change-password",
                            json={"current_password": cur_pwd, "new_password": new_pwd},
                            headers=auth_headers(), timeout=5
                        )
                        res.raise_for_status()
                        st.success(res.json().get("message", "Mot de passe mis à jour"))
                    except requests.HTTPError as e:
                        st.error(e.response.json().get("detail", "Erreur serveur"))


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

if not is_logged_in():
    render_login()
else:
    render_dashboard()