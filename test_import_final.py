#!/usr/bin/env python3
"""
Script de test complet des endpoints d'import Excel.
"""

import requests
import time

API_URL = "http://127.0.0.1:8000"

def test_all():
    """Test tous les endpoints."""
    
    # Connexion
    print("🔐 Connexion...")
    res = requests.post(f"{API_URL}/auth/login", json={
        "username": "dfri",
        "password": "dfri1234"
    })
    if res.status_code != 200:
        print(f"❌ Erreur connexion: {res.text}")
        return
    
    token = res.json()['access_token']
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ Connecté")
    
    # Test 1: Template
    print("\n📥 Test template download...")
    res = requests.get(f"{API_URL}/interns/import/template", headers=headers)
    if res.status_code == 200:
        print(f"✅ Template téléchargé ({len(res.content)} octets)")
    else:
        print(f"❌ Erreur: {res.status_code}")
        return
    
    # Test 2: Validation
    print("\n✓ Test validation...")
    with open("c:\\CHU_PFE_clean\\test_import_data.xlsx", "rb") as f:
        files = {"file": f}
        res = requests.post(f"{API_URL}/interns/import/validate", headers=headers, files=files)
    
    if res.status_code == 200:
        data = res.json()
        print(f"✅ Validation: {data['valid_count']} valides, {data['errors_count']} erreurs")
    else:
        print(f"❌ Erreur: {res.status_code} - {res.text}")
        return
    
    # Test 3: Import
    print("\n📤 Test import...")
    with open("c:\\CHU_PFE_clean\\test_import_data.xlsx", "rb") as f:
        files = {"file": f}
        res = requests.post(f"{API_URL}/interns/import", headers=headers, files=files)
    
    if res.status_code == 200:
        data = res.json()
        print(f"✅ Import: {data['created_count']} stagiaires créés")
    else:
        print(f"❌ Erreur: {res.status_code} - {res.text}")
        return
    
    # Vérification finale
    print("\n✓ Vérification...")
    res = requests.get(f"{API_URL}/interns", headers=headers)
    if res.status_code == 200:
        interns = res.json()
        print(f"✅ Total stagiaires en base: {len(interns)}")
        for i in interns[-5:]:  # Afficher les 5 derniers
            print(f"   - {i['first_name']} {i['last_name']} (ID: {i['id'][:8]}...)")
    
    print("\n✅ TOUS LES TESTS RÉUSSIS!")

if __name__ == "__main__":
    try:
        test_all()
    except Exception as e:
        print(f"❌ Erreur: {e}")
