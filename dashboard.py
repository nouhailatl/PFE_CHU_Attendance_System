import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from database import engine  
from utils_stats import compute_attendance_metrics, identify_alerts

# --- 1. CONFIGURATION ET THÈME ---
st.set_page_config(
    page_title="CHU Analytics | Dashboard Décisionnel", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# Injection de CSS adaptatif (Variables Streamlit pour support Dark Mode)
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        /* Cartes (Containers) adaptatives */
        div[data-testid="stVerticalBlock"] > div[style*="border: 1px solid"] {
            border: 1px solid rgba(128, 128, 128, 0.2) !important;
            border-radius: 12px !important;
            padding: 20px !important;
            background-color: var(--background-color) !important; /* Adaptatif */
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1) !important;
        }

        /* Metrics adaptatives */
        [data-testid="stMetricValue"] {
            font-size: 1.8rem !important;
            font-weight: 700 !important;
            color: var(--text-color) !important;
        }
        
        [data-testid="stMetricLabel"] {
            font-size: 0.9rem !important;
            text-transform: uppercase !important;
            letter-spacing: 0.05em !important;
            color: var(--text-color) !important;
            opacity: 0.8;
        }

        /* Sidebar adaptative */
        [data-testid="stSidebar"] {
            background-color: var(--secondary-background-color) !important;
            border-right: 1px solid rgba(128, 128, 128, 0.1);
        }

        /* Titres forcés sur la couleur du thème */
        h1, h2, h3, h4 {
            color: var(--text-color) !important;
            font-weight: 700 !important;
        }

        /* Fix pour les widgets en mode sombre */
        .stSelectbox label, .stRadio label {
            color: var(--text-color) !important;
        }
    </style>
""", unsafe_allow_html=True)

# Couleurs pour les graphiques
COLOR_PRIMARY = "#2563eb"  # Bleu CHU
COLOR_SECONDARY = "#10b981" 

# --- 2. FONCTION POUR LES GRAPHIQUES ADAPTATIFS ---
def update_chart_theme(fig):
    """Rend le fond du graphique transparent pour s'adapter au mode sombre/clair"""
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_color='gray',
        margin=dict(l=10, r=10, t=40, b=10),
        template="plotly_white" if st.get_option("theme.base") == "light" else "plotly_dark"
    )
    return fig

# --- 3. CHARGEMENT DES DONNÉES ---
@st.cache_data(ttl=60)
def load_all_data():
    query_interns = """
        SELECT i.id, i.first_name, i.last_name, d.name as department 
        FROM interns i
        LEFT JOIN departments d ON i.department_id = d.id
    """
    df_int = pd.read_sql(query_interns, engine)
    df_att = pd.read_sql("SELECT * FROM attendance_events", engine)
    df_daily = pd.read_sql("SELECT * FROM daily_status", engine)
    df_depts = pd.read_sql("SELECT * FROM departments", engine)
    
    if not df_int.empty:
        df_int['name'] = df_int['first_name'] + " " + df_int['last_name']
    df_att['timestamp'] = pd.to_datetime(df_att['timestamp'])
    return df_att, df_int, df_depts, df_daily

try:
    df_attendance, df_interns, df_departments, df_daily = load_all_data()
except Exception as e:
    st.error(f"Erreur de connexion à la base de données : {e}")
    st.stop()

# --- 4. SIDEBAR NAVIGATION ---
with st.sidebar:
    st.title("CHU Analytics")
    st.markdown("---")
    menu = st.radio(
        "Navigation", 
        ["Vue Globale", "Vue Individuelle", "Vue Départementale", "Clusters & ML", "Journal des Alertes"],
        index=0
    )
    st.markdown("---")
    st.caption("Système de Monitoring Temps-Réel v2.1")

# --- 5. LOGIQUE DES MENUS ---

# --- VUE GLOBALE ---
if menu == "Vue Globale":
    st.header("Surveillance des Flux")
    
    today = datetime.utcnow().date()
    yesterday = today - timedelta(days=1)
    
    present_today = df_attendance[df_attendance['timestamp'].dt.date == today]['intern_id'].nunique()
    present_yesterday = df_attendance[df_attendance['timestamp'].dt.date == yesterday]['intern_id'].nunique()
    delta_presences = int(present_today - present_yesterday)

    # Metrics
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Total Stagiaires", len(df_interns))
    with m2:
        st.metric("Présences Jour", present_today, delta=delta_presences)
    with m3:
        st.metric("Services Opérationnels", len(df_departments))
    
    st.markdown("### Analyse de l'Activité")
    col_left, col_right = st.columns(2)
    
    with col_left:
        with st.container(border=True):
            st.subheader("Évolution Temporelle des Scans")
            df_counts = df_attendance.groupby(df_attendance['timestamp'].dt.date).size().reset_index(name='scans')
            fig_flow = px.area(df_counts, x='timestamp', y='scans', color_discrete_sequence=[COLOR_PRIMARY])
            st.plotly_chart(update_chart_theme(fig_flow), use_container_width=True)

    with col_right:
        with st.container(border=True):
            st.subheader("Concentration Horaire")
            if not df_attendance.empty:
                df_attendance['hour'] = df_attendance['timestamp'].dt.hour
                df_attendance['day'] = df_attendance['timestamp'].dt.day_name()
                days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                heatmap_data = df_attendance.groupby(['day', 'hour']).size().unstack(fill_value=0)
                heatmap_data = heatmap_data.reindex(days_order).fillna(0)
                
                fig_heat = px.imshow(heatmap_data, labels=dict(x="Heure", y="Jour", color="Scans"), color_continuous_scale='Blues')
                st.plotly_chart(update_chart_theme(fig_heat), use_container_width=True)

# --- VUE INDIVIDUELLE ---
elif menu == "Vue Individuelle":
    st.header("Analyse Profil 360°")
    if not df_interns.empty:
        selected_name = st.selectbox("Sélectionner un stagiaire", df_interns['name'].dropna().unique())
        selection = df_interns[df_interns['name'] == selected_name]
        
        if not selection.empty:
            intern_info = selection.iloc[0]
            intern_id = intern_info['id']
            col_a, col_b = st.columns([1, 2])
            
            with col_a:
                with st.container(border=True):
                    st.markdown(f"#### {intern_info['name']}")
                    st.markdown(f"**Département :** `{intern_info['department']}`")
                    st.divider()
                    categories = ['Ponctualité', 'Assiduité', 'Engagement', 'Cohérence']
                    fig_radar = go.Figure(data=go.Scatterpolar(
                        r=[80, 90, 70, 85], theta=categories, fill='toself',
                        fillcolor='rgba(37, 99, 235, 0.2)', line=dict(color=COLOR_PRIMARY, width=2)
                    ))
                    st.plotly_chart(update_chart_theme(fig_radar), use_container_width=True)
            
            with col_b:
                with st.container(border=True):
                    st.subheader("Historique d'Activité")
                    personal_logs = df_attendance[df_attendance['intern_id'] == intern_id].sort_values('timestamp', ascending=False)
                    st.dataframe(personal_logs[['timestamp', 'type']].rename(columns={'timestamp': 'Date & Heure', 'type': 'Événement'}), use_container_width=True, height=400)

# --- VUE DÉPARTEMENTALE ---
elif menu == "Vue Départementale":
    st.header("Pilotage des Services")
    col_c, col_d = st.columns(2)
    
    with col_c:
        with st.container(border=True):
            st.subheader("Répartition des Effectifs")
            dept_dist = df_interns['department'].value_counts().reset_index()
            dept_dist.columns = ['Service', 'Effectif']
            fig_pie = px.pie(dept_dist, values='Effectif', names='Service', hole=0.6)
            st.plotly_chart(update_chart_theme(fig_pie), use_container_width=True)
    
    with col_d:
        with st.container(border=True):
            st.subheader("Volume d'Activité par Service")
            df_merged = df_attendance.merge(df_interns, left_on='intern_id', right_on='id')
            dept_act = df_merged['department'].value_counts().reset_index()
            dept_act.columns = ['Service', 'Total Scans']
            fig_bar = px.bar(dept_act, x='Service', y='Total Scans', color='Total Scans', color_continuous_scale='Blues')
            st.plotly_chart(update_chart_theme(fig_bar), use_container_width=True)

# --- CLUSTERS & ML ---
elif menu == "Clusters & ML":
    st.header("Intelligence Comportementale")
    with st.container(border=True):
        st.subheader("Segmentation des Profils (K-Means)")
        mock_data = pd.DataFrame({
            'PCA1': [1, 2, -1, 0, 5, 2, 3, -1],
            'PCA2': [2, -1, 0, 3, -2, 1, 4, 0],
            'Segment': ['Régulier', 'Régulier', 'À Risque', 'Désengagé', 'Élite', 'Régulier', 'Élite', 'À Risque'],
            'Stagiaire': ['Stagiaire A', 'Stagiaire B', 'Stagiaire C', 'Stagiaire D', 'Stagiaire E', 'Stagiaire F', 'Stagiaire G', 'Stagiaire H']
        })
        fig_ml = px.scatter(mock_data, x='PCA1', y='PCA2', color='Segment', hover_name='Stagiaire', size=[10]*8)
        st.plotly_chart(update_chart_theme(fig_ml), use_container_width=True)
        st.info("Cette projection utilise une réduction de dimensionnalité pour identifier les patterns d'engagement.")

# --- JOURNAL DES ALERTES ---
elif menu == "Journal des Alertes":
    st.header("Centre de Gestion des Anomalies")
    try:
        alerts = identify_alerts(df_attendance, df_interns)
        if not alerts.empty:
            st.warning(f"Système : {len(alerts)} alertes critiques détectées.")
            # Style conditionnel adapté au mode sombre/clair
            st.table(alerts)
        else:
            st.success("État du personnel : Nominal. Aucune anomalie détectée.")
    except Exception as e:
        st.info("Module d'alertes en cours d'initialisation.")