from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from app.services.payment_service import PaymentService
from app.dependencies import get_current_user, get_current_admin
import stripe
import os

router = APIRouter(prefix="/payments", tags=["payments"])

# ============================================
# STEP 1: Create Payment Intent
# (Like M-Pesa STK Push)
# ============================================

class CreateIntentRequest(BaseModel):
    amount: float
    payment_method: str  # "card" or "twint"

@router.post("/create-intent")
async def create_payment_intent(
    request: CreateIntentRequest,
    current_user = Depends(get_current_user)
):
    """
    M-Pesa equivalent: STK Push initiation
    Returns client_secret (like CheckoutRequestID)
    """
    try:
        result = PaymentService.create_payment_intent(
            amount=request.amount,
            payment_method=request.payment_method
        )
        return result

    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================
# STEP 2: Webhook Handler
# (Like M-Pesa Callback URL)
# ============================================

@router.post("/webhook")
async def stripe_webhook(request: Request):
    """
    M-Pesa equivalent: Callback URL
    Stripe calls this when payment is completed
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    try:
        # Verify webhook is from Stripe
        # Like verifying M-Pesa callback signature
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # ============================================
    # Handle Events (Like M-Pesa Result Codes)
    # ============================================

    # Payment succeeded (like M-Pesa ResultCode: 0)
    if event["type"] == "payment_intent.succeeded":
        payment_intent = event["data"]["object"]
        payment_intent_id = payment_intent["id"]
        amount_paid = payment_intent["amount"] / 100  # Convert back to CHF

        # Update your order here
        # find order by payment_intent_id → mark as paid
        print(f"Payment succeeded: {payment_intent_id}, Amount: CHF {amount_paid}")

    # Payment failed (like M-Pesa ResultCode: 1032 - cancelled)
    elif event["type"] == "payment_intent.payment_failed":
        payment_intent = event["data"]["object"]
        print(f"Payment failed: {payment_intent['id']}")

    return {"status": "success"}

@router.get("/admin/stripe-balance")
async def get_stripe_balance(current_user = Depends(get_current_admin)):
    """
    Fetch the actual Stripe balance (Available & Pending)
    """
    try:
        balance = stripe.Balance.retrieve()
        return balance
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))