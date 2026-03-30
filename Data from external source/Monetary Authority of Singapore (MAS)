#Monetary Authority of Singapore (MAS)
# Used for enhancing 6 months prediction
# Get inflation trend
import requests

def get_mas_inflation():
    # Correct MAS endpoint for inflation/CPI-related data
    url = "https://eservices.mas.gov.sg/api/action/datastore/search.json"
    
    params = {
        "resource_id": "5a3d9b52-a3b5-4b3b-9a1a-1b2c3d4e5f6a",  # Replace with actual MAS resource ID
        "limit": 10,
        "sort": "end_of_period desc"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Validate expected structure
        if "result" not in data or "records" not in data["result"]:
            print("Unexpected response structure:", data)
            return None

        records = data["result"]["records"]

        if not records:
            print("No records returned from MAS API.")
            return None

        print(f"{'Period':<20} {'Value'}")
        print("-" * 35)

        for record in records:
            period = record.get("end_of_period", "N/A")
            value = record.get("value", "N/A")
            print(f"{str(period):<20} {value}")

        return records

    except requests.exceptions.Timeout:
        print("Request timed out.")
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error: {e.response.status_code} - {e}")
    except requests.exceptions.ConnectionError:
        print("Connection error. Check your internet or the API URL.")
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
    except (KeyError, TypeError, ValueError) as e:
        print(f"Data parsing error: {e}")

    return None
