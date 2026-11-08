"""Session token verification, for both Supabase signing schemes.

Keys are generated locally, so nothing here touches a real Supabase project.
"""

from __future__ import annotations

import time
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from app.core import security
from app.core.config import settings
from app.core.errors import UnauthorizedError

SECRET = "test-secret-that-is-long-enough-for-hs256-signing"
KID = "test-kid"


def _claims(**overrides: object) -> dict:
    now = int(time.time())
    claims = {
        "sub": "user-123",
        "email": "someone@example.com",
        "aud": "authenticated",
        "iat": now,
        "exp": now + 3600,
    }
    claims.update(overrides)
    return claims


@pytest.fixture
def es256_key(monkeypatch: pytest.MonkeyPatch) -> ec.EllipticCurvePrivateKey:
    """A signing key, with the JWKS lookup pointed at its public half."""
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()

    class FakeJwksClient:
        def get_signing_key_from_jwt(self, token: str) -> SimpleNamespace:
            if jwt.get_unverified_header(token).get("kid") != KID:
                raise jwt.PyJWKClientError("Unable to find a signing key that matches")
            return SimpleNamespace(key=public_key)

    monkeypatch.setattr(security, "_jwks_client", lambda: FakeJwksClient())
    return private_key


@pytest.fixture
def jwt_secret(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setattr(settings, "supabase_jwt_secret", SECRET)
    return SECRET


def test_es256_session_token_is_accepted(es256_key: ec.EllipticCurvePrivateKey) -> None:
    """The case that used to fail: a project on JWT signing keys."""
    token = jwt.encode(_claims(), es256_key, algorithm="ES256", headers={"kid": KID})
    assert security._decode(token)["sub"] == "user-123"


def test_es256_token_does_not_need_the_shared_secret(
    es256_key: ec.EllipticCurvePrivateKey, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "supabase_jwt_secret", "")
    token = jwt.encode(_claims(), es256_key, algorithm="ES256", headers={"kid": KID})
    assert security._decode(token)["sub"] == "user-123"


def test_legacy_hs256_token_is_still_accepted(jwt_secret: str) -> None:
    token = jwt.encode(_claims(), jwt_secret, algorithm="HS256")
    assert security._decode(token)["sub"] == "user-123"


def test_token_signed_by_an_unknown_key_is_rejected(es256_key: ec.EllipticCurvePrivateKey) -> None:
    token = jwt.encode(_claims(), es256_key, algorithm="ES256", headers={"kid": "someone-else"})
    with pytest.raises(UnauthorizedError) as exc:
        security._decode(token)
    assert exc.value.code == "invalid_token"


def test_token_signed_by_a_different_private_key_is_rejected(
    es256_key: ec.EllipticCurvePrivateKey,
) -> None:
    """Same kid, wrong key: the signature check is what actually protects us."""
    forger = ec.generate_private_key(ec.SECP256R1())
    token = jwt.encode(_claims(), forger, algorithm="ES256", headers={"kid": KID})
    with pytest.raises(UnauthorizedError):
        security._decode(token)


def test_expired_token_says_so(es256_key: ec.EllipticCurvePrivateKey) -> None:
    token = jwt.encode(
        _claims(exp=int(time.time()) - 60), es256_key, algorithm="ES256", headers={"kid": KID}
    )
    with pytest.raises(UnauthorizedError) as exc:
        security._decode(token)
    assert exc.value.code == "token_expired"


def test_wrong_audience_is_rejected(jwt_secret: str) -> None:
    # The anon key is a valid HS256 token too, but it is not a user session.
    token = jwt.encode(_claims(aud="anon"), jwt_secret, algorithm="HS256")
    with pytest.raises(UnauthorizedError):
        security._decode(token)


def test_unsigned_token_is_rejected(jwt_secret: str) -> None:
    token = jwt.encode(_claims(), key=None, algorithm="none")
    with pytest.raises(UnauthorizedError):
        security._decode(token)


def test_hs256_without_a_configured_secret_reports_misconfiguration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "supabase_jwt_secret", "")
    token = jwt.encode(_claims(), SECRET, algorithm="HS256")
    with pytest.raises(UnauthorizedError) as exc:
        security._decode(token)
    assert exc.value.code == "auth_misconfigured"
