import requests
import logging
import time
from datetime import datetime
from sqlmodel import Session, select
from .database import engine
from .models import NationalCPIDB
from urllib.parse import quote

logger = logging.getLogger(__name__)

API_BASE_URL = "https://tablebuilder.singstat.gov.sg/api/table"
TABLE_ID = "M213751"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; SpendWise/1.0)",
    "Accept": "application/json",
}

def parse_key_date(key: str):
    key = key.strip()
    for fmt in ["%Y %b", "%b %Y"]:
        try:
            return datetime.strptime(key, fmt).strftime("%Y-%m")
        except Exception:
            pass
    return None

def fetch_and_store_dynamic_cpi():
    with Session(engine) as session:
        from sqlmodel import func
        count = session.exec(select(func.count(func.distinct(NationalCPIDB.Category)))).one()
        
        if count > 200:
            logger.info(f"Database already has {count} categories. Skipping full sync!")
            return 
            
    logger.info("Database looks empty or incomplete. Starting full targeted sync...")
    
    try:
        # STEP 1: Get all category names from the metadata
        meta_url = f"{API_BASE_URL}/metadata/{TABLE_ID}"
        meta_response = requests.get(meta_url, headers=HEADERS, timeout=20)
        meta_response.raise_for_status()
        
        meta_records = meta_response.json().get("Data", {}).get("records", {}).get("row", [])
        
        category_names = []
        for record in meta_records:
            name = record.get("rowText", "").strip()
            if name:
                category_names.append(name)
                
        logger.info(f"Found {len(category_names)} categories to search for.")

        processed_categories = set()
        
        with Session(engine) as session:
            # ─── PASS 1: FAST DUMP RAW DATA ───
            for target_category in category_names:
                if target_category in processed_categories:
                    continue 
                
                offset = 0
                limit = 5000
                
                while True:
                    search_term = target_category
                    if "&" in search_term:
                        search_term = search_term.split("&")[0].strip()

                    safe_search_term = quote(search_term)
                    
                    exact_url = (
                        f"{API_BASE_URL}/tabledata/{TABLE_ID}"
                        f"?isTestApi=true"
                        f"&offset={offset}"
                        f"&limit={limit}"
                        f"&sortBy=key%20desc"
                        f"&search={safe_search_term}"
                    )
                    
                    try:
                        data_response = requests.get(exact_url, headers=HEADERS, timeout=20)
                        
                        if data_response.status_code != 200:
                            logger.error(f"API Error {data_response.status_code} for {target_category}")
                            break 
                            
                        api_data = data_response.json()
                        rows = api_data.get("Data", {}).get("row", [])
                        
                        if not rows:
                            break 

                        for row in rows:
                            cat_name = row.get("rowText", "").strip()
                            columns = row.get("columns", [])
                            
                            if not cat_name or not columns:
                                continue
                                
                            processed_categories.add(cat_name)

                            for col in columns:
                                raw_month = col.get("key", "").replace(" Numeric", "").replace(" Text", "").strip()
                                formatted_month = parse_key_date(raw_month)
                                raw_value = col.get("value")
                                
                                if not formatted_month or raw_value in (None, "", "-", "na", "NA", "s"):
                                    continue
                                
                                index_value = float(raw_value)

                                # Safely Upsert raw data only
                                statement = select(NationalCPIDB).where(
                                    NationalCPIDB.Month == formatted_month,
                                    NationalCPIDB.Category == cat_name
                                )
                                existing_record = session.exec(statement).first()

                                if not existing_record:
                                    session.add(NationalCPIDB(
                                        Month=formatted_month,
                                        Category=cat_name,
                                        IndexValue=index_value,
                                        YoYChange=None # Leave blank for Pass 2
                                    ))
                                elif existing_record.IndexValue != index_value:
                                    existing_record.IndexValue = index_value
                                    session.add(existing_record)
                                    
                        session.commit()
                        
                        if len(rows) < limit:
                            break
                            
                        offset += limit
                        time.sleep(0.2)

                    except Exception as cat_err:
                        logger.error(f"Failed to fetch keyword '{target_category}' at offset {offset}: {cat_err}")
                        session.rollback()
                        break
                
                if len(processed_categories) % 10 == 0:
                    logger.info(f"Progress: {len(processed_categories)} unique categories synced...")
                time.sleep(0.2)

            # ─── PASS 2: CALCULATE YoY CHANGES INTERNALLY ───
            logger.info("Raw data sync complete. Calculating Year-over-Year changes...")
            
            # Get all records that don't have a YoY change calculated yet
            missing_yoy_records = session.exec(
                select(NationalCPIDB).where(NationalCPIDB.YoYChange == None)
            ).all()

            for current_record in missing_yoy_records:
                try:
                    # Find exactly one year ago
                    current_date = datetime.strptime(current_record.Month, "%Y-%m")
                    one_year_ago_date = current_date.replace(year=current_date.year - 1)
                    one_year_ago_str = one_year_ago_date.strftime("%Y-%m")

                    # Look up the past record
                    past_record = session.exec(
                        select(NationalCPIDB).where(
                            NationalCPIDB.Month == one_year_ago_str,
                            NationalCPIDB.Category == current_record.Category
                        )
                    ).first()

                    # Calculate and save
                    if past_record and past_record.IndexValue > 0:
                        yoy = round(((current_record.IndexValue / past_record.IndexValue) - 1) * 100, 2)
                        current_record.YoYChange = yoy
                        session.add(current_record)
                
                except Exception as e:
                    logger.error(f"Failed to calculate YoY for {current_record.Category} in {current_record.Month}: {e}")

            # Commit all the new YoY calculations
            session.commit()
            logger.info("YoY Calculations complete!")

    except Exception as e:
        logger.error(f"Metadata fetch failed: {e}")


def update_latest_cpi_data():
    """
    Lightweight updater incorporating all API workarounds. 
    Finds the latest month in the DB, searches categories, 
    and only inserts data that is strictly newer.
    """
    logger.info("Checking SingStat for new monthly CPI data...")
    
    with Session(engine) as session:
        # 1. Find the "High Water Mark"
        latest_db_record = session.exec(
            select(NationalCPIDB.Month).order_by(NationalCPIDB.Month.desc())
        ).first()
        
        if not latest_db_record:
            logger.warning("Database is empty! Please run the full historical sync first.")
            return
            
        logger.info(f"Latest month in DB is {latest_db_record}. Checking for newer data...")
        
        # 2. Get categories directly from our own database! (Saves a metadata API call)
        db_categories = session.exec(select(NationalCPIDB.Category).distinct()).all()
        
        processed_categories = set()
        new_records_added = 0
        
        # 3. Loop through categories using our finalized search logic
        for target_category in db_categories:
            if target_category in processed_categories:
                continue
                
            # Ampersand workaround
            search_term = target_category
            if "&" in search_term:
                search_term = search_term.split("&")[0].strip()
                
            safe_search_term = quote(search_term)
            
            offset = 0
            limit = 5000
            
            while True:
                exact_url = (
                    f"https://tablebuilder.singstat.gov.sg/api/table/tabledata/M213751"
                    f"?isTestApi=true"
                    f"&offset={offset}"
                    f"&limit={limit}"
                    f"&sortBy=key%20desc"
                    f"&search={safe_search_term}"
                )
                
                try:
                    data_response = requests.get(exact_url, headers=HEADERS, timeout=20)
                    if data_response.status_code != 200:
                        break
                        
                    api_data = data_response.json()
                    rows = api_data.get("Data", {}).get("row", [])
                    
                    if not rows:
                        break

                    for row in rows:
                        cat_name = row.get("rowText", "").strip()
                        columns = row.get("columns", [])
                        
                        if not cat_name or not columns:
                            continue
                            
                        processed_categories.add(cat_name)

                        for col in columns:
                            raw_month = col.get("key", "").replace(" Numeric", "").replace(" Text", "").strip()
                            formatted_month = parse_key_date(raw_month)
                            raw_value = col.get("value")
                            
                            # THE OPTIMIZATION: Instantly skip older months in memory
                            if not formatted_month or formatted_month <= latest_db_record:
                                continue
                                
                            if raw_value in (None, "", "-", "na", "NA", "s"):
                                continue
                            
                            index_value = float(raw_value)

                            # Calculate the date exactly one year ago
                            current_date = datetime.strptime(formatted_month, "%Y-%m")
                            one_year_ago_date = current_date.replace(year=current_date.year - 1)
                            one_year_ago_str = one_year_ago_date.strftime("%Y-%m")

                            # Look up the IndexValue from 1 year ago in the DB
                            past_record_statement = select(NationalCPIDB).where(
                                NationalCPIDB.Month == one_year_ago_str,
                                NationalCPIDB.Category == cat_name
                            )
                            past_record = session.exec(past_record_statement).first()

                            # Calculate YoY Change if we have historical data
                            yoy_change = None
                            if past_record and past_record.IndexValue > 0:
                                yoy_change = round(((index_value / past_record.IndexValue) - 1) * 100, 2)

                            # Because it passed the High Water Mark, check if it exists or needs updating
                            statement = select(NationalCPIDB).where(
                                NationalCPIDB.Month == formatted_month,
                                NationalCPIDB.Category == cat_name
                            )
                            existing_record = session.exec(statement).first()

                            if not existing_record:
                                session.add(NationalCPIDB(
                                    Month=formatted_month,
                                    Category=cat_name,
                                    IndexValue=index_value,
                                    YoYChange=yoy_change
                                ))
                            elif existing_record.IndexValue != index_value:
                                existing_record.IndexValue = index_value
                                existing_record.YoYChange = yoy_change
                                session.add(existing_record)
                                
                    session.commit()
                    
                    # Pagination logic
                    if len(rows) < limit:
                        break
                        
                    offset += limit
                    time.sleep(0.2)

                except Exception as e:
                    logger.error(f"Updater failed for '{target_category}': {e}")
                    session.rollback()
                    break
                    
        # 4. Final Summary
        if new_records_added > 0:
            logger.info(f"Update Complete! Successfully added {new_records_added} new CPI records.")
        else:
            logger.info("Database is already up to date. No new months found.")