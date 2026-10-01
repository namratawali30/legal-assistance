import uuid

from app.rag.llm_client import (
    LLMServiceError,
)


def unique_email() -> str:
    token = uuid.uuid4().hex[:10]

    return (
        f"complaint-generation-"
        f"{token}@example.com"
    )


def register_user(
    client,
):
    email = unique_email()

    payload = {
        "full_name":
            "Complaint Generation Test User",

        "email":
            email,

        "password":
            "TestPassword123!",
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
        "email":
            email,

        "password":
            payload["password"],
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
        data.get(
            "access_token"
        )
        or data.get(
            "token"
        )
    )

    assert token

    return token


def auth_headers(
    token: str,
) -> dict[str, str]:
    return {
        "Authorization":
            f"Bearer {token}"
    }


def create_complaint(
    client,
    token: str,
):
    response = client.post(
        "/api/v1/complaints",
        headers=auth_headers(
            token
        ),
        json={
            "title": (
                "Defective mobile phone complaint"
            ),

            "category":
                "consumer_rights",

            "complainant_name":
                "Complaint Test User",

            "complainant_address":
                "Test Address",

            "complainant_contact":
                "9999999999",

            "respondent_name":
                "ABC Electronics",

            "respondent_address":
                "Seller Address",

            "incident_date":
                "2026-08-01",

            "incident_location":
                "Test City",

            "facts": (
                "I purchased a mobile phone from "
                "the seller. The phone was defective "
                "and the seller refused to replace "
                "the product or provide a refund."
            ),

            "relief_requested": (
                "Replacement of the defective "
                "phone or refund of the "
                "purchase amount."
            ),

            "additional_details": {
                "product_name":
                    "Mobile phone",

                "invoice_number":
                    "GEN-TEST-001",

                "purchase_amount":
                    25000,
            },
        },
    )

    assert response.status_code == 201, (
        response.text
    )

    return response.json()


def fake_success_result(
    version: str = "first",
):
    return {
        "generated": True,

        "reason":
            "success",

        "generated_text": (
            "To,\n"
            "[Appropriate Authority]\n\n"
            "Subject: Consumer complaint\n\n"
            "Respected Sir/Madam,\n\n"
            "The complainant states that a "
            "defective mobile phone was supplied "
            "by the respondent.\n\n"
            "The Consumer Protection Act, 2019 "
            "provides the relevant legal framework "
            "for this complaint. [SOURCE_1]\n\n"
            f"Generation version: {version}\n\n"
            "Drafting note: This AI-generated "
            "draft is for general informational "
            "assistance and should be reviewed "
            "before submission."
        ),

        "sources": [
            {
                "citation_id":
                    "SOURCE_1",

                "title":
                    "Consumer Protection Act, 2019",

                "authority":
                    "India Code",

                "category":
                    "consumer_rights",

                "provision_type":
                    "section",

                "provision_number":
                    "35",

                "provision_title":
                    "Manner in which complaint "
                    "shall be made",

                "page_start":
                    20,

                "page_end":
                    21,

                "landing_page":
                    "https://www.indiacode.nic.in/",

                "pdf_url":
                    "https://www.indiacode.nic.in/"
                    "example.pdf",
            }
        ],

        "confidence": {
            "accepted":
                True,

            "reason":
                "sufficient_relevance",

            "top_score":
                0.63,

            "threshold":
                0.52,
        },

        "citation_validation": {
            "valid":
                True,

            "found": [
                "SOURCE_1"
            ],

            "valid_citations": [
                "SOURCE_1"
            ],

            "invalid_citations":
                [],
        },

        "citation_retry_used":
            False,
    }


def test_successful_complaint_generation(
    client,
    monkeypatch,
):
    async def fake_generator(
        complaint,
        top_k=5,
    ):
        return fake_success_result()

    monkeypatch.setattr(
        (
            "app.services."
            "complaint_generation_service."
            "generate_grounded_complaint"
        ),
        fake_generator,
    )

    account = register_user(
        client
    )

    token = login_user(
        client,
        account["email"],
        account["password"],
    )

    complaint = create_complaint(
        client,
        token,
    )

    complaint_id = complaint[
        "id"
    ]

    # Initial state must be draft.
    assert complaint[
        "status"
    ] == "draft"

    assert (
        complaint[
            "generated_text"
        ]
        is None
    )

    # -------------------------
    # GENERATE
    # -------------------------

    response = client.post(
        (
            f"/api/v1/complaints/"
            f"{complaint_id}/generate"
        ),
        headers=auth_headers(
            token
        ),
        json={
            "regenerate":
                False
        },
    )

    assert response.status_code == 200, (
        response.text
    )

    generated = response.json()

    assert generated[
        "status"
    ] == "generated"

    assert generated[
        "generated_text"
    ]

    assert (
        "[SOURCE_1]"
        in generated[
            "generated_text"
        ]
    )

    assert len(
        generated[
            "sources"
        ]
    ) == 1

    assert (
        generated[
            "sources"
        ][0][
            "citation_id"
        ]
        == "SOURCE_1"
    )

    # -------------------------
    # VERIFY PERSISTENCE
    # -------------------------

    response = client.get(
        (
            f"/api/v1/complaints/"
            f"{complaint_id}"
        ),
        headers=auth_headers(
            token
        ),
    )

    assert response.status_code == 200, (
        response.text
    )

    persisted = response.json()

    assert persisted[
        "status"
    ] == "generated"

    assert persisted[
        "generated_text"
    ] == generated[
        "generated_text"
    ]

    assert persisted[
        "sources"
    ] == generated[
        "sources"
    ]


def test_generation_overwrite_protection(
    client,
    monkeypatch,
):
    call_count = {
        "value": 0
    }

    async def fake_generator(
        complaint,
        top_k=5,
    ):
        call_count[
            "value"
        ] += 1

        return fake_success_result()

    monkeypatch.setattr(
        (
            "app.services."
            "complaint_generation_service."
            "generate_grounded_complaint"
        ),
        fake_generator,
    )

    account = register_user(
        client
    )

    token = login_user(
        client,
        account["email"],
        account["password"],
    )

    complaint = create_complaint(
        client,
        token,
    )

    complaint_id = complaint[
        "id"
    ]

    # First generation succeeds.
    response = client.post(
        (
            f"/api/v1/complaints/"
            f"{complaint_id}/generate"
        ),
        headers=auth_headers(
            token
        ),
        json={
            "regenerate":
                False
        },
    )

    assert response.status_code == 200, (
        response.text
    )

    assert call_count[
        "value"
    ] == 1

    # Second generation without permission
    # must not overwrite the draft.
    response = client.post(
        (
            f"/api/v1/complaints/"
            f"{complaint_id}/generate"
        ),
        headers=auth_headers(
            token
        ),
        json={
            "regenerate":
                False
        },
    )

    assert response.status_code == 409, (
        response.text
    )

    # Generator must not have been called again.
    assert call_count[
        "value"
    ] == 1


def test_explicit_regeneration(
    client,
    monkeypatch,
):
    call_count = {
        "value": 0
    }

    async def fake_generator(
        complaint,
        top_k=5,
    ):
        call_count[
            "value"
        ] += 1

        return fake_success_result(
            version=str(
                call_count[
                    "value"
                ]
            )
        )

    monkeypatch.setattr(
        (
            "app.services."
            "complaint_generation_service."
            "generate_grounded_complaint"
        ),
        fake_generator,
    )

    account = register_user(
        client
    )

    token = login_user(
        client,
        account["email"],
        account["password"],
    )

    complaint = create_complaint(
        client,
        token,
    )

    complaint_id = complaint[
        "id"
    ]

    # -------------------------
    # FIRST GENERATION
    # -------------------------

    first_response = client.post(
        (
            f"/api/v1/complaints/"
            f"{complaint_id}/generate"
        ),
        headers=auth_headers(
            token
        ),
        json={
            "regenerate":
                False
        },
    )

    assert (
        first_response.status_code
        == 200
    ), first_response.text

    first_text = (
        first_response
        .json()[
            "generated_text"
        ]
    )

    assert (
        "Generation version: 1"
        in first_text
    )

    # -------------------------
    # EXPLICIT REGENERATION
    # -------------------------

    second_response = client.post(
        (
            f"/api/v1/complaints/"
            f"{complaint_id}/generate"
        ),
        headers=auth_headers(
            token
        ),
        json={
            "regenerate":
                True
        },
    )

    assert (
        second_response.status_code
        == 200
    ), second_response.text

    second_text = (
        second_response
        .json()[
            "generated_text"
        ]
    )

    assert (
        "Generation version: 2"
        in second_text
    )

    assert second_text != first_text

    assert call_count[
        "value"
    ] == 2


def test_generation_ownership_isolation(
    client,
    monkeypatch,
):
    generator_called = {
        "value": False
    }

    async def fake_generator(
        complaint,
        top_k=5,
    ):
        generator_called[
            "value"
        ] = True

        return fake_success_result()

    monkeypatch.setattr(
        (
            "app.services."
            "complaint_generation_service."
            "generate_grounded_complaint"
        ),
        fake_generator,
    )

    first = register_user(
        client
    )

    first_token = login_user(
        client,
        first["email"],
        first["password"],
    )

    second = register_user(
        client
    )

    second_token = login_user(
        client,
        second["email"],
        second["password"],
    )

    complaint = create_complaint(
        client,
        first_token,
    )

    complaint_id = complaint[
        "id"
    ]

    response = client.post(
        (
            f"/api/v1/complaints/"
            f"{complaint_id}/generate"
        ),
        headers=auth_headers(
            second_token
        ),
        json={
            "regenerate":
                False
        },
    )

    assert response.status_code == 404, (
        response.text
    )

    # Important:
    # another user's complaint must be rejected
    # BEFORE the generation pipeline executes.
    assert (
        generator_called[
            "value"
        ]
        is False
    )


def test_low_confidence_generation_rejected(
    client,
    monkeypatch,
):
    async def low_confidence_generator(
        complaint,
        top_k=5,
    ):
        return {
            "generated":
                False,

            "reason":
                "low_relevance",

            "generated_text":
                None,

            "sources":
                [],

            "confidence": {
                "accepted":
                    False,

                "reason":
                    "low_relevance",

                "top_score":
                    0.40,

                "threshold":
                    0.52,
            },

            "citation_retry_used":
                False,
        }

    monkeypatch.setattr(
        (
            "app.services."
            "complaint_generation_service."
            "generate_grounded_complaint"
        ),
        low_confidence_generator,
    )

    account = register_user(
        client
    )

    token = login_user(
        client,
        account["email"],
        account["password"],
    )

    complaint = create_complaint(
        client,
        token,
    )

    complaint_id = complaint[
        "id"
    ]

    response = client.post(
        (
            f"/api/v1/complaints/"
            f"{complaint_id}/generate"
        ),
        headers=auth_headers(
            token
        ),
        json={
            "regenerate":
                False
        },
    )

    assert response.status_code == 422, (
        response.text
    )

    # -------------------------
    # VERIFY DRAFT UNCHANGED
    # -------------------------

    response = client.get(
        (
            f"/api/v1/complaints/"
            f"{complaint_id}"
        ),
        headers=auth_headers(
            token
        ),
    )

    assert response.status_code == 200

    saved = response.json()

    assert saved[
        "status"
    ] == "draft"

    assert (
        saved[
            "generated_text"
        ]
        is None
    )

    assert saved[
        "sources"
    ] == []


def test_llm_provider_failure_preserves_draft(
    client,
    monkeypatch,
):
    async def failed_generator(
        complaint,
        top_k=5,
    ):
        raise LLMServiceError(
            "Simulated provider failure"
        )

    monkeypatch.setattr(
        (
            "app.services."
            "complaint_generation_service."
            "generate_grounded_complaint"
        ),
        failed_generator,
    )

    account = register_user(
        client
    )

    token = login_user(
        client,
        account["email"],
        account["password"],
    )

    complaint = create_complaint(
        client,
        token,
    )

    complaint_id = complaint[
        "id"
    ]

    response = client.post(
        (
            f"/api/v1/complaints/"
            f"{complaint_id}/generate"
        ),
        headers=auth_headers(
            token
        ),
        json={
            "regenerate":
                False
        },
    )

    assert response.status_code == 503, (
        response.text
    )

    # The API should expose a controlled
    # message, not the provider exception.
    assert (
        "Simulated provider failure"
        not in response.text
    )

    # -------------------------
    # VERIFY DRAFT UNCHANGED
    # -------------------------

    response = client.get(
        (
            f"/api/v1/complaints/"
            f"{complaint_id}"
        ),
        headers=auth_headers(
            token
        ),
    )

    assert response.status_code == 200

    saved = response.json()

    assert saved[
        "status"
    ] == "draft"

    assert (
        saved[
            "generated_text"
        ]
        is None
    )

    assert saved[
        "sources"
    ] == []
    