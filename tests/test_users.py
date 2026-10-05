def test_list_users(client, admin_token):
    """Ověření výpisu uživatelů včetně předvyplněných seed dat."""
    response = client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 3
    usernames = [u["username"] for u in data["items"]]
    assert "admin" in usernames
    assert "vera" in usernames
    assert "hruba" in usernames


def test_create_user_success(client, admin_token):
    """Ověření vytvoření nového uživatele administrátorem."""
    new_user_data = {
        "username": "novak",
        "email": "novak@ordinace.cz",
        "full_name": "MUDr. Karel Novák",
        "password": "HesloNovak123",
        "role": "DOCTOR",
        "is_active": True,
    }
    response = client.post(
        "/api/v1/users",
        json=new_user_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "novak"
    assert data["role"] == "DOCTOR"
    assert "id" in data


def test_create_user_duplicate_username(client, admin_token):
    """Ověření zamítnutí duplicitního uživatelského jména."""
    duplicate_data = {
        "username": "admin",
        "email": "jiny.email@ordinace.cz",
        "full_name": "Další Admin",
        "password": "Heslo123456",
        "role": "ADMIN",
        "is_active": True,
    }
    response = client.post(
        "/api/v1/users",
        json=duplicate_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 400
    assert "již obsazeno" in response.json()["detail"]


def test_create_user_forbidden_for_non_admin(client, receptionist_token):
    """Ověření, že recepční nemůže vytvářet nové uživatele (RBAC)."""
    new_user_data = {
        "username": "hacker",
        "email": "hacker@test.cz",
        "full_name": "Neoprávněný Pokus",
        "password": "Heslo123456",
        "role": "ADMIN",
        "is_active": True,
    }
    response = client.post(
        "/api/v1/users",
        json=new_user_data,
        headers={"Authorization": f"Bearer {receptionist_token}"}
    )
    assert response.status_code == 403


def test_update_user(client, admin_token):
    """Ověření úpravy údajů uživatele."""
    # Nejprve zjistíme ID uživatele vera
    list_res = client.get("/api/v1/users?search=vera", headers={"Authorization": f"Bearer {admin_token}"})
    vera_id = list_res.json()["items"][0]["id"]

    update_payload = {
        "full_name": "Věra Nováková (Hlavní recepční)",
        "is_active": True,
    }
    response = client.put(
        f"/api/v1/users/{vera_id}",
        json=update_payload,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert response.json()["full_name"] == "Věra Nováková (Hlavní recepční)"


def test_delete_user(client, admin_token):
    """Ověření smazání uživatele."""
    # Vytvoříme uživatele pro smazání
    res = client.post(
        "/api/v1/users",
        json={
            "username": "tosmazat",
            "email": "tosmazat@ordinace.cz",
            "full_name": "Uživatel Ke Smazání",
            "password": "Heslo123456",
            "role": "RECEPTIONIST",
            "is_active": True,
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    user_id = res.json()["id"]

    delete_res = client.delete(
        f"/api/v1/users/{user_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert delete_res.status_code == 204

    # Ověříme, že uživatel již neexistuje
    get_res = client.get(
        f"/api/v1/users/{user_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert get_res.status_code == 404


def test_cannot_delete_last_admin(client, admin_token):
    """Byznys pravidlo: Posledního aktivního administrátora nelze smazat."""
    list_res = client.get("/api/v1/users?role=ADMIN", headers={"Authorization": f"Bearer {admin_token}"})
    admin_id = list_res.json()["items"][0]["id"]

    response = client.delete(
        f"/api/v1/users/{admin_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 400
    assert "posledního aktivního administrátora" in response.json()["detail"]
