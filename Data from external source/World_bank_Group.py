# comparision between Singapore and the rest of the world for inflation and consumer prices
#Get singapore inflation only
import requests

def get_worldbank_cpi():
    url = "https://api.worldbank.org/v2/country/SGP/indicator/FP.CPI.TOTL.ZG"
    
    params = {
        "format": "json",
        "mrv": 5,        # most recent 5 values
        "gapfill": "Y"   # fill gaps if data is missing
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        # World Bank API returns a list of 2 elements:
        # data[0] = metadata, data[1] = actual records
        if not isinstance(data, list) or len(data) < 2:
            print("Unexpected response structure.")
            return None

        records = data[1]

        if not records:
            print("No records found. The indicator may not have recent data.")
            return None

        print(f"{'Year':<10} {'Inflation (%)'}")
        print("-" * 25)

        for entry in records:
            year = entry.get("date", "N/A")
            value = entry.get("value")

            # value can be None if World Bank hasn't published data yet
            if value is None:
                print(f"{str(year):<10} Data not available")
            else:
                print(f"{str(year):<10} {round(float(value), 2)}%")

        # Return the most recent valid record
        latest_valid = next(
            (r for r in records if r.get("value") is not None), None
        )

        if latest_valid:
            return latest_valid["date"], round(float(latest_valid["value"]), 2)

        return None, None

    except requests.exceptions.Timeout:
        print("Request timed out.")
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error: {e.response.status_code} - {e}")
    except requests.exceptions.ConnectionError:
        print("Connection error. Check your internet connection.")
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
    except (KeyError, IndexError, TypeError, ValueError) as e:
        print(f"Data parsing error: {e}")

    return None, None



#Comparing to other countries
import requests

def compare_countries():
    countries = {
        "SGP": "Singapore",
        "USA": "United States",
        "IND": "India"
    }

    params = {
        "format": "json",
        "mrv": 5,       # fetch last 5 years to find latest non-null value
        "gapfill": "Y"
    }

    results = {}

    print(f"{'Country':<20} {'Year':<10} {'Inflation (%)'}")
    print("-" * 45)

    for code, name in countries.items():
        url = f"https://api.worldbank.org/v2/country/{code}/indicator/FP.CPI.TOTL.ZG"

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Validate World Bank response structure
            if not isinstance(data, list) or len(data) < 2 or not data[1]:
                print(f"{name:<20} No data available")
                continue

            records = data[1]

            # Find the most recent entry where value is not None
            latest_valid = next(
                (r for r in records if r.get("value") is not None), None
            )

            if latest_valid is None:
                print(f"{name:<20} Data not available")
                continue

            year = latest_valid.get("date", "N/A")
            value = round(float(latest_valid["value"]), 2)

            print(f"{name:<20} {str(year):<10} {value}%")
            results[code] = {"country": name, "year": year, "inflation": value}

        except requests.exceptions.Timeout:
            print(f"{name:<20} Request timed out")
        except requests.exceptions.HTTPError as e:
            print(f"{name:<20} HTTP error: {e.response.status_code}")
        except requests.exceptions.ConnectionError:
            print(f"{name:<20} Connection error")
        except requests.exceptions.RequestException as e:
            print(f"{name:<20} Request failed: {e}")
        except (KeyError, IndexError, TypeError, ValueError) as e:
            print(f"{name:<20} Data parsing error: {e}")

    # highest and lowest inflation
    if results:
        sorted_results = sorted(results.values(), key=lambda x: x["inflation"])
        print("\n--- Summary ---")
        print(f"Lowest : {sorted_results[0]['country']} ({sorted_results[0]['inflation']}%)")
        print(f"Highest: {sorted_results[-1]['country']} ({sorted_results[-1]['inflation']}%)")

    return results
