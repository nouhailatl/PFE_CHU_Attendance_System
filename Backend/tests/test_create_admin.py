#!/usr/bin/env python3
"""Test script for create-admin endpoint"""

import requests
import json

BASE_URL = "http://localhost:8000"

try:
    # Login
    login_res = requests.post(f"{BASE_URL}/auth/login", json={
        "username": "dfri",
        "password": "dfri1234"
    })
    
    if login_res.status_code != 200:
        print(f"Login failed: {login_res.status_code}")
        print(f"Response: {login_res.text}")
        exit(1)
    
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    print("Logged in successfully\n")
    
    # Test 1: Chef de Service without department (should fail with 400)
    print("=" * 70)
    print("TEST 1: Chef de Service WITHOUT department (expect 400)")
    print("=" * 70)
    
    res = requests.post(f"{BASE_URL}/auth/create-admin", 
        json={
            "username": "test_chef_nodept",
            "password": "Password1234",
            "role": "chef_service",
            "department_id": None
        },
        headers=headers
    )
    
    print(f"Status Code: {res.status_code}")
    print(f"Response Headers: {dict(res.headers)}")
    print(f"Response Body: {res.text}")
    
    if res.status_code == 400:
        print("\n✓ Test passed - got expected 400 error")
    elif res.status_code == 500:
        print("\n✗ Test failed - got 500 error instead of 400")
    else:
        print(f"\n✗ Test failed - got {res.status_code} instead of 400")
    
    print("\n" + "=" * 70)
    print("TEST 2: Secretaire WITHOUT department (expect 200)")
    print("=" * 70)
    
    res = requests.post(f"{BASE_URL}/auth/create-admin", 
        json={
            "username": "test_sec_nodept",
            "password": "Password1234",
            "role": "secretaire",
            "department_id": None
        },
        headers=headers
    )
    
    print(f"Status Code: {res.status_code}")
    print(f"Response Body: {res.text}")
    
    if res.status_code == 200:
        print("\n✓ Test passed - created account successfully")
    else:
        print(f"\n✗ Test failed - got {res.status_code}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
