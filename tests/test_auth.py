def test_login_success(client):
    """Ověření úspěšného přihlášení a návratu JWT tokenu."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "Admin123!"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "admin"
    assert data["user"]["role"] == "ADMIN"


def test_login_invalid_password(client):
    """Ověření zamítnutí při chybném heslu."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "SpatneHeslo123"}
    )
    assert response.status_code == 401
    assert "Nesprávné uživatelské jméno" in response.json()["detail"]


def test_login_nonexistent_user(client):
    """Ověření zamítnutí pro neexistujícího uživatele."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "neexistuje", "password": "Password123"}
    )
    assert response.status_code == 401


def test_get_current_user_me(client, admin_token):
    """Ověření získání profilu přihlášeného uživatele."""
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "admin"
    assert data["role"] == "ADMIN"


def test_get_current_user_unauthorized(client):
    """Ověření ochrany endpointu bez platného tokenu."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
