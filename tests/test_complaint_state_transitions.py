import uuid


def unique_email() -> str:
    token = uuid.uuid4().hex[:10]

    return (
        f"complaint-state-"
        f"{token}@example.com"
    )


def register_user(
    client,
):
    email = unique_email()

    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name":
                "Complaint State Test User",

            "email":
                email,

            "password":
                "TestPassword123!",
        },
    )

    assert response.status_code in (
        200,
        201,
    ), response.text

    return {
        "email":
            email,

        "password":
            "TestPassword123!",
    }


def login_user(
    client,
    email: str,
    password: str,
) -> str:
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

    assert token

    return token


def auth_headers(
    token: str,
) -> dict[str, str]:
    return {
        "Authorization":
            f"Bearer {token}"
    }


def create_draft_complaint(
    client,
    token: str,
):
    response = client.post(
        "/api/v1/complaints",
        headers=auth_headers(
            token
        ),
        json={
            "title":
                "Defective product complaint",

            "category":
                "consumer_rights",

            "complainant_name":
                "Complaint State User",

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
                "I purchased a mobile phone "
                "from the respondent. The phone "
                "was defective and the seller "
                "refused to replace it or provide "
                "a refund."
            ),

            "relief_requested": (
                "Replacement of the defective "
                "product or refund of the "
                "purchase amount."
            ),

            "additional_details": {
                "invoice_number":
                    "STATE-TEST-001",

                "purchase_amount":
                    25000,
            },
        },
    )

    assert response.status_code == 201, (
        response.text
    )

    return response.json()


def fake_generation_result():
    return {
        "generated":
            True,

        "reason":
            "success",

        "generated_text": (
            "To,\n"
            "[Appropriate Authority]\n\n"
            "Subject: Consumer complaint\n\n"
            "Respected Sir/Madam,\n\n"
            "I respectfully submit this complaint "
            "concerning a defective product supplied "
            "by the respondent.\n\n"
            "The relevant consumer complaint "
            "provisions provide a legal basis for "
            "this complaint. [SOURCE_1]\n\n"
            "I request appropriate relief.\n\n"
            "Drafting note: This AI-generated draft "
            "is for general informational assistance "
            "and should be reviewed before submission."
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


async def fake_generator(
    complaint,
    top_k=5,
):
    return fake_generation_result()


def create_generated_complaint(
    client,
    token: str,
    monkeypatch,
):
    monkeypatch.setattr(
        (
            "app.services."
            "complaint_generation_service."
            "generate_grounded_complaint"
        ),
        fake_generator,
    )

    draft = create_draft_complaint(
        client,
        token,
    )

    complaint_id = draft[
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

    assert response.status_code == 200, (
        response.text
    )

    generated = response.json()

    assert generated[
        "status"
    ] == "generated"

    return generated


def create_account_and_token(
    client,
):
    account = register_user(
        client
    )

    token = login_user(
        client,
        account["email"],
        account["password"],
    )

    return token


# =========================================================
# DRAFT STATE
# =========================================================


def test_draft_structured_edit_stays_draft(
    client,
):
    token = create_account_and_token(
        client
    )

    complaint = create_draft_complaint(
        client,
        token,
    )

    complaint_id = complaint[
        "id"
    ]

    response = client.patch(
        (
            f"/api/v1/complaints/"
            f"{complaint_id}"
        ),
        headers=auth_headers(
            token
        ),
        json={
            "relief_requested": (
                "I request a full refund of "
                "the purchase amount."
            )
        },
    )

    assert response.status_code == 200, (
        response.text
    )

    updated = response.json()

    assert updated[
        "status"
    ] == "draft"

    assert updated[
        "relief_requested"
    ] == (
        "I request a full refund of "
        "the purchase amount."
    )


def test_draft_generated_text_edit_rejected(
    client,
):
    token = create_account_and_token(
        client
    )

    complaint = create_draft_complaint(
        client,
        token,
    )

    complaint_id = complaint[
        "id"
    ]

    response = client.patch(
        (
            f"/api/v1/complaints/"
            f"{complaint_id}/generated-text"
        ),
        headers=auth_headers(
            token
        ),
        json={
            "generated_text": (
                "This text should not be accepted "
                "because no generated complaint "
                "exists yet."
            )
        },
    )

    assert response.status_code == 409, (
        response.text
    )


def test_draft_finalization_rejected(
    client,
):
    token = create_account_and_token(
        client
    )

    complaint = create_draft_complaint(
        client,
        token,
    )

    complaint_id = complaint[
        "id"
    ]

    response = client.post(
        (
            f"/api/v1/complaints/"
            f"{complaint_id}/finalize"
        ),
        headers=auth_headers(
            token
        ),
        json={
            "confirm":
                True
        },
    )

    assert response.status_code == 409, (
        response.text
    )


# =========================================================
# GENERATED → EDITED
# =========================================================


def test_generated_text_edit_changes_status_to_edited(
    client,
    monkeypatch,
):
    token = create_account_and_token(
        client
    )

    complaint = create_generated_complaint(
        client,
        token,
        monkeypatch,
    )

    complaint_id = complaint[
        "id"
    ]

    edited_text = (
        "To,\n"
        "[Appropriate Authority]\n\n"
        "Subject: Edited consumer complaint\n\n"
        "Respected Sir/Madam,\n\n"
        "I respectfully submit this edited "
        "complaint concerning the defective "
        "product supplied by the respondent.\n\n"
        "The relevant legal provisions support "
        "the complaint process. [SOURCE_1]\n\n"
        "I request appropriate relief.\n\n"
        "Drafting note: This AI-generated draft "
        "is for general informational assistance "
        "and should be reviewed before submission."
    )

    response = client.patch(
        (
            f"/api/v1/complaints/"
            f"{complaint_id}/generated-text"
        ),
        headers=auth_headers(
            token
        ),
        json={
            "generated_text":
                edited_text
        },
    )

    assert response.status_code == 200, (
        response.text
    )

    updated = response.json()

    assert updated[
        "status"
    ] == "edited"

    assert updated[
        "generated_text"
    ] == edited_text

    assert len(
        updated["sources"]
    ) == 1


def test_structured_edit_after_generation_marks_edited(
    client,
    monkeypatch,
):
    token = create_account_and_token(
        client
    )

    complaint = create_generated_complaint(
        client,
        token,
        monkeypatch,
    )

    complaint_id = complaint[
        "id"
    ]

    response = client.patch(
        (
            f"/api/v1/complaints/"
            f"{complaint_id}"
        ),
        headers=auth_headers(
            token
        ),
        json={
            "incident_location":
                "Updated Test City"
        },
    )

    assert response.status_code == 200, (
        response.text
    )

    updated = response.json()

    assert updated[
        "status"
    ] == "edited"

    assert updated[
        "incident_location"
    ] == "Updated Test City"


# =========================================================
# CITATION INTEGRITY
# =========================================================


def test_unknown_citation_in_edit_rejected(
    client,
    monkeypatch,
):
    token = create_account_and_token(
        client
    )

    complaint = create_generated_complaint(
        client,
        token,
        monkeypatch,
    )

    complaint_id = complaint[
        "id"
    ]

    response = client.patch(
        (
            f"/api/v1/complaints/"
            f"{complaint_id}/generated-text"
        ),
        headers=auth_headers(
            token
        ),
        json={
            "generated_text": (
                "This edited complaint attempts "
                "to rely upon an unknown source. "
                "[SOURCE_999] This citation was "
                "never attached to the complaint."
            )
        },
    )

    assert response.status_code == 400, (
        response.text
    )

    # Verify the stored generated complaint
    # was not overwritten.
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

    assert (
        "[SOURCE_999]"
        not in saved[
            "generated_text"
        ]
    )

    assert saved[
        "status"
    ] == "generated"


# =========================================================
# FINALIZATION
# =========================================================


def test_finalize_requires_explicit_confirmation(
    client,
    monkeypatch,
):
    token = create_account_and_token(
        client
    )

    complaint = create_generated_complaint(
        client,
        token,
        monkeypatch,
    )

    complaint_id = complaint[
        "id"
    ]

    response = client.post(
        (
            f"/api/v1/complaints/"
            f"{complaint_id}/finalize"
        ),
        headers=auth_headers(
            token
        ),
        json={
            "confirm":
                False
        },
    )

    assert response.status_code == 409, (
        response.text
    )

    response = client.get(
        (
            f"/api/v1/complaints/"
            f"{complaint_id}"
        ),
        headers=auth_headers(
            token
        ),
    )

    saved = response.json()

    assert saved[
        "status"
    ] == "generated"

    assert saved[
        "finalized_at"
    ] is None


def test_generated_complaint_can_be_finalized(
    client,
    monkeypatch,
):
    token = create_account_and_token(
        client
    )

    complaint = create_generated_complaint(
        client,
        token,
        monkeypatch,
    )

    complaint_id = complaint[
        "id"
    ]

    response = client.post(
        (
            f"/api/v1/complaints/"
            f"{complaint_id}/finalize"
        ),
        headers=auth_headers(
            token
        ),
        json={
            "confirm":
                True
        },
    )

    assert response.status_code == 200, (
        response.text
    )

    finalized = response.json()

    assert finalized[
        "status"
    ] == "finalized"

    assert finalized[
        "finalized_at"
    ] is not None

    assert finalized[
        "generated_text"
    ]

    assert finalized[
        "sources"
    ]


def test_edited_complaint_can_be_finalized(
    client,
    monkeypatch,
):
    token = create_account_and_token(
        client
    )

    complaint = create_generated_complaint(
        client,
        token,
        monkeypatch,
    )

    complaint_id = complaint[
        "id"
    ]

    edit_response = client.patch(
        (
            f"/api/v1/complaints/"
            f"{complaint_id}/generated-text"
        ),
        headers=auth_headers(
            token
        ),
        json={
            "generated_text": (
                "To,\n"
                "[Appropriate Authority]\n\n"
                "Subject: Edited complaint\n\n"
                "Respected Sir/Madam,\n\n"
                "I respectfully submit this "
                "complaint based on the facts "
                "provided above.\n\n"
                "The relevant legal basis is "
                "supported by the authoritative "
                "source. [SOURCE_1]\n\n"
                "I request appropriate relief."
            )
        },
    )

    assert (
        edit_response.status_code
        == 200
    ), edit_response.text

    assert (
        edit_response.json()[
            "status"
        ]
        == "edited"
    )

    finalize_response = client.post(
        (
            f"/api/v1/complaints/"
            f"{complaint_id}/finalize"
        ),
        headers=auth_headers(
            token
        ),
        json={
            "confirm":
                True
        },
    )

    assert (
        finalize_response.status_code
        == 200
    ), finalize_response.text

    assert (
        finalize_response.json()[
            "status"
        ]
        == "finalized"
    )


# =========================================================
# FINALIZED STATE LOCK
# =========================================================


def create_finalized_complaint(
    client,
    token: str,
    monkeypatch,
):
    complaint = create_generated_complaint(
        client,
        token,
        monkeypatch,
    )

    complaint_id = complaint[
        "id"
    ]

    response = client.post(
        (
            f"/api/v1/complaints/"
            f"{complaint_id}/finalize"
        ),
        headers=auth_headers(
            token
        ),
        json={
            "confirm":
                True
        },
    )

    assert response.status_code == 200, (
        response.text
    )

    assert response.json()[
        "status"
    ] == "finalized"

    return response.json()


def test_finalized_complaint_is_immutable(
    client,
    monkeypatch,
):
    token = create_account_and_token(
        client
    )

    complaint = create_finalized_complaint(
        client,
        token,
        monkeypatch,
    )

    complaint_id = complaint[
        "id"
    ]

    headers = auth_headers(
        token
    )

    # -------------------------
    # STRUCTURED EDIT BLOCKED
    # -------------------------

    response = client.patch(
        (
            f"/api/v1/complaints/"
            f"{complaint_id}"
        ),
        headers=headers,
        json={
            "incident_location":
                "Unauthorized Final Edit"
        },
    )

    assert response.status_code == 409, (
        response.text
    )

    # -------------------------
    # GENERATED TEXT EDIT BLOCKED
    # -------------------------

    response = client.patch(
        (
            f"/api/v1/complaints/"
            f"{complaint_id}/generated-text"
        ),
        headers=headers,
        json={
            "generated_text": (
                "This finalized complaint "
                "must not be editable anymore. "
                "[SOURCE_1]"
            )
        },
    )

    assert response.status_code == 409, (
        response.text
    )

    # -------------------------
    # REGENERATION BLOCKED
    # -------------------------

    response = client.post(
        (
            f"/api/v1/complaints/"
            f"{complaint_id}/generate"
        ),
        headers=headers,
        json={
            "regenerate":
                True
        },
    )

    assert response.status_code == 409, (
        response.text
    )

    # -------------------------
    # FINALIZE AGAIN BLOCKED
    # -------------------------

    response = client.post(
        (
            f"/api/v1/complaints/"
            f"{complaint_id}/finalize"
        ),
        headers=headers,
        json={
            "confirm":
                True
        },
    )

    assert response.status_code == 409, (
        response.text
    )

    # -------------------------
    # DELETE BLOCKED
    # -------------------------

    response = client.delete(
        (
            f"/api/v1/complaints/"
            f"{complaint_id}"
        ),
        headers=headers,
    )

    assert response.status_code == 409, (
        response.text
    )

    # -------------------------
    # ORIGINAL DATA STILL EXISTS
    # -------------------------

    response = client.get(
        (
            f"/api/v1/complaints/"
            f"{complaint_id}"
        ),
        headers=headers,
    )

    assert response.status_code == 200

    saved = response.json()

    assert saved[
        "status"
    ] == "finalized"

    assert saved[
        "finalized_at"
    ] is not None