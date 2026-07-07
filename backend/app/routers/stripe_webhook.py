"""
POST /api/v1/stripe/webhook
Processes Stripe billing events and syncs subscription status to the database.
FR-007: Automated subscription status management.
Security: Validates Stripe-Signature header before processing any payload.
"""

from __future__ import annotations

import logging

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import User

router = APIRouter()
logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY

# Stripe events that affect subscription status
SUBSCRIPTION_ACTIVE_EVENTS = {
    "customer.subscription.created",
    "customer.subscription.updated",
    "invoice.payment_succeeded",
}

SUBSCRIPTION_INACTIVE_EVENTS = {
    "customer.subscription.deleted",
    "customer.subscription.paused",
    "invoice.payment_failed",
}


@router.post(
    "/webhook",
    status_code=status.HTTP_200_OK,
    summary="Stripe webhook handler",
    description=(
        "Processes Stripe billing events to sync user subscription state. "
        "Validates the Stripe-Signature header before any processing."
    ),
)
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:  # type: ignore[type-arg]
    """
    Stripe webhook handler flow:
    1. Verify Stripe-Signature to authenticate the webhook.
    2. Parse the event type.
    3. Update is_subscribed flag on the User record.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe.SignatureVerificationError as exc:
        logger.warning("Invalid Stripe webhook signature: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook signature",
        ) from exc
    except Exception as exc:
        logger.error("Stripe webhook parsing error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook parsing failed",
        ) from exc

    event_type: str = event["type"]
    data_object: dict = event["data"]["object"]  # type: ignore[assignment]

    logger.info("Processing Stripe event: %s", event_type)

    # Resolve Auth0 user ID from Stripe customer metadata
    stripe_customer_id: str | None = data_object.get("customer")
    if stripe_customer_id is None:
        return {"status": "ignored", "reason": "no_customer_id"}

    # Look up user by stripe_customer_id
    result = await db.execute(
        select(User).where(User.stripe_customer_id == stripe_customer_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        logger.warning(
            "Stripe webhook received for unknown customer: %s", stripe_customer_id
        )
        return {"status": "ignored", "reason": "user_not_found"}

    if event_type in SUBSCRIPTION_ACTIVE_EVENTS:
        user.is_subscribed = True
        logger.info("Activated subscription for user %s", user.id)

    elif event_type in SUBSCRIPTION_INACTIVE_EVENTS:
        user.is_subscribed = False
        logger.info("Deactivated subscription for user %s", user.id)

    else:
        return {"status": "ignored", "reason": "unhandled_event_type"}

    return {"status": "processed"}
