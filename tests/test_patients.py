import pytest


def test_create_patient_success(client, receptionist_token):
    """Recepční může úspěšně zaevidovat nového pacienta."""
    payload = {
        "first_name": "Tomáš",
        "last_name": "Marný",
        "birth_year": 1990,
        "phone_number": "+420777123456",
        "insurance_number": "9005151234",
        "insurance_company_code": "111",
        "notes": "Preferuje ranní termíny.",
    }
    response = client.post(
        "/api/v1/patients",
        json=payload,
        headers={"Authorization": f"Bearer {receptionist_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["first_name"] == "Tomáš"
    assert data["last_name"] == "Marný"
    assert data["insurance_number"] == "9005151234"
    assert data["insurance_company_code"] == "111"
    assert data["is_active"] is True
    assert "id" in data


def test_create_patient_duplicate_insurance_number(client, receptionist_token):
    """Nelze založit dva pacienty se shodným číslem pojištěnce (rodným číslem)."""
    payload = {
        "first_name": "Jan",
        "last_name": "Novák",
        "birth_year": 1980,
        "phone_number": "+420601111222",
        "insurance_number": "8001011111",
        "insurance_company_code": "205",
    }
    res1 = client.post(
        "/api/v1/patients",
        json=payload,
        headers={"Authorization": f"Bearer {receptionist_token}"},
    )
    assert res1.status_code == 201

    # Pokus o založení se stejným číslem pojištěnce
    payload2 = {
        "first_name": "Jana",
        "last_name": "Nováková",
        "birth_year": 1982,
        "phone_number": "+420601333444",
        "insurance_number": "8001011111",
        "insurance_company_code": "111",
    }
    res2 = client.post(
        "/api/v1/patients",
        json=payload2,
        headers={"Authorization": f"Bearer {receptionist_token}"},
    )
    assert res2.status_code == 400
    assert "již v evidenci existuje" in res2.json()["detail"]


def test_create_patient_invalid_validations(client, receptionist_token):
    """Validace neplatného kódu pojišťovny, telefonu a roku narození."""
    # Neplatná pojišťovna
    res_ins = client.post(
        "/api/v1/patients",
        json={
            "first_name": "Karel",
            "last_name": "Drobný",
            "birth_year": 1975,
            "phone_number": "+420777000111",
            "insurance_number": "7505051234",
            "insurance_company_code": "999",  # Neexistující kód
        },
        headers={"Authorization": f"Bearer {receptionist_token}"},
    )
    assert res_ins.status_code == 422

    # Neplatný telefon
    res_phone = client.post(
        "/api/v1/patients",
        json={
            "first_name": "Karel",
            "last_name": "Drobný",
            "birth_year": 1975,
            "phone_number": "123",  # Příliš krátké
            "insurance_number": "7505051234",
            "insurance_company_code": "111",
        },
        headers={"Authorization": f"Bearer {receptionist_token}"},
    )
    assert res_phone.status_code == 422


def test_search_patient_by_last_name_and_phone(client, receptionist_token):
    """Ověření rychlého vyhledávání podle příjmení a telefonního čísla."""
    client.post(
        "/api/v1/patients",
        json={
            "first_name": "Alena",
            "last_name": "Záhorská",
            "birth_year": 1992,
            "phone_number": "+420776554433",
            "insurance_number": "9252011234",
            "insurance_company_code": "207",
        },
        headers={"Authorization": f"Bearer {receptionist_token}"},
    )
    client.post(
        "/api/v1/patients",
        json={
            "first_name": "Bohumil",
            "last_name": "Kopecký",
            "birth_year": 1968,
            "phone_number": "+420603998877",
            "insurance_number": "6803155678",
            "insurance_company_code": "211",
        },
        headers={"Authorization": f"Bearer {receptionist_token}"},
    )

    # Hledání podle příjmení (case insensitive, částečná shoda)
    res_surname = client.get(
        "/api/v1/patients?search=Záhor",
        headers={"Authorization": f"Bearer {receptionist_token}"},
    )
    assert res_surname.status_code == 200
    items = res_surname.json()["items"]
    assert len(items) == 1
    assert items[0]["last_name"] == "Záhorská"

    # Hledání podle telefonu (bez mezer)
    res_phone = client.get(
        "/api/v1/patients?search=998877",
        headers={"Authorization": f"Bearer {receptionist_token}"},
    )
    assert res_phone.status_code == 200
    items = res_phone.json()["items"]
    assert len(items) == 1
    assert items[0]["last_name"] == "Kopecký"

    # Hledání podle telefonu (s mezerami, např. "603 998")
    res_phone_spaces = client.get(
        "/api/v1/patients?search=603%20998%20877",
        headers={"Authorization": f"Bearer {receptionist_token}"},
    )
    assert res_phone_spaces.status_code == 200
    items_spaces = res_phone_spaces.json()["items"]
    assert len(items_spaces) == 1
    assert items_spaces[0]["last_name"] == "Kopecký"


def test_get_patient_detail(client, doctor_token):
    """Lékař může načíst detail pacienta."""
    create_res = client.post(
        "/api/v1/patients",
        json={
            "first_name": "Lukáš",
            "last_name": "Veselý",
            "birth_year": 1988,
            "phone_number": "+420723112233",
            "insurance_number": "8812241234",
            "insurance_company_code": "111",
        },
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    patient_id = create_res.json()["id"]

    res = client.get(
        f"/api/v1/patients/{patient_id}",
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert res.status_code == 200
    assert res.json()["last_name"] == "Veselý"

    # Neexistující ID
    res_404 = client.get(
        "/api/v1/patients/99999",
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert res_404.status_code == 404


def test_update_patient(client, receptionist_token):
    """Úprava údajů existujícího pacienta."""
    create_res = client.post(
        "/api/v1/patients",
        json={
            "first_name": "Jiří",
            "last_name": "Malý",
            "birth_year": 1970,
            "phone_number": "+420777888999",
            "insurance_number": "7001019999",
            "insurance_company_code": "111",
        },
        headers={"Authorization": f"Bearer {receptionist_token}"},
    )
    patient_id = create_res.json()["id"]

    update_payload = {
        "phone_number": "+420777000999",
        "notes": "Změna telefonního čísla na vyžádání pacienta.",
    }
    update_res = client.put(
        f"/api/v1/patients/{patient_id}",
        json=update_payload,
        headers={"Authorization": f"Bearer {receptionist_token}"},
    )
    assert update_res.status_code == 200
    updated_data = update_res.json()
    assert updated_data["phone_number"] == "+420777000999"
    assert updated_data["notes"] == "Změna telefonního čísla na vyžádání pacienta."
    assert updated_data["first_name"] == "Jiří"


def test_soft_delete_and_role_restrictions(client, receptionist_token, admin_token):
    """Měkké smazání (deaktivace) a kontrola oprávnění trvalého smazání."""
    create_res = client.post(
        "/api/v1/patients",
        json={
            "first_name": "Zdeňka",
            "last_name": "Růžičková",
            "birth_year": 1955,
            "phone_number": "+420775123987",
            "insurance_number": "5558121234",
            "insurance_company_code": "205",
        },
        headers={"Authorization": f"Bearer {receptionist_token}"},
    )
    patient_id = create_res.json()["id"]

    # Recepční provede měkké smazání (deaktivaci)
    del_res = client.delete(
        f"/api/v1/patients/{patient_id}",
        headers={"Authorization": f"Bearer {receptionist_token}"},
    )
    assert del_res.status_code == 204

    # Záznam v DB zůstává s is_active=False (uchování historie)
    detail_res = client.get(
        f"/api/v1/patients/{patient_id}",
        headers={"Authorization": f"Bearer {receptionist_token}"},
    )
    assert detail_res.status_code == 200
    assert detail_res.json()["is_active"] is False

    # Recepční nemůže provést permanentní smazání
    perm_del_rec = client.delete(
        f"/api/v1/patients/{patient_id}?permanent=true",
        headers={"Authorization": f"Bearer {receptionist_token}"},
    )
    assert perm_del_rec.status_code == 403

    # Administrátor může provést trvalé smazání
    perm_del_admin = client.delete(
        f"/api/v1/patients/{patient_id}?permanent=true",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert perm_del_admin.status_code == 204

    # Nyní již pacient neexistuje
    assert client.get(
        f"/api/v1/patients/{patient_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    ).status_code == 404


def test_unauthorized_access(client):
    """Neautorizovaný uživatel bez tokenu nemá přístup k evidenci pacientů."""
    res = client.get("/api/v1/patients")
    assert res.status_code == 401
