import uuid

import pytest

from app.main import app

def unique_email() -> str:
    token = uuid.uuid4().hex[:10]

    return (
        f"backend-test-{token}@example.com"
    )


def register_user(client):
    email = unique_email()

    payload = {
    "full_name": "Backend Test User",
    "email": email,
    "password": "TestPassword123!",
}

    response = client.post(
        "/api/v1/auth/register",
        json=payload,
    )

    assert response.status_code in (
        200,
        201,
    ), response.text

    return {
        "email": email,
        "password": payload["password"],
        "register_response": response.json(),
    }


def login_user(
    client,
    email: str,
    password: str,
):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )

    assert response.status_code == 200, (
        response.text
    )

    data = response.json()

    token = (
        data.get("access_token")
        or data.get("token")
    )

    assert token, (
        "Login response did not contain "
        "access_token/token"
    )

    return token


def auth_headers(
    token: str,
) -> dict[str, str]:
    return {
        "Authorization": (
            f"Bearer {token}"
        )
    }


def create_consumer_chat(
    client,
    token: str,
):
    response = client.post(
        "/api/v1/chats",
        headers=auth_headers(
            token
        ),
        json={
            "title": (
                "API regression consumer test"
            ),
            "category": (
                "consumer_rights"
            ),
        },
    )

    assert response.status_code in (
        200,
        201,
    ), response.text

    data = response.json()

    assert data["category"] == (
        "consumer_rights"
    )

    return data


def test_health(client):
    response = client.get(
        "/health"
    )

    assert response.status_code == 200

    data = response.json()

    assert isinstance(
        data,
        dict,
    )


def test_protected_chat_requires_auth(client):
    response = client.get(
        "/api/v1/chats"
    )

    assert response.status_code in (
        401,
        403,
    )


def test_auth_and_chat_crud(client):
    account = register_user(client)

    token = login_user(
        client,
        account["email"],
        account["password"],
    )

    headers = auth_headers(
        token
    )

    # ----------------------------
    # CREATE CHAT
    # ----------------------------

    chat = create_consumer_chat(
        client,
        token
    )

    chat_id = chat["id"]

    assert chat_id

    # ----------------------------
    # LIST CHATS
    # ----------------------------

    response = client.get(
        "/api/v1/chats",
        headers=headers,
    )

    assert response.status_code == 200, (
        response.text
    )

    chats = response.json()

    assert any(
        item["id"] == chat_id
        for item in chats
    )

    # ----------------------------
    # GET CHAT
    # ----------------------------

    response = client.get(
        f"/api/v1/chats/{chat_id}",
        headers=headers,
    )

    assert response.status_code == 200, (
        response.text
    )

    assert response.json()["id"] == (
        chat_id
    )

    # ----------------------------
    # UPDATE CHAT
    # ----------------------------

    response = client.patch(
        f"/api/v1/chats/{chat_id}",
        headers=headers,
        json={
            "title": (
                "Updated regression chat"
            )
        },
    )

    assert response.status_code == 200, (
        response.text
    )

    assert (
        response.json()["title"]
        == "Updated regression chat"
    )

    # ----------------------------
    # DELETE CHAT
    # ----------------------------

    response = client.delete(
        f"/api/v1/chats/{chat_id}",
        headers=headers,
    )

    assert response.status_code in (
        200,
        204,
    ), response.text

    # ----------------------------
    # VERIFY DELETE
    # ----------------------------

    response = client.get(
        f"/api/v1/chats/{chat_id}",
        headers=headers,
    )

    assert response.status_code == 404


def test_chat_ownership_isolation(client):
    first = register_user(client)

    first_token = login_user(
        client,
        first["email"],
        first["password"],
    )

    second = register_user(client)

    second_token = login_user(
        client,
        second["email"],
        second["password"],
    )

    chat = create_consumer_chat(
        client,
        first_token
    )

    chat_id = chat["id"]

    # User 2 must not see user 1's chat.
    response = client.get(
        f"/api/v1/chats/{chat_id}",
        headers=auth_headers(
            second_token
        ),
    )

    assert response.status_code == 404

    # User 2 must not update it.
    response = client.patch(
        f"/api/v1/chats/{chat_id}",
        headers=auth_headers(
            second_token
        ),
        json={
            "title": "Unauthorized"
        },
    )

    assert response.status_code == 404

    # User 2 must not delete it.
    response = client.delete(
        f"/api/v1/chats/{chat_id}",
        headers=auth_headers(
            second_token
        ),
    )

    assert response.status_code == 404


@pytest.mark.integration
def test_rag_chat_turn(client):
    account = register_user(client)

    token = login_user(
        client,
        account["email"],
        account["password"],
    )

    headers = auth_headers(
        token
    )

    chat = create_consumer_chat(
        client,
        token
    )

    chat_id = chat["id"]

    response = client.post(
        (
            f"/api/v1/chats/"
            f"{chat_id}/messages"
        ),
        headers=headers,
        json={
            "content": (
                "How can a consumer file "
                "a complaint against a seller?"
            )
        },
    )

    assert response.status_code == 201, (
        response.text
    )

    data = response.json()

    assert (
        data["user_message"]["role"]
        == "user"
    )

    assert (
        data["assistant_message"]["role"]
        == "assistant"
    )

    assert (
        data["assistant_message"][
            "status"
        ]
        in (
            "completed",
            "failed",
        )
    )

    # A successful RAG response should
    # either contain citations/sources,
    # or be a safe fallback.
    assistant = data[
        "assistant_message"
    ]

    if assistant["status"] == "completed":
        assert assistant["content"]

    # ----------------------------
    # VERIFY PERSISTENCE
    # ----------------------------

    response = client.get(
        (
            f"/api/v1/chats/"
            f"{chat_id}/messages"
        ),
        headers=headers,
    )

    assert response.status_code == 200, (
        response.text
    )

    messages = response.json()

    roles = [
        message["role"]
        for message in messages
    ]

    assert "user" in roles
    assert "assistant" in roles


@pytest.mark.integration
def test_conversation_follow_up(client):
    account = register_user(client)

    token = login_user(
        client,
        account["email"],
        account["password"],
    )

    headers = auth_headers(
        token
    )

    chat = create_consumer_chat(
        client,
        token
    )

    chat_id = chat["id"]

    first_response = client.post(
        (
            f"/api/v1/chats/"
            f"{chat_id}/messages"
        ),
        headers=headers,
        json={
            "content": (
                "How can I file a consumer "
                "complaint against a seller?"
            )
        },
    )

    assert (
        first_response.status_code
        == 201
    ), first_response.text

    second_response = client.post(
        (
            f"/api/v1/chats/"
            f"{chat_id}/messages"
        ),
        headers=headers,
        json={
            "content": (
                "Where can I file it?"
            )
        },
    )

    assert (
        second_response.status_code
        == 201
    ), second_response.text

    data = second_response.json()

    assistant = data[
        "assistant_message"
    ]

    assert assistant[
        "role"
    ] == "assistant"

    assert assistant["content"]


@pytest.mark.integration
def test_category_boundary(client):
    account = register_user(client)

    token = login_user(
        client,
        account["email"],
        account["password"],
    )

    headers = auth_headers(
        token
    )

    chat = create_consumer_chat(
        client,
        token
    )

    chat_id = chat["id"]

    response = client.post(
        (
            f"/api/v1/chats/"
            f"{chat_id}/messages"
        ),
        headers=headers,
        json={
            "content": (
                "What happens if my employer "
                "does not pay minimum wage?"
            )
        },
    )

    assert response.status_code == 201, (
        response.text
    )

    assistant = response.json()[
        "assistant_message"
    ]

    assert assistant["content"]

    # Consumer chat should never return
    # labour-law source metadata.
    for source in assistant.get(
        "sources",
        [],
    ):
        assert source.get(
            "category"
        ) != "labour_rights"