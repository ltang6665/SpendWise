#Singapore Department of Statistics
# current CPI for latest month
import requests

def get_current_cpi_singstat():
    url = "https://tablebuilder.singstat.gov.sg/api/table/tabledata/M212261"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raises an error for 4xx/5xx responses
        data = response.json()

        records = data['Data']['row']
        if not records:
            raise ValueError("No records found in response")

        latest = records[-1]

        # Safely access key and value
        month = latest['key'][0] if latest.get('key') else None
        value = latest['value'][0] if latest.get('value') else None

        print(f"[SingStat] Current CPI ({month}): {value}")
        return month, value

    except requests.exceptions.Timeout:
        print("Request timed out")
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error: {e}")
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
    except (KeyError, IndexError, ValueError) as e:
        print(f"Data parsing error: {e}")

    return None, None


#Get CPI by category
import requests

def get_cpi_by_category():
    url = "https://tablebuilder.singstat.gov.sg/api/table/tabledata/M212261"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        records = data['Data']['row']

        if not records:
            print("No records found.")
            return

        print(f"{'Category':<30} {'CPI Value'}")
        print("-" * 40)

        for r in records[-5:]:  # last 5 entries
            # key[0] is typically the month, key[1] is category (if present)
            category = r['key'][1] if len(r.get('key', [])) > 1 else "All Items"

            # value may be a list or a single item — handle both
            raw_value = r.get('value', [])
            value = raw_value[0] if isinstance(raw_value, list) and raw_value else raw_value

            print(f"{str(category):<30} {value}")

    except requests.exceptions.Timeout:
        print("Request timed out.")
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error: {e}")
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
    except (KeyError, IndexError, TypeError) as e:
        print(f"Data parsing error: {e}")


