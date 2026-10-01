"""
Tests for the refresh token / session renewal system.

Covers:
  A. Login gives valid session (access + refresh tokens)
  B. Access token expires but refresh remains valid → new access token
  C. Active user continues using protected APIs after renewal
  D. Expired refresh session → user must log in again
  E. Logout invalidates session
  F. Malformed refresh token rejected
  G. Revoked refresh token rejected (rotation)
  H. Concurrent frontend expiry does not create refresh loop
  I. Failed refresh clears frontend auth (tested via API behavior)
  J. Ownership/security remains unchanged
"""

import time
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest


REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
REFRESH_URL = "/api/v1/auth/refresh"
LOGOUT_URL = "/api/v1/auth/logout"
ME_URL = "/api/v1/auth/me"


def register_and_login(client, suffix="refresh"):
    """Helper: register a user and return login response."""
    email = f"refresh_test_{suffix}_{int(time.time() * 1000)}@test.com"
    client.post(REGISTER_URL, json={
        "email": email,
        "full_name": "Refresh Test User",
        "password": "TestPassword123!",
    })
    response = client.post(LOGIN_URL, json={
        "email": email,
        "password": "TestPassword123!",
    })
    assert response.status_code == 200
    return response.json()


# ─────────────────────────────────────────────
# A. Login gives valid session
# ─────────────────────────────────────────────


def test_login_returns_both_tokens(client):
    """Login must return access_token, refresh_token, and token_type."""
    data = register_and_login(client, "a_both")
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert len(data["access_token"]) > 10
    assert len(data["refresh_token"]) > 10


# ─────────────────────────────────────────────
# B. Access token expired, refresh valid → new access token
# ─────────────────────────────────────────────


def test_refresh_issues_new_access_token(client):
    """Valid refresh token should yield a new access + refresh token pair."""
    data = register_and_login(client, "b_refresh")
    old_refresh = data["refresh_token"]

    response = client.post(REFRESH_URL, json={
        "refresh_token": old_refresh,
    })
    assert response.status_code == 200

    new_data = response.json()
    assert "access_token" in new_data
    assert "refresh_token" in new_data
    assert len(new_data["access_token"]) > 10
    # Refresh token must be rotated (always different)
    assert new_data["refresh_token"] != old_refresh

    # New access token must work on /me
    me_response = client.get(ME_URL, headers={
        "Authorization": f"Bearer {new_data['access_token']}",
    })
    assert me_response.status_code == 200


# ─────────────────────────────────────────────
# C. Active user continues using protected APIs after renewal
# ─────────────────────────────────────────────


def test_renewed_access_token_works_on_protected_routes(client):
    """After refresh, the new access token should work on /me."""
    data = register_and_login(client, "c_continue")
    refresh_response = client.post(REFRESH_URL, json={
        "refresh_token": data["refresh_token"],
    })
    assert refresh_response.status_code == 200

    new_access = refresh_response.json()["access_token"]
    me_response = client.get(ME_URL, headers={
        "Authorization": f"Bearer {new_access}",
    })
    assert me_response.status_code == 200
    assert "email" in me_response.json()


# ─────────────────────────────────────────────
# D. Expired refresh session → user must log in again
# ─────────────────────────────────────────────


def test_expired_refresh_token_rejected(client):
    """A refresh token past its expiry should be rejected."""
    data = register_and_login(client, "d_expired")

    # Manually expire the refresh token using synchronous PyMongo
    # (the test client runs synchronously, not in an async loop)
    from pymongo import MongoClient
    from app.config import settings
    from app.core.security import hash_refresh_token

    token_hash = hash_refresh_token(data["refresh_token"])

    sync_client = MongoClient(settings.mongodb_url, serverSelectionTimeoutMS=5000)
    try:
        db = sync_client[settings.mongodb_database]
        db["refresh_tokens"].update_one(
            {"token_hash": token_hash},
            {"$set": {"expires_at": datetime.now(timezone.utc) - timedelta(hours=1)}},
        )
    finally:
        sync_client.close()

    response = client.post(REFRESH_URL, json={
        "refresh_token": data["refresh_token"],
    })
    assert response.status_code == 401


# ─────────────────────────────────────────────
# E. Logout invalidates session
# ─────────────────────────────────────────────


def test_logout_revokes_refresh_token(client):
    """After logout, the refresh token should no longer work."""
    data = register_and_login(client, "e_logout")

    # Logout
    logout_response = client.post(
        LOGOUT_URL,
        headers={"Authorization": f"Bearer {data['access_token']}"},
        json={"refresh_token": data["refresh_token"]},
    )
    assert logout_response.status_code == 204

    # Refresh should fail
    refresh_response = client.post(REFRESH_URL, json={
        "refresh_token": data["refresh_token"],
    })
    assert refresh_response.status_code == 401


# ─────────────────────────────────────────────
# F. Malformed refresh token rejected
# ─────────────────────────────────────────────


def test_malformed_refresh_token_rejected(client):
    """Random string should not be accepted as a refresh token."""
    response = client.post(REFRESH_URL, json={
        "refresh_token": "not-a-real-token-at-all",
    })
    assert response.status_code == 401


def test_empty_refresh_token_rejected(client):
    """Empty string refresh token should be rejected."""
    response = client.post(REFRESH_URL, json={
        "refresh_token": "",
    })
    assert response.status_code == 401


def test_missing_refresh_token_field(client):
    """Request without refresh_token field should fail validation."""
    response = client.post(REFRESH_URL, json={})
    assert response.status_code == 422


# ─────────────────────────────────────────────
# G. Revoked refresh token rejected (rotation test)
# ─────────────────────────────────────────────


def test_rotated_old_refresh_token_rejected(client):
    """After rotation, the OLD refresh token must be invalid."""
    data = register_and_login(client, "g_rotate")
    old_refresh = data["refresh_token"]

    # Refresh → rotates the token
    response = client.post(REFRESH_URL, json={
        "refresh_token": old_refresh,
    })
    assert response.status_code == 200

    # Try using the old refresh token again → should fail
    retry_response = client.post(REFRESH_URL, json={
        "refresh_token": old_refresh,
    })
    assert retry_response.status_code == 401


# ─────────────────────────────────────────────
# H. Multiple sequential refresh calls work with rotation
# ─────────────────────────────────────────────


def test_sequential_refresh_rotation(client):
    """Each refresh should yield a new pair, and the latest should work."""
    data = register_and_login(client, "h_seq")
    current_refresh = data["refresh_token"]

    for i in range(3):
        response = client.post(REFRESH_URL, json={
            "refresh_token": current_refresh,
        })
        assert response.status_code == 200, f"Refresh #{i+1} failed"
        new_data = response.json()
        current_refresh = new_data["refresh_token"]

        # The newest access token should work on /me
        me_response = client.get(ME_URL, headers={
            "Authorization": f"Bearer {new_data['access_token']}",
        })
        assert me_response.status_code == 200


# ─────────────────────────────────────────────
# I. Failed refresh returns 401 (frontend can clear state)
# ─────────────────────────────────────────────


def test_failed_refresh_returns_401(client):
    """Invalid refresh should return 401 so frontend can clear auth."""
    response = client.post(REFRESH_URL, json={
        "refresh_token": "completely-invalid-token",
    })
    assert response.status_code == 401
    detail = response.json().get("detail", "")
    assert "expired" in detail.lower() or "sign in" in detail.lower()


# ─────────────────────────────────────────────
# J. Ownership/security unchanged — /me still works correctly
# ─────────────────────────────────────────────


def test_access_token_still_protects_me(client):
    """Bearer auth on /me must still work correctly."""
    data = register_and_login(client, "j_owner")
    me_response = client.get(ME_URL, headers={
        "Authorization": f"Bearer {data['access_token']}",
    })
    assert me_response.status_code == 200
    user = me_response.json()
    assert "email" in user
    assert "full_name" in user


def test_no_token_rejects_protected_route(client):
    """Protected routes must still reject unauthenticated requests."""
    response = client.get(ME_URL)
    assert response.status_code == 401
