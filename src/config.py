import secrets
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Ordinace Na Vyhlídce"
    VERSION: str = "0.1.0-demo"
    API_V1_PREFIX: str = "/api/v1"
    
    # Údaje ordinace pro hlavičku výkazů pojišťovnám (syntetické hodnoty pro demo)
    PRACTICE_NAME: str = "Ordinace Na Vyhlídce s.r.o."
    PRACTICE_ADDRESS: str = "Na Vyhlídce 12, 500 03 Hradec Králové"
    PRACTICE_ICZ: str = "52999000"

    # Databáze
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/ordinace_db"
    
    # Bezpečnost a JWT
    # Tajný klíč pro podpis JWT se do gitu neukládá: lze ho dodat proměnnou prostředí / .env,
    # jinak se při startu vygeneruje náhodný (po restartu je nutné se znovu přihlásit).
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8  # 8 hodin pro pracovní směnu
    # Cena bcrypt hashování (v testech se snižuje kvůli rychlosti, min. 4)
    BCRYPT_ROUNDS: int = 12
    
    # Výchozí administrátor
    FIRST_ADMIN_USERNAME: str = "admin"
    FIRST_ADMIN_PASSWORD: str = "Admin123!"
    FIRST_ADMIN_EMAIL: str = "admin@ordinacenavyhlidce.cz"
    FIRST_ADMIN_FULL_NAME: str = "Administrátor Systému"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
if not settings.SECRET_KEY:
    settings.SECRET_KEY = secrets.token_urlsafe(48)
