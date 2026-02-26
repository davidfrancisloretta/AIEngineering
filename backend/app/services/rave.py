import yaml
import requests

RAVE_BASE_URL = "https://api.flutterwave.com/v3"


def fetch_transactions(secret_key: str, page: int = 1) -> dict:
    headers = {"Authorization": f"Bearer {secret_key}"}
    response = requests.get(
        f"{RAVE_BASE_URL}/transactions",
        headers=headers,
        params={"page": page, "perPage": 100},
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def to_yaml(data: dict) -> str:
    return yaml.dump(data, default_flow_style=False, allow_unicode=True)
