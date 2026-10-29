import time
import json
import os
from datetime import date
from google import genai
from google.genai import types
from config import settings

client = genai.Client(api_key=settings.GEMINI_API_KEY)

def extract_expense_data(user_text: str, image_bytes: bytes = None) -> dict:

    today_str = date.today().isoformat()
    
    prompt = f"""
    You are an expert financial categorization assistant for the 'SpendWise' app.
    Analyze the input (text or image) and extract ALL expense details. A single input may contain multiple distinct expenses (e.g., a one-off deposit and a recurring monthly payment).
    
    Current Date: {today_str}

    CATEGORY DEFINITIONS:
    - Transport: Ride-hailing apps, public transit, flights, gas/petrol, vehicle maintenance, and train tickets.
    - Food & Dining: Supermarkets, grocery stores, restaurants, cafes, food delivery apps, and convenience stores.
    - Shopping: E-commerce platforms, clothing, electronics, and general retail.
    - Utilities: Phone bills, internet, electricity, water, and subscriptions (e.g., streaming).
    - Healthcare: Pharmacies, doctor visits, and medical supplies.

    INSTRUCTIONS:
    1. If the input is a greeting, a question, or conversational (e.g., "Hello"), set "IsValidExpense" to false and leave the "Expenses" list empty.
    2. If expenses are found, set "IsValidExpense" to true and extract each distinct item or payment structure into the "Expenses" list.
    3. Briefly explain what each specific item/service is in the "Reasoning" field.
    4. Provide a clean, readable "ItemName".
    5. DATE RULE: If the user mentions a specific day (e.g., "yesterday", "Tuesday", "April 12"), calculate the exact "DatePurchased" based on the Current Date. If no date is mentioned, use the Current Date.
    
    Return ONLY a valid JSON object matching this schema exactly:
    {{
        "IsValidExpense": boolean,
        "Expenses": [
            {{
                "Reasoning": "Briefly explain what the purchased item/service is",
                "Type": "Must be exactly one of: Food & Dining, Transport, Utilities, Entertainment, Shopping, Healthcare, Other",
                "ItemName": "Short, clear descriptive name",
                "AmountSpent": float,
                "Recurring": boolean,
                "DatePurchased": "YYYY-MM-DD",
                "Note": "Any extra details provided by the user"
            }}
        ]
    }}
    """
    
    contents = [prompt, user_text]
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash", 
                contents=contents
            )
            clean_json = response.text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_json)
            
        except Exception as e:
            error_str = str(e)
            print(f"Attempt {attempt + 1} failed: {error_str}")
            
            # Check if it is the 429 Quota Error
            if "429" in error_str and attempt < max_retries - 1:
                print("⏳ Rate limit hit. Waiting 15 seconds before retrying...")
                time.sleep(15) # Wait before trying the loop again
            else:
                # If it's a different error, or we ran out of retries, give up
                return None
