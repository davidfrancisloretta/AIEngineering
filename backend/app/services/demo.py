"""
Generates realistic demo Rave/Flutterwave transaction data.
Used only for the demo account — no real API calls made.
"""
import random
from datetime import datetime, timedelta, timezone

import yaml

CUSTOMERS = [
    ("Adebayo Okafor", "adebayo.okafor@gmail.com", "+2348012345678"),
    ("Ngozi Adeyemi", "ngozi.adeyemi@yahoo.com", "+2348023456789"),
    ("Chukwuemeka Eze", "emeka.eze@outlook.com", "+2348034567890"),
    ("Fatima Al-Hassan", "fatima.alhassan@gmail.com", "+2348045678901"),
    ("Taiwo Abiodun", "taiwo.abiodun@gmail.com", "+2348056789012"),
    ("Amara Diallo", "amara.diallo@yahoo.com", "+2347012345678"),
    ("Kofi Mensah", "kofi.mensah@gmail.com", "+233201234567"),
    ("Ama Asante", "ama.asante@hotmail.com", "+233209876543"),
    ("Wanjiru Kamau", "wanjiru.kamau@gmail.com", "+254701234567"),
    ("Mwangi Njoroge", "mwangi.njoroge@yahoo.com", "+254723456789"),
    ("Chiamaka Obi", "chiamaka.obi@gmail.com", "+2348067890123"),
    ("Olumide Adewale", "olumide.adewale@company.ng", "+2348078901234"),
    ("Blessing Nwosu", "blessing.nwosu@gmail.com", "+2348089012345"),
    ("Emeka Onuoha", "emeka.onuoha@enterprise.com", "+2348090123456"),
    ("Tunde Fashola", "t.fashola@business.ng", "+2348101234567"),
    ("Grace Osei", "grace.osei@gmail.com", "+233246789012"),
    ("Kwame Asare", "kwame.asare@business.gh", "+233257890123"),
    ("Aisha Mohammed", "aisha.m@gmail.com", "+2348112345678"),
    ("David Adekunle", "d.adekunle@tech.ng", "+2348123456789"),
    ("Yetunde Balogun", "yetunde.b@market.ng", "+2348134567890"),
]

CURRENCIES_WEIGHTS = [
    ("NGN", 55),  # Nigerian Naira — dominant
    ("USD", 20),  # US Dollar
    ("GHS", 10),  # Ghanaian Cedi
    ("KES", 10),  # Kenyan Shilling
    ("GBP", 5),   # British Pound
]

PAYMENT_TYPES_WEIGHTS = [
    ("card", 45),
    ("bank_transfer", 30),
    ("mobile_money", 15),
    ("ussd", 10),
]

STATUS_WEIGHTS = [
    ("successful", 72),
    ("failed", 18),
    ("pending", 10),
]

AMOUNT_RANGES = {
    "NGN": (500, 450_000),
    "USD": (5, 4_500),
    "GHS": (10, 8_000),
    "KES": (200, 90_000),
    "GBP": (5, 3_500),
}

NARRATIONS = [
    "Payment for services",
    "Product purchase",
    "Subscription renewal",
    "Invoice payment",
    "E-commerce order",
    "Marketplace transaction",
    "Digital product",
    "Consulting fee",
    "Salary disbursement",
    "School fees",
    "Utility bill",
    "Airtime purchase",
]


def _weighted_choice(weighted_list: list[tuple]) -> str:
    population = [item for item, weight in weighted_list for _ in range(weight)]
    return random.choice(population)


def generate_transactions(n: int = 60, seed: int = 42) -> list[dict]:
    rng = random.Random(seed)
    now = datetime.now(timezone.utc)
    transactions = []

    for i in range(n):
        currency = _weighted_choice_rng(rng, CURRENCIES_WEIGHTS)
        lo, hi = AMOUNT_RANGES[currency]
        amount = round(rng.uniform(lo, hi), 2)
        status = _weighted_choice_rng(rng, STATUS_WEIGHTS)
        payment_type = _weighted_choice_rng(rng, PAYMENT_TYPES_WEIGHTS)
        customer_name, customer_email, phone = rng.choice(CUSTOMERS)
        days_ago = rng.randint(0, 89)
        hours_ago = rng.randint(0, 23)
        created_at = now - timedelta(days=days_ago, hours=hours_ago)

        rave_id = 1_000_000 + i + rng.randint(0, 999)
        tx_ref = f"DEMO-{rave_id}-{created_at.strftime('%Y%m%d')}"

        txn = {
            "id": rave_id,
            "tx_ref": tx_ref,
            "flw_ref": f"FLW-{rng.randint(100000, 999999)}",
            "amount": amount,
            "currency": currency,
            "status": status,
            "payment_type": payment_type,
            "narration": rng.choice(NARRATIONS),
            "customer": {
                "email": customer_email,
                "name": customer_name,
                "phone_number": phone,
            },
            "created_at": created_at.isoformat(),
            "app_fee": round(amount * 0.014, 2),
            "merchant_fee": 0,
            "charged_amount": amount,
        }
        transactions.append(txn)

    # Sort newest first
    transactions.sort(key=lambda t: t["created_at"], reverse=True)
    return transactions


def _weighted_choice_rng(rng: random.Random, weighted_list: list[tuple]) -> str:
    population = [item for item, weight in weighted_list for _ in range(weight)]
    return rng.choice(population)


def transaction_to_yaml(txn: dict) -> str:
    return yaml.dump(txn, default_flow_style=False, allow_unicode=True, sort_keys=False)


def transactions_to_bulk_yaml(transactions: list[dict]) -> str:
    return yaml.dump(
        {"transactions": transactions, "total": len(transactions)},
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )
