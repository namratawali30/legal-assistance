import uuid
import zipfile
from io import BytesIO


def unique_email() -> str:
    token = uuid.uuid4().hex[:10]

    return (
        f"complaint-export-"
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
                "Complaint Export Test User",

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
                "Defective product export test",

            "category":
                "consumer_rights",

            "complainant_name":
                "Complaint Export User",

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
                "the respondent. The phone was "
                "defective and the seller refused "
                "to replace it or provide a refund."
            ),

            "relief_requested": (
                "Replacement of the defective "
                "product or refund of the "
                "purchase amount."
            ),

            "additional_details": {
                "invoice_number":
                    "EXPORT-TEST-001",

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
            "Subject: Complaint regarding "
            "defective product\n\n"
            "Respected Sir/Madam,\n\n"
            "I respectfully submit this complaint "
            "concerning the defective mobile phone "
            "supplied by the respondent.\n\n"
            "The relevant consumer complaint "
            "provisions provide a legal basis "
            "for this complaint. [SOURCE_1]\n\n"
            "I request replacement of the "
            "defective product or refund of the "
            "purchase amount.\n\n"
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


async def fake_generator(
    complaint,
    top_k=5,
):
    return fake_generation_result()


def create_finalized_complaint(
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

    assert response.json()[
        "status"
    ] == "generated"

    # -------------------------
    # FINALIZE
    # -------------------------

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

    return finalized


# =========================================================
# AUTHENTICATION
# =========================================================


def test_export_requires_authentication(
    client,
):
    for extension in (
        "pdf",
        "docx",
    ):
        response = client.get(
            (
                "/api/v1/complaints/"
                "000000000000000000000000/"
                f"export/{extension}"
            )
        )

        assert response.status_code in (
            401,
            403,
        )


# =========================================================
# FINALIZED-ONLY RULE
# =========================================================


def test_non_finalized_complaint_cannot_be_exported(
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

    for extension in (
        "pdf",
        "docx",
    ):
        response = client.get(
            (
                f"/api/v1/complaints/"
                f"{complaint_id}/"
                f"export/{extension}"
            ),
            headers=auth_headers(
                token
            ),
        )

        assert response.status_code == 409, (
            response.text
        )

        assert (
            "finalized"
            in response.text.lower()
        )


# =========================================================
# PDF EXPORT
# =========================================================


def test_finalized_complaint_pdf_export(
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

    response = client.get(
        (
            f"/api/v1/complaints/"
            f"{complaint_id}/export/pdf"
        ),
        headers=auth_headers(
            token
        ),
    )

    assert response.status_code == 200, (
        response.text
    )

    # -------------------------
    # CONTENT TYPE
    # -------------------------

    assert (
        response.headers[
            "content-type"
        ].startswith(
            "application/pdf"
        )
    )

    # -------------------------
    # REAL PDF SIGNATURE
    # -------------------------

    assert response.content.startswith(
        b"%PDF"
    )

    assert len(
        response.content
    ) > 500

    # -------------------------
    # DOWNLOAD HEADER
    # -------------------------

    disposition = response.headers.get(
        "content-disposition",
        "",
    )

    assert "attachment" in (
        disposition.lower()
    )

    assert ".pdf" in (
        disposition.lower()
    )

    assert complaint_id in (
        disposition
    )

    # -------------------------
    # SECURITY HEADERS
    # -------------------------

    cache_control = (
        response.headers.get(
            "cache-control",
            "",
        ).lower()
    )

    assert "no-store" in cache_control
    assert "private" in cache_control

    assert (
        response.headers.get(
            "pragma"
        )
        == "no-cache"
    )

    assert (
        response.headers.get(
            "x-content-type-options"
        )
        == "nosniff"
    )



# DOCX EXPORT

def test_finalized_complaint_docx_export(
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

    response = client.get(
        (
            f"/api/v1/complaints/"
            f"{complaint_id}/export/docx"
        ),
        headers=auth_headers(
            token
        ),
    )

    assert response.status_code == 200, (
        response.text
    )

    expected_content_type = (
        "application/"
        "vnd.openxmlformats-officedocument."
        "wordprocessingml.document"
    )

    assert (
        expected_content_type
        in response.headers[
            "content-type"
        ]
    )

    # DOCX is a ZIP-based OOXML format.
    assert response.content.startswith(
        b"PK"
    )

    assert len(
        response.content
    ) > 1000

    
    # VERIFY REAL DOCX CONTENT
    

    docx_buffer = BytesIO(
        response.content
    )

    assert zipfile.is_zipfile(
        docx_buffer
    )

    docx_buffer.seek(
        0
    )

    with zipfile.ZipFile(
        docx_buffer
    ) as archive:
        filenames = archive.namelist()

        assert (
            "word/document.xml"
            in filenames
        )

        assert (
            "[Content_Types].xml"
            in filenames
        )

    
    # DOWNLOAD HEADER
    

    disposition = response.headers.get(
        "content-disposition",
        "",
    )

    assert "attachment" in (
        disposition.lower()
    )

    assert ".docx" in (
        disposition.lower()
    )

    assert complaint_id in (
        disposition
    )

    
    # SECURITY HEADERS
    

    cache_control = (
        response.headers.get(
            "cache-control",
            "",
        ).lower()
    )

    assert "no-store" in cache_control
    assert "private" in cache_control

    assert (
        response.headers.get(
            "pragma"
        )
        == "no-cache"
    )

    assert (
        response.headers.get(
            "x-content-type-options"
        )
        == "nosniff"
    )


# OWNERSHIP


def test_export_ownership_isolation(
    client,
    monkeypatch,
):
    first_token = (
        create_account_and_token(
            client
        )
    )

    second_token = (
        create_account_and_token(
            client
        )
    )

    complaint = create_finalized_complaint(
        client,
        first_token,
        monkeypatch,
    )

    complaint_id = complaint[
        "id"
    ]

    for extension in (
        "pdf",
        "docx",
    ):
        response = client.get(
            (
                f"/api/v1/complaints/"
                f"{complaint_id}/"
                f"export/{extension}"
            ),
            headers=auth_headers(
                second_token
            ),
        )

        # Do not reveal that another
        # user's complaint exists.
        assert response.status_code == 404

# INVALID IDS

def test_export_invalid_complaint_id(
    client,
):
    token = create_account_and_token(
        client
    )

    for extension in (
        "pdf",
        "docx",
    ):
        response = client.get(
            (
                "/api/v1/complaints/"
                "not-a-valid-object-id/"
                f"export/{extension}"
            ),
            headers=auth_headers(
                token
            ),
        )

        assert response.status_code == 404