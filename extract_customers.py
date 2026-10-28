"""
API Data Extraction and Transformation
Squad Python Specialization - Data Engineering

Extracts customer records from the JSONPlaceholder Users API, flattens the
nested JSON, and exports output/customers_clean.csv.

"""
import sys
from pathlib import Path

import pandas as pd
import requests


API_URL = "https://jsonplaceholder.typicode.com/users"
OUTPUT_PATH = Path("output") / "customers_clean.csv"

EXPECTED_COLUMNS = [
    "customer_id", "name", "username", "email", "phone", "website",
    "address_street", "address_suite", "address_city", "address_zipcode",
    "address_geo_lat", "address_geo_lng",
    "company_name", "company_catchphrase", "company_bs",
]

def fetch_users(url: str = API_URL, timeout: float = 10.0) -> list[dict]:
    """Retrieve the list of users from the API.

    Must raise or report a clear error for: connection failures, timeouts,
    non-200 status codes and bodies that are not valid JSON.
    """
    try:
        response = requests.get(url, timeout=timeout)
    except requests.exceptions.Timeout:
        raise RuntimeError(f"Request timed out after {timeout} seconds: {url}")
    except requests.exceptions.ConnectionError:
        raise RuntimeError(f"Could not connect to {url}. Check the URL and your internet connection.")
    except requests.exceptions.RequestException as error:
        raise RuntimeError(f"Request to {url} failed: {error}")

    if response.status_code != 200:
        raise RuntimeError(f"API returned status {response.status_code} for {url}")

    try:
        return response.json()
    except ValueError:
        raise RuntimeError(f"Response from {url} is not valid JSON")


def _print_types(data: dict, indent: int = 1) -> None:
    """Print the type of every value in a dict, going inside nested dicts."""
    for key, value in data.items():
        print(f"{'  ' * indent}{key}: {type(value).__name__}")
        if isinstance(value, dict):
            _print_types(value, indent + 1)


def describe_structure(payload) -> None:
    """Print what Python types the payload and one record are made of
    (the top-level container, a record, and each nested value)."""
    print(f"Top-level payload: {type(payload).__name__} with {len(payload)} items")
    record = payload[0]
    print(f"One record: {type(record).__name__} with {len(record)} keys")
    _print_types(record)


def extract_core_fields(users: list[dict]) -> list[dict]:
    """Return one small dict per user with id, name, email, city and company name."""
    core = []                   # start with an empty list
    for user in users:              # go through each user one at a time
        record = {
            "id": user.get("id"),
            "name": user.get("name", "Unknown"),
            "email": user.get("email", "Unknown"),
            "city": user.get("address", {}).get("city", "Unknown"),
            "company": user.get("company", {}).get("name", "Unknown"),
        }
        core.append(record)         # add this user's small dict to the list
    return core                     # hand back the full list


def build_structures(users: list[dict]) -> tuple[list, list[tuple], dict]:
    """Return (list_of_names, list_of_(id, email)_tuples, dict_of_id_to_city).

    Use at least one list comprehension and one dict comprehension.
    """
    names = [user.get("name", "Unknown") for user in users]
    id_emails = [(user.get("id"), user.get("email", "Unknown")) for user in users]
    id_to_city = {user.get("id"): user.get("address", {}).get("city", "Unknown") for user in users}
    return names, id_emails, id_to_city


def flatten_user(user: dict, parent_key: str = "", sep: str = "_") -> dict:
    """Flatten one nested user record into a single-level dict.

    e.g. a nested address -> geo -> lat becomes the key address_geo_lat.
    """
    flat = {}
    for key, value in user.items():
        new_key = f"{parent_key}{sep}{key}" if parent_key else key
        if isinstance(value, dict):
            flat.update(flatten_user(value, new_key, sep))
        else:
            flat[new_key] = value
    return flat


def to_dataframe(flat_users: list[dict]) -> pd.DataFrame:
    """Build a DataFrame with the columns in the expected-output order."""
    df = pd.DataFrame(flat_users)
    df.columns = df.columns.str.lower()
    df = df.rename(columns={"id": "customer_id"})
    for col in ["address_geo_lat", "address_geo_lng"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.reindex(columns=EXPECTED_COLUMNS)
    return df


def export_csv(df: pd.DataFrame, path: Path = OUTPUT_PATH) -> Path:
    """Write the DataFrame to CSV (creating the folder if needed) and return the path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return path


def main() -> None:
    """Run the full pipeline: extract, transform and load the customer data."""
    users = fetch_users()
    describe_structure(users)
    core = extract_core_fields(users)
    names, id_emails, id_to_city = build_structures(users)
    flat_users = [flatten_user(user) for user in users]
    df = to_dataframe(flat_users)
    saved_path = export_csv(df)

    print("\nRun summary")
    print(f"  Users fetched:    {len(users)}")
    print(f"  Core records:     {len(core)}")
    print(f"  Names collected:  {len(names)}")
    print(f"  Cities mapped:    {len(id_to_city)}")
    print(f"  Columns exported: {df.shape[1]}")
    print(f"  Saved {len(df)} rows to {saved_path}")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
