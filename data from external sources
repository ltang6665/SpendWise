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



