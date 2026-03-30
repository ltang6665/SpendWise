import requests

def get_current_cpi():
    """
    Fetches the latest CPI data from SingStat and returns it as a dict.
    Returns None if data could not be retrieved.
    """
    try:
        month, value = get_current_cpi_singstat()

        # Validate that both values were successfully returned
        if month is None or value is None:
            print("CPI data unavailable: get_current_cpi_singstat() returned None.")
            return None

        # Safely convert value to float for consistency
        try:
            cpi_value = round(float(value), 2)
        except (TypeError, ValueError):
            print(f"Invalid CPI value received: {value!r}")
            return None

        result = {
            "month": str(month).strip(),
            "cpi": cpi_value
        }

        print(f"[CPI] Month: {result['month']} | CPI: {result['cpi']}")
        return result

    except TypeError as e:
        print(f"Unpacking error — get_current_cpi_singstat() may not have returned 2 values: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error in get_current_cpi(): {e}")
        return None
