#!/usr/bin/env python3
"""
Nyaya AI Non-Destructive Staging Smoke Test Script
Executes safe post-deployment verification against staging URLs.
"""

import os
import sys
import urllib.request
import urllib.error
import json


def run_staging_smoke():
    backend_url = os.getenv("STAGING_BACKEND_URL", "http://localhost:8000").rstrip("/")
    frontend_url = os.getenv("STAGING_FRONTEND_URL", "http://localhost:8080").rstrip("/")

    print(f"=== Starting Nyaya AI Staging Smoke Test ===")
    print(f"Target Backend:  {backend_url}")
    print(f"Target Frontend: {frontend_url}\n")

    failures = 0

    # 1. Health Endpoint Verification
    try:
        req = urllib.request.Request(f"{backend_url}/health")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if resp.status == 200 and data.get("status") == "ok":
                print("[PASS] Backend /health endpoint returned status ok")
            else:
                print(f"[FAIL] Backend /health invalid response: {data}")
                failures += 1
    except Exception as exc:
        print(f"[FAIL] Backend /health connection failed: {exc}")
        failures += 1

    # 2. Version Endpoint Verification
    try:
        req = urllib.request.Request(f"{backend_url}/version")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if resp.status == 200 and "version" in data and "release_id" in data:
                print(f"[PASS] Backend /version returned release_id: {data.get('release_id')}")
            else:
                print(f"[FAIL] Backend /version invalid response: {data}")
                failures += 1
    except Exception as exc:
        print(f"[FAIL] Backend /version connection failed: {exc}")
        failures += 1

    # 3. Protected Route Rejection Verification
    try:
        req = urllib.request.Request(f"{backend_url}/api/v1/auth/me")
        urllib.request.urlopen(req, timeout=10)
        print("[FAIL] Protected route /api/v1/auth/me accepted request without Authorization header")
        failures += 1
    except urllib.error.HTTPError as err:
        if err.code in (401, 403):
            print(f"[PASS] Protected route /api/v1/auth/me correctly rejected unauthenticated request ({err.code})")
            sec_header = err.headers.get("X-Content-Type-Options")
            if sec_header == "nosniff":
                print("[PASS] Security header X-Content-Type-Options: nosniff present on API response")
            else:
                print(f"[WARN] X-Content-Type-Options missing or unexpected: {sec_header}")
        else:
            print(f"[FAIL] Protected route returned unexpected HTTP status: {err.code}")
            failures += 1
    except Exception as exc:
        print(f"[FAIL] Protected route check failed: {exc}")
        failures += 1

    # 4. Frontend SPA Reachability
    try:
        req = urllib.request.Request(frontend_url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            if resp.status == 200 and ("<div id=\"root\"" in html or "<script" in html):
                print("[PASS] Frontend static site returned 200 OK with valid React SPA entry HTML")
            else:
                print(f"[FAIL] Frontend html response invalid or empty")
                failures += 1
    except Exception as exc:
        print(f"[FAIL] Frontend static site connection failed: {exc}")
        failures += 1

    print("\n=== Smoke Test Summary ===")
    if failures == 0:
        print("ALL STAGING SMOKE CHECKS PASSED SUCCESSFULLY.")
        sys.exit(0)
    else:
        print(f"STAGING SMOKE CHECKS FAILED: {failures} failure(s) detected.")
        sys.exit(1)


if __name__ == "__main__":
    run_staging_smoke()
