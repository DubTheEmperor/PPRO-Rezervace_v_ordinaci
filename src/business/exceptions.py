"""Doménové výjimky byznys vrstvy.

Byznys vrstva nezná HTTP – vyhazuje tyto výjimky a prezentační vrstva je
převádí na odpovídající HTTP odpovědi (viz src/presentation/error_handlers.py).
"""


class DomainError(Exception):
    """Společný předek všech doménových chyb. `message` je text pro uživatele."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    """Požadovaný záznam neexistuje."""


class BusinessRuleError(DomainError):
    """Požadavek porušuje obchodní pravidlo nebo validaci (např. mimo ordinační hodiny)."""


class ConflictError(DomainError):
    """Požadavek koliduje s existujícím stavem (např. překryv termínů)."""


class PermissionDeniedError(DomainError):
    """Uživatel nemá oprávnění k akci."""


class AuthenticationError(DomainError):
    """Neplatné přihlašovací údaje nebo token."""


class AccountDisabledError(DomainError):
    """Uživatelský účet je deaktivován."""
