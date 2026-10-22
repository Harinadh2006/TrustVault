
def test_register_user(client):
    response = client.post(
        "/auth/register",
        json={
            "email": "testuser@example.com",
            "full_name": "Test User",
            "password": "SecureTestPass123!",
        },
    )

    assert response.status_code in (200, 201)
    assert response.json()["email"] == "testuser@example.com"


def test_login_user(client):
    client.post(
        "/auth/register",
        json={
            "email": "loginuser@example.com",
            "full_name": "Login User",
            "password": "SecureTestPass123!",
        },
    )

    response = client.post(
        "/auth/login",
        json={
            "email": "loginuser@example.com",
            "password": "SecureTestPass123!",
        },
    )

    assert response.status_code == 200
    assert response.json()["token_type"].lower() == "bearer"
    assert response.json()["access_token"]


def test_documents_require_authentication(client):
    response = client.get("/documents")

    assert response.status_code == 401
