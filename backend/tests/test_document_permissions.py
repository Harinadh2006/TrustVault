
def create_user(client, email):
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "full_name": "Test User",
            "password": "SecureTestPass123!",
        },
    )
    assert response.status_code in (200, 201)

    login = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": "SecureTestPass123!",
        },
    )
    assert login.status_code == 200

    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def upload_test_document(client, headers):
    response = client.post(
        "/documents/upload",
        headers=headers,
        files={
            "file": (
                "sample.pdf",
                b"%PDF-1.4\nTrustVault test document\n%%EOF",
                "application/pdf",
            )
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_shared_document_can_be_downloaded_then_revoked(client):
    owner_headers = create_user(client, "owner@example.com")
    viewer_headers = create_user(client, "viewer@example.com")

    document_id = upload_test_document(client, owner_headers)

    # A user without permission must be denied.
    denied = client.get(
        f"/documents/{document_id}/download",
        headers=viewer_headers,
    )
    assert denied.status_code == 403

    # Owner grants read access.
    share = client.post(
        f"/documents/{document_id}/share",
        headers=owner_headers,
        json={
            "email": "viewer@example.com",
            "can_read": True,
            "can_edit": False,
        },
    )
    assert share.status_code == 200
    assert share.json()["can_read"] is True

    # Viewer can now download the document.
    download = client.get(
        f"/documents/{document_id}/download",
        headers=viewer_headers,
    )
    assert download.status_code == 200
    assert download.content.startswith(b"%PDF-1.4")

    # Owner revokes access.
    revoke = client.delete(
        f"/documents/{document_id}/share/2",
        headers=owner_headers,
    )
    assert revoke.status_code == 200

    # The very next request must be denied.
    after_revoke = client.get(
        f"/documents/{document_id}/download",
        headers=viewer_headers,
    )
    assert after_revoke.status_code == 403


def test_non_owner_cannot_share_document(client):
    owner_headers = create_user(client, "owner2@example.com")
    other_headers = create_user(client, "other@example.com")

    document_id = upload_test_document(client, owner_headers)

    response = client.post(
        f"/documents/{document_id}/share",
        headers=other_headers,
        json={
            "email": "owner2@example.com",
            "can_read": True,
            "can_edit": False,
        },
    )

    assert response.status_code == 403
