import uuid


def unique_email() -> str:
    token = uuid.uuid4().hex[
        :10
    ]

    return (
        f"complaint-test-"
        f"{token}@example.com"
    )


def register_user(
    client,
):
    email = unique_email()

    payload = {
        "full_name":
            "Complaint Test User",

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


def create_test_complaint(
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
                "I purchased a mobile phone "
                "from the seller. The product "
                "was defective and the seller "
                "refused to replace or refund it."
            ),

            "relief_requested": (
                "Replacement of the defective "
                "product or refund of the "
                "purchase amount."
            ),

            "additional_details": {
                "product_name":
                    "Mobile phone",

                "invoice_number":
                    "TEST-INV-001",

                "purchase_amount":
                    25000,
            },
        },
    )

    assert response.status_code == 201, (
        response.text
    )

    return response.json()


def test_complaint_requires_auth(
    client,
):
    response = client.get(
        "/api/v1/complaints"
    )

    assert response.status_code in (
        401,
        403,
    )


def test_complaint_crud(
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

    headers = auth_headers(
        token
    )

    # -------------------------
    # CREATE
    # -------------------------

    complaint = (
        create_test_complaint(
            client,
            token,
        )
    )

    complaint_id = complaint[
        "id"
    ]

    assert complaint_id

    assert complaint[
        "status"
    ] == "draft"

    assert (
        complaint[
            "generated_text"
        ]
        is None
    )

    assert complaint[
        "sources"
    ] == []

    assert complaint[
        "category"
    ] == "consumer_rights"

    assert complaint[
        "incident_date"
    ] == "2026-08-01"

    # -------------------------
    # LIST
    # -------------------------

    response = client.get(
        "/api/v1/complaints",
        headers=headers,
    )

    assert response.status_code == 200, (
        response.text
    )

    complaints = response.json()

    assert any(
        item["id"]
        == complaint_id

        for item in complaints
    )

    # -------------------------
    # GET
    # -------------------------

    response = client.get(
        (
            f"/api/v1/complaints/"
            f"{complaint_id}"
        ),
        headers=headers,
    )

    assert response.status_code == 200, (
        response.text
    )

    fetched = response.json()

    assert fetched[
        "id"
    ] == complaint_id

    # -------------------------
    # UPDATE
    # -------------------------

    response = client.patch(
        (
            f"/api/v1/complaints/"
            f"{complaint_id}"
        ),
        headers=headers,
        json={
            "title": (
                "Updated defective product complaint"
            ),

            "relief_requested": (
                "Full refund of the "
                "purchase amount."
            ),
        },
    )

    assert response.status_code == 200, (
        response.text
    )

    updated = response.json()

    assert updated[
        "title"
    ] == (
        "Updated defective product complaint"
    )

    assert updated[
        "relief_requested"
    ] == (
        "Full refund of the purchase amount."
    )

    # Draft should remain a draft.
    assert updated[
        "status"
    ] == "draft"

    # -------------------------
    # DELETE
    # -------------------------

    response = client.delete(
        (
            f"/api/v1/complaints/"
            f"{complaint_id}"
        ),
        headers=headers,
    )

    assert response.status_code == 204, (
        response.text
    )

    # -------------------------
    # VERIFY DELETE
    # -------------------------

    response = client.get(
        (
            f"/api/v1/complaints/"
            f"{complaint_id}"
        ),
        headers=headers,
    )

    assert response.status_code == 404


def test_complaint_ownership_isolation(
    client,
):
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

    complaint = (
        create_test_complaint(
            client,
            first_token,
        )
    )

    complaint_id = complaint[
        "id"
    ]

    second_headers = auth_headers(
        second_token
    )

    # -------------------------
    # SECOND USER CANNOT GET
    # -------------------------

    response = client.get(
        (
            f"/api/v1/complaints/"
            f"{complaint_id}"
        ),
        headers=second_headers,
    )

    assert response.status_code == 404

    # -------------------------
    # SECOND USER CANNOT UPDATE
    # -------------------------

    response = client.patch(
        (
            f"/api/v1/complaints/"
            f"{complaint_id}"
        ),
        headers=second_headers,
        json={
            "title":
                "Unauthorized update"
        },
    )

    assert response.status_code == 404

    # -------------------------
    # SECOND USER CANNOT DELETE
    # -------------------------

    response = client.delete(
        (
            f"/api/v1/complaints/"
            f"{complaint_id}"
        ),
        headers=second_headers,
    )

    assert response.status_code == 404

    # -------------------------
    # OWNER STILL HAS COMPLAINT
    # -------------------------

    response = client.get(
        (
            f"/api/v1/complaints/"
            f"{complaint_id}"
        ),
        headers=auth_headers(
            first_token
        ),
    )

    assert response.status_code == 200


def test_invalid_complaint_id(
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

    response = client.get(
        (
            "/api/v1/complaints/"
            "this-is-not-an-object-id"
        ),
        headers=auth_headers(
            token
        ),
    )

    assert response.status_code == 404