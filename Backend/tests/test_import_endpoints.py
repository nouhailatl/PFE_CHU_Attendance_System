#!/usr/bin/env python3
"""
Script de test pour les endpoints d'import Excel.
"""

import requests
import json
from pathlib import Path

# Configuration
API_URL = "http://127.0.0.1:8000"
TEST_FILE = Path("c:\\CHU_PFE_clean\\test_import_data.xlsx")

# Authentification par défaut pour les tests
DEFAULT_CREDS = {
    "username": "dfri",
    "password": "dfri1234"
}

def login():
    """Connecte l'utilisateur et retourne le token."""
    res = requests.post(f"{API_URL}/auth/login", json=DEFAULT_CREDS)
    if res.status_code != 200:
        print(f"Erreur de connexion: {res.text}")
        return None
    return res.json()['access_token']

def test_template_download(token):
    """Teste le téléchargement du template."""
    print("\nTest: Téléchargement du template Excel...")
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get(f"{API_URL}/interns/import/template", headers=headers)
    if res.status_code == 200:
        print(f"Template téléchargé avec succès ({len(res.content)} octets)")
        return True
    else:
        print(f"Erreur: {res.status_code} - {res.text}")
        return False

def test_validate_import(token):
    """Teste la validation du fichier d'import."""
    print("\nTest: Validation du fichier d'import...")
    if not TEST_FILE.exists():
        print(f"Fichier de test non trouvé: {TEST_FILE}")
        return False
    
    headers = {"Authorization": f"Bearer {token}"}
    with open(TEST_FILE, "rb") as f:
        files = {"file": f}
        res = requests.post(f"{API_URL}/interns/import/validate", headers=headers, files=files)
    
    if res.status_code == 200:
        data = res.json()
        print(f"Validation réussie:")
        print(f"   - Lignes valides: {data.get('valid_count', 0)}")
        print(f"   - Lignes avec erreurs: {data.get('errors_count', 0)}")
        if data.get('errors_details'):
            for err in data['errors_details']:
                print(f"     Ligne {err['row']}: {err['message']}")
        return True
    else:
        print(f"Erreur: {res.status_code} - {res.text}")
        return False

def test_import(token):
    """Teste l'import réel des données."""
    print("\nTest: Import des stagiaires...")
    if not TEST_FILE.exists():
        print(f"Fichier de test non trouvé: {TEST_FILE}")
        return False
    
    headers = {"Authorization": f"Bearer {token}"}
    with open(TEST_FILE, "rb") as f:
        files = {"file": f}
        res = requests.post(f"{API_URL}/interns/import", headers=headers, files=files)
    
    if res.status_code == 200:
        data = res.json()
        print(f"Import réussi:")
        print(f"   - Message: {data.get('message', '')}")
        print(f"   - Stagiaires créés: {data.get('created_count', 0)}")
        return True
    else:
        print(f"Erreur: {res.status_code} - {res.text}")
        return False

def main():
    print("=" * 60)
    print("Test des endpoints d'import Excel")
    print("=" * 60)
    
    # Se connecter
    print("\nConnexion...")
    token = login()
    if not token:
        print("Impossible de se connecter. Assurez-vous que le serveur est actif.")
        return
    print("Connecté avec succès")
    
    # Tests
    test_template_download(token)
    test_validate_import(token)
    test_import(token)
    
    print("\n" + "=" * 60)
    print("Tests terminés")
    print("=" * 60)

if __name__ == "__main__":
    main()
