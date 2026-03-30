#to get the food price,transport costs and utility costs (Singapore)
import requests
from bs4 import BeautifulSoup

def get_numbeo_prices():
    url = "https://www.numbeo.com/cost-of-living/in/Singapore"

    # Headers to mimic a real browser — Numbeo blocks plain requests
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.google.com/"
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Numbeo uses <td class="priceValue"> for cost values
        # and nearby <td> for item names — extract both together
        results = []

        rows = soup.find_all("tr")
        for row in rows:
            name_td = row.find("td", class_="itemName")
            price_td = row.find("td", class_="priceValue")

            if name_td and price_td:
                item = name_td.get_text(strip=True)
                price = price_td.get_text(strip=True)
                results.append((item, price))

        if not results:
            print("No price data found. Numbeo may have changed its HTML structure.")
            return []

        print(f"{'Item':<45} {'Price (SGD)'}")
        print("-" * 60)

        for item, price in results[:10]:   # show first 10 items
            print(f"{item:<45} {price}")

        return results

    except requests.exceptions.Timeout:
        print("Request timed out. Numbeo may be slow or unavailable.")
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code
        if status == 403:
            print("Access blocked (403). Numbeo is rejecting the request.")
        elif status == 429:
            print("Rate limited (429). Too many requests — wait before retrying.")
        else:
            print(f"HTTP error: {status}")
    except requests.exceptions.ConnectionError:
        print("Connection error. Check your internet connection.")
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
    except Exception as e:
        print(f"Unexpected error during scraping: {e}")

    return []
