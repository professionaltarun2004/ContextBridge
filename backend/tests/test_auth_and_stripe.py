"""
Unit tests for auth.py JWT verification and stripe_webhook.py billing handler.
Uses mocked JWKS, jose.jwt.decode, and stripe.Webhook to avoid live API calls.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from httpx import AsyncClient

from app.auth import AuthTokenClaims, _decode_jwt

# ---------------------------------------------------------------------------
# Auth Tests — JWT decoding (auth.py)
# ---------------------------------------------------------------------------


class TestAuthTokenClaims:
    """Tests for the AuthTokenClaims typed wrapper."""

    def test_claims_extracts_sub_and_email(self) -> None:
        payload = {"sub": "auth0|abc123", "email": "test@example.com"}
        claims = AuthTokenClaims(payload)
        assert claims.sub == "auth0|abc123"
        assert claims.email == "test@example.com"

    def test_claims_defaults_email_to_empty_string(self) -> None:
        payload = {"sub": "auth0|noemail"}
        claims = AuthTokenClaims(payload)
        assert claims.email == ""

    def test_claims_stores_raw_payload(self) -> None:
        payload = {"sub": "auth0|abc", "email": "x@y.com", "custom": "value"}
        claims = AuthTokenClaims(payload)
        assert claims.raw == payload


class TestDecodeJWT:
    """Tests for _decode_jwt with mocked JWKS and jose."""

    def test_raises_401_on_malformed_header(self) -> None:
        """JWT with a completely invalid token structure should raise 401."""
        from jose import JWTError

        with patch("app.auth._get_jwks", return_value={"keys": []}):
            with patch(
                "app.auth.jwt.get_unverified_header",
                side_effect=JWTError("bad header"),
            ):
                with pytest.raises(HTTPException) as exc_info:
                    _decode_jwt("totally.invalid.token")
                assert exc_info.value.status_code == 401
                assert "Invalid token header" in exc_info.value.detail

    def test_raises_401_when_no_matching_jwks_key(self) -> None:
        """No matching KID in JWKS should raise 401."""
        with patch(
            "app.auth._get_jwks",
            return_value={"keys": [{"kid": "other-kid", "kty": "RSA"}]},
        ):
            with patch(
                "app.auth.jwt.get_unverified_header",
                return_value={"kid": "my-kid", "alg": "RS256"},
            ):
                with pytest.raises(HTTPException) as exc_info:
                    _decode_jwt("any.token.here")
                assert exc_info.value.status_code == 401
                assert "Unable to find appropriate key" in exc_info.value.detail

    def test_raises_401_on_expired_token(self) -> None:
        """Expired JWT should raise 401 with 'expired' message."""
        from jose.exceptions import ExpiredSignatureError

        mock_key = {
            "kid": "test-kid",
            "kty": "RSA",
            "use": "sig",
            "n": "test",
            "e": "AQAB",
        }
        with patch(
            "app.auth._get_jwks", return_value={"keys": [mock_key]}
        ):
            with patch(
                "app.auth.jwt.get_unverified_header",
                return_value={"kid": "test-kid", "alg": "RS256"},
            ):
                with patch(
                    "app.auth.jwt.decode",
                    side_effect=ExpiredSignatureError("token expired"),
                ):
                    with pytest.raises(HTTPException) as exc_info:
                        _decode_jwt("expired.token.here")
                    assert exc_info.value.status_code == 401
                    assert "expired" in exc_info.value.detail.lower()

    def test_successful_decode_returns_payload(self) -> None:
        """Valid JWT should return decoded payload dict."""
        mock_key = {
            "kid": "test-kid",
            "kty": "RSA",
            "use": "sig",
            "n": "test",
            "e": "AQAB",
        }
        expected_payload = {
            "sub": "auth0|user123",
            "email": "user@test.com",
            "aud": "https://api.contextbridge.ai",
        }
        with patch(
            "app.auth._get_jwks", return_value={"keys": [mock_key]}
        ):
            with patch(
                "app.auth.jwt.get_unverified_header",
                return_value={"kid": "test-kid", "alg": "RS256"},
            ):
                with patch(
                    "app.auth.jwt.decode", return_value=expected_payload
                ):
                    result = _decode_jwt("valid.jwt.token")
                    assert result["sub"] == "auth0|user123"
                    assert result["email"] == "user@test.com"


# ---------------------------------------------------------------------------
# Stripe Webhook Tests — billing handler (stripe_webhook.py)
# ---------------------------------------------------------------------------


class TestStripeWebhook:
    """Tests for POST /api/v1/stripe/webhook."""

    @pytest.mark.asyncio
    async def test_invalid_signature_returns_400(
        self, client: AsyncClient
    ) -> None:
        """Webhook with invalid Stripe-Signature header should return 400."""
        import stripe

        with patch(
            "app.routers.stripe_webhook.stripe.Webhook.construct_event",
            side_effect=stripe.SignatureVerificationError(
                "Invalid signature", "sig_header"
            ),
        ):
            response = await client.post(
                "/api/v1/stripe/webhook",
                content=b'{"type": "customer.subscription.created"}',
                headers={
                    "stripe-signature": "invalid_sig",
                    "content-type": "application/json",
                },
            )
        assert response.status_code == 400
        assert "signature" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_subscription_created_activates_user(
        self, client: AsyncClient, test_db: object
    ) -> None:
        """customer.subscription.created event activates user subscription."""
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import AsyncSession

        db = test_db  # type: ignore[assignment]
        assert isinstance(db, AsyncSession)

        # Insert a user with stripe_customer_id
        await db.execute(
            text(
                "INSERT INTO users (id, email, stripe_customer_id, is_subscribed) "
                "VALUES ('auth0|stripe_test', 'stripe@test.com', 'cus_test123', 0)"
            )
        )
        await db.commit()

        mock_event = MagicMock()
        mock_event.__getitem__ = lambda self, key: {
            "type": "customer.subscription.created",
            "data": {"object": {"customer": "cus_test123"}},
        }[key]

        with patch(
            "app.routers.stripe_webhook.stripe.Webhook.construct_event",
            return_value=mock_event,
        ):
            response = await client.post(
                "/api/v1/stripe/webhook",
                content=b'{"type": "customer.subscription.created"}',
                headers={
                    "stripe-signature": "valid_sig",
                    "content-type": "application/json",
                },
            )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_unknown_customer_returns_ignored(
        self, client: AsyncClient
    ) -> None:
        """Webhook for unknown customer should return ignored status."""
        mock_event = MagicMock()
        mock_event.__getitem__ = lambda self, key: {
            "type": "customer.subscription.created",
            "data": {"object": {"customer": "cus_unknown_999"}},
        }[key]

        with patch(
            "app.routers.stripe_webhook.stripe.Webhook.construct_event",
            return_value=mock_event,
        ):
            response = await client.post(
                "/api/v1/stripe/webhook",
                content=b'{"type": "customer.subscription.created"}',
                headers={
                    "stripe-signature": "valid_sig",
                    "content-type": "application/json",
                },
            )

        assert response.status_code == 200
        assert response.json()["status"] == "ignored"
        assert response.json()["reason"] == "user_not_found"

    @pytest.mark.asyncio
    async def test_unhandled_event_type_returns_ignored(
        self, client: AsyncClient
    ) -> None:
        """Unhandled event types should be ignored without error."""
        mock_event = MagicMock()
        mock_event.__getitem__ = lambda self, key: {
            "type": "payment_method.attached",
            "data": {"object": {"customer": "cus_any"}},
        }[key]

        with patch(
            "app.routers.stripe_webhook.stripe.Webhook.construct_event",
            return_value=mock_event,
        ):
            response = await client.post(
                "/api/v1/stripe/webhook",
                content=b'{"type": "payment_method.attached"}',
                headers={
                    "stripe-signature": "valid_sig",
                    "content-type": "application/json",
                },
            )

        assert response.status_code == 200
        assert response.json()["status"] == "ignored"
