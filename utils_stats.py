import pandas as pd
import numpy as np
from datetime import datetime

def compute_attendance_metrics(df_attendance, df_interns):
    """
    Transforme les événements bruts en indicateurs de performance (KPIs)
    Conforme au point 2.3 du rapport : Feature Engineering.
    """
    if df_attendance.empty:
        return pd.DataFrame()

    # 1. Calcul des sessions (Appariement check-in/check-out)
    df = df_attendance.sort_values(['intern_id', 'timestamp'])
    
    # On crée une colonne pour le scan suivant pour calculer la durée
    df['next_timestamp'] = df.groupby('intern_id')['timestamp'].shift(-1)
    df['next_status'] = df.groupby('intern_id')['status'].shift(-1)
    
    # Une session valide est un 'check-in' suivi d'un 'check-out'
    sessions = df[(df['status'] == 'check-in') & (df['next_status'] == 'check-out')].copy()
    sessions['duration_hours'] = (sessions['next_timestamp'] - sessions['timestamp']).dt.total_seconds() / 3600

    # 2. Agrégation par stagiaire
    metrics = sessions.groupby('intern_id').agg(
        total_hours=('duration_hours', 'sum'),
        avg_session=('duration_hours', 'mean'),
        nb_sessions=('duration_hours', 'count')
    ).reset_index()

    # 3. Fusion avec les infos stagiaires pour avoir les noms et départements
    full_metrics = pd.merge(metrics, df_interns, left_on='intern_id', right_on='id', how='right')
    
    # Remplissage des valeurs vides pour les nouveaux stagiaires sans scans
    full_metrics[['total_hours', 'nb_sessions']] = full_metrics[['total_hours', 'nb_sessions']].fillna(0)
    
    # 4. Calcul du Taux de Présence (%)
    # Hypothèse : Un stage complet sur 2 mois (40 jours ouvrés environ)
    jours_attendus = 40 
    full_metrics['presence_rate'] = (full_metrics['nb_sessions'] / jours_attendus * 100).clip(upper=100)
    
    return full_metrics

def get_daily_activity(df_attendance):
    """
    Prépare les données pour la Vue Globale (Analyse temporelle).
    """
    df_attendance['date'] = df_attendance['timestamp'].dt.date
    daily = df_attendance.groupby('date').size().reset_index(name='scan_count')
    return daily

def identify_alerts(df_attendance, df_interns):
    """
    Logique du Système d'alertes (Point 3.3 du PDF)[cite: 1].
    """
    today = pd.Timestamp(datetime.now().date())
    last_scans = df_attendance.groupby('intern_id')['timestamp'].max().reset_index()
    
    # Fusion avec les stagiaires
    alerts = pd.merge(df_interns, last_scans, left_on='id', right_on='intern_id', how='left')
    alerts['days_since_last'] = (today - alerts['timestamp'].dt.normalize()).dt.days
    
    # Application des règles métier du rapport[cite: 1] :
    # Critique : Absence >= 3 jours
    critique = alerts[alerts['days_since_last'] >= 3].copy()
    critique['level'] = 'CRITIQUE'
    
    return critique[['name', 'department', 'days_since_last', 'level']]