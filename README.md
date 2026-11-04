# Day 1: API Data Extraction and Transformation
Extracts customer records from the JSONPlaceholder Users API, flattens the nested JSON, and exports a clean CSV for the Duka Connect analytics team.

## Approach

The script `extract_customers.py` runs a small ETL pipeline:

1. **Extract:** `fetch_users` calls the API with a timeout, checks the status code, and parses the JSON.
2. **Inspect:** `describe_structure` prints the type of the payload, one record, and every nested value (recursively).
3. **Select:** `extract_core_fields` pulls id, name, email, city and company name, with safe defaults for missing keys.
4. **Restructure:** `build_structures` builds a list of names, a list of (id, email) tuples and an id → city dict, using list and dict comprehensions.
5. **Flatten:** `flatten_user` recursively collapses nested dicts into single-level keys like `address_geo_lat`, with no field names hard-coded.
6. **Transform:** `to_dataframe` loads the records into pandas, lowercases column names, renames `id` to `customer_id`, orders the columns to match the expected output, and converts coordinates to numbers. It then drops rows with a blank or duplicated `customer_id` (keeping the first copy) and prints the DataFrame's shape and column types, so a column that silently changes type is easy to spot.
7. **Load:** `export_csv` writes `output/customers_clean.csv` (creating the folder if needed), without the index, overwriting any previous file.

## How to run

Requires Python 3.10 or newer.

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python extract_customers.py
```

On Mac or Linux, activate with `source venv/bin/activate` instead. The output is written to `output/customers_clean.csv`.

## Data structure (Task 2)

The API returns a **list** of 10 user records. Each record is a **dict** with 8 keys.

| Field | Type | Nested? | Depth |
|---|---|---|---|
| id | int | no | 0 |
| name, username, email, phone, website | str | no | 0 |
| address | dict | yes | 1 |
| address → street, suite, city, zipcode | str | no | 1 |
| address → geo | dict | yes | 2 |
| address → geo → lat, lng | str | no | 2 |
| company | dict | yes | 1 |
| company → name, catchPhrase, bs | str | no | 1 |

Two nested fields (`address`, `company`); the deepest nesting is 2 levels (`address → geo`).

Note: `lat` and `lng` are stored as strings and are converted to numbers in Task 6.

## Assumptions

- **Missing fields (Task 3):** if a field is missing, `extract_core_fields` uses the default `"Unknown"` instead of crashing. Nested parents use `(user.get("address") or {}).get("city", "Unknown")`: a plain `.get("address", {})` only covers a missing key, while `or {}` also covers a key whose value is `null`. A missing `id` becomes `None`, since "Unknown" is not a sensible id.
- **Flattening (Task 5):** `flatten_user` is recursive and hard-codes no field names. Nested keys are joined with `_` (e.g. `address → geo → lat` becomes `address_geo_lat`), at any depth. Tested on an unseen record nested 3 levels deep: `{"shipping": {"warehouse": {"location": {"country": "Kenya"}}}}` became `shipping_warehouse_location_country`.
- **DataFrame (Task 6):** all column names are lowercased (fixing `catchPhrase`), `id` is renamed to `customer_id`, and `address_geo_lat` / `address_geo_lng` are converted with `pd.to_numeric(errors="coerce")`, so any value that can't be converted becomes empty instead of crashing. Columns are reordered to match the expected output; any missing column would be filled with empty values.
- **Customer IDs:** rows with a blank or duplicated `customer_id` are dropped before export, the first copy is kept, and the number dropped is printed. Tested with four fake records (a duplicate ID and a blank ID among them): two rows were dropped and the IDs stayed whole numbers.

## Error handling (Task 8)

Every failure prints one clear `Error: ...` message and exits with code 1. There is no raw traceback. `fetch_users` turns each low-level error into a `RuntimeError`, and the `__main__` block catches it, prints it to stderr, and calls `sys.exit(1)`.

| Case | How I tested it | Message |
| --- | --- | --- |
| Non-200 status | `fetch_users("https://jsonplaceholder.typicode.com/userz")` | `API returned status 404 for ...` |
| Wrong URL | `fetch_users("https://this-site-does-not-exist-12345.com/users")` | `Could not connect to ... Check the URL and your internet connection.` |
| Timeout | `fetch_users(timeout=0.001)` | `Request timed out after 0.001 seconds: ...` |
| Body not JSON | `fetch_users("https://jsonplaceholder.typicode.com/")` (returns HTML with status 200) | `Response from ... is not valid JSON` |
| Payload is not a list | `fetch_users(".../users/1")` (returns one user as a dict) | `Expected a list of users from ..., got dict` |
| Payload is an empty list | `fetch_users(".../users?id=999")` (returns `[]`) | `API returned an empty list of users: ...` |

I checked the exit code after each test with `echo %ERRORLEVEL%`, which printed `1`.

Any other unexpected error is caught by a final `except Exception` in `__main__`, which prints `Unexpected error: <type>: <message>` and exits with code 1, so no run ends in a raw traceback.