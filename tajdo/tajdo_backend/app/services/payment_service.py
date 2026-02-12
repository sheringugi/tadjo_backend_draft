from typing import Dict, Any
import random

def process_twint_payment(amount: float, currency: str) -> Dict[str, Any]:
    """
    Simulates processing a Twint payment.
    In a real-world scenario, this would involve:
    1. Calling the Twint API to create a payment request.
    2. Receiving a transaction ID and a redirect URL/QR code.
    3. The user completing the payment on their device.
    4. Twint sending a webhook callback to our backend.
    """
    # Simulate a successful transaction 90% of the time
    if random.random() < 0.9:
        return {
            "status": "succeeded",
            "transaction_id": f"TWINT-{random.randint(100000, 999999)}",
            "amount": amount,
            "currency": currency
        }
    else:
        return {
            "status": "failed",
            "error": "Twint payment rejected by user or insufficient funds",
            "amount": amount,
            "currency": currency
        }

def process_card_payment(amount: float, currency: str, card_details: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simulates processing a bank card payment (e.g., via Stripe or similar).
    In a real-world scenario, this would involve:
    1. Sending card details securely to a payment gateway.
    2. The gateway performing 3D Secure verification if required.
    3. Receiving a success or failure response from the gateway.
    """
    # Basic validation simulation
    card_number = card_details.get("card_number", "")
    if len(card_number) < 13:
        return {
            "status": "failed",
            "error": "Invalid card number",
            "amount": amount,
            "currency": currency
        }

    # Simulate a successful transaction 95% of the time
    if random.random() < 0.95:
        return {
            "status": "succeeded",
            "transaction_id": f"CARD-{random.randint(100000, 999999)}",
            "amount": amount,
            "currency": currency
        }
    else:
        return {
            "status": "failed",
            "error": "Card declined by the issuing bank",
            "amount": amount,
            "currency": currency
        }
