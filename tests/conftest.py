import os
# Nastavení testovací SQLite databáze před inicializací nastavení
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
# Nízká cena bcryptu – hashování v testech trvá ~1 ms místo ~200 ms
os.environ["BCRYPT_ROUNDS"] = "4"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.main import app
from src.infrastructure.database import Base, get_db
from src.infrastructure.models.user_model import UserModel, UserRole
from src.business.seed import seed_initial_users, seed_doctors, seed_procedures

# In-memory SQLite databáze pro rychlé a izolované testy
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"


test_engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session():
    """Vytvoří novou čistou databázi pro každý test."""
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    seed_initial_users(session)
    seed_doctors(session)
    seed_procedures(session)
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Testovací HTTP klient s přepsanou databázovou závislostí."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def admin_token(client):
    """Získá platný JWT token pro výchozího administrátora."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "Admin123!"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def receptionist_token(client):
    """Získá platný JWT token pro recepční Věru."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "vera", "password": "Vera123!"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def doctor_token(client):
    """Získá platný JWT token pro MUDr. Janu Hrubou."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "hruba", "password": "Hruba123!"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def doctor2_token(client):
    """Získá platný JWT token pro MUDr. Tomáše Malého."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "maly", "password": "Maly123!"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def doctors_by_username(client, admin_token):
    """Mapa uživatelské jméno lékaře -> profil lékaře (z API)."""
    response = client.get(
        "/api/v1/doctors", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    names = {"MUDr. Jana Hrubá": "hruba", "MUDr. Tomáš Malý": "maly", "MUDr. Lucie Veselá": "vesela"}
    return {names[d["full_name"]]: d for d in response.json()}
