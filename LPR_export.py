#Developed by Khoa Bui. This is the newest version that bypasses API limitation  
import requests
import csv
import os
from datetime import datetime, timedelta
from tqdm import tqdm
import pytz
import time

# === CONFIGURATION ===
TOKEN_FILE = "fusus_token.txt"
LPR_API_URL = "https://lpr-api.fususone.com/api/reads/"

# Load token
def load_token():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            return f.read().strip()
    return None

# Save token
def save_token(token):
    with open(TOKEN_FILE, "w") as f:
        f.write(token)

# Refresh token explicitly
def refresh_token(token):
    headers = {
        "Origin": "https://fususone.com",
        "Content-Type": "application/json"
    }
    payload = {"token": token[4:] if token.startswith("JWT ") else token}
    response = requests.post(
        "https://api.fususone.com/api/auth/jwt/refresh/",
        headers=headers,
        json=payload,
        timeout=15
    )
    response.raise_for_status()
    new_token = response.json().get("token")
    if new_token:
        print("✅ Token refreshed successfully.\n")
        return "JWT " + new_token
    raise Exception("Token refresh failed.")

# Date range selection
def get_date_range(choice):
    utc = pytz.utc
    et = pytz.timezone('America/New_York')
    end_date = datetime.utcnow().replace(tzinfo=utc)

    if choice == "7":
        from_input = input("Enter the FROM date/time (MM/DD/YYYY HH:MM AM/PM): ").strip()
        to_input = input("Enter the TO date/time (MM/DD/YYYY HH:MM AM/PM): ").strip()

        from_date_et = et.localize(datetime.strptime(from_input, "%m/%d/%Y %I:%M %p"))
        to_date_et = et.localize(datetime.strptime(to_input, "%m/%d/%Y %I:%M %p"))

        return from_date_et.astimezone(utc), to_date_et.astimezone(utc)

    choices = {
        "1": timedelta(hours=2),
        "2": timedelta(days=1),
        "3": timedelta(days=2),
        "4": timedelta(days=7),
        "5": timedelta(days=14),
        "6": timedelta(days=30)
    }
    delta = choices.get(choice, timedelta(hours=2))
    return end_date - delta, end_date

# Fetch LPR data with pagination and filters
def fetch_lpr_data(token, from_date, to_date, filters, search_reason):
    headers = {
        "Authorization": token,
        "Accept": "application/json",
        "Origin": "https://fususone.com",
        "Referer": "https://fususone.com/",
        "User-Agent": "Mozilla/5.0"
    }

    results = []
    current_from_date = from_date
    chunk_size = timedelta(minutes=10)  # Chunk size for queries

    while current_from_date < to_date:
        current_to_date = min(current_from_date + chunk_size, to_date)
        params = {
            "page": 1,
            "search_reason": "Automated Script",
            "event_timestamp_from": current_from_date.isoformat(),
            "event_timestamp_to": current_to_date.isoformat(),
            "ordering": "-event_timestamp",
            "size": 100,
            **filters
        }

        retries = 3
        with tqdm(desc=f"Fetching {current_from_date.strftime('%Y-%m-%d %H:%M:%S')} to {current_to_date.strftime('%Y-%m-%d %H:%M:%S')}", unit="page") as pbar:
            while True:
                for attempt in range(retries):
                    response = requests.get(LPR_API_URL, headers=headers, params=params)
                    if response.status_code == 200:
                        break
                    time.sleep(5)
                else:
                    params["page"] += 1
                    continue

                data = response.json()
                items = data.get("items", [])
                if not items:
                    break

                results.extend(items)
                params["page"] += 1
                pbar.set_postfix_str(f"Total Records: {len(results)}")
                pbar.update(1)

        current_from_date = current_to_date

    return results

# Export to CSV without duplicates
def export_to_csv(lpr_data, filename):
    print(f"\n💾 Exporting {len(lpr_data)} records to {filename}")
    seen = set()
    with open(filename, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Plate", "Plate State", "Timestamp", "Vehicle Make", "Vehicle Color", "Camera Name", "Coordinates", "Image URL"])

        for entry in lpr_data:
            unique_key = (entry.get("plate"), entry.get("event_timestamp"), entry.get("camera_name"))
            if unique_key in seen:
                continue
            seen.add(unique_key)

            media = entry.get('media', [{}])
            image_url = media[0].get('url', '') if media else ''

            writer.writerow([
                entry.get("plate", ""),
                entry.get("plate_state", ""),
                entry.get("event_timestamp", ""),
                entry.get("vehicle_make", ""),
                entry.get("vehicle_color", ""),
                entry.get("camera_name", ""),
                entry.get("geometry", {}).get("coordinates", []),
                image_url
            ])

    print("✅ Export complete!")


# Main execution
if __name__ == "__main__":
    token = None
    if os.path.exists(TOKEN_FILE):
        use_saved = input("💾 Use saved token? (y/n): ").strip().lower()
        if use_saved == "y":
            token = load_token()

    if not token:
        token = input("🔑 Paste your JWT token: ").strip()
        if not token.startswith("JWT "):
            token = "JWT " + token

    token = refresh_token(token)
    save_token(token)

    print("\nSelect Time Range:")
    print("1. Last 2 hours")
    print("2. Last 24 hours")
    print("3. Last 48 hours")
    print("4. Last 7 days")
    print("5. Last 14 days")
    print("6. Last 30 days")
    print("7. Custom date/time")
    choice = input("Enter your choice (1-7): ").strip()

    from_date, to_date = get_date_range(choice)

    search_reason = input("Enter search reason: ").strip()

    filters = {}
    vehicle_make = input("Filter by Vehicle Make (leave blank if none): ").strip()
    if vehicle_make:
        filters["vehicle_make"] = vehicle_make

    vehicle_color = input("Filter by Vehicle Color (leave blank if none): ").strip()
    if vehicle_color:
        filters["vehicle_color"] = vehicle_color

    license_plate = input("Filter by License Plate (leave blank if none): ").strip()
    if license_plate:
        filters["plate"] = license_plate

    plate_state = input("Filter by Plate State (leave blank if none): ").strip()
    if plate_state:
        filters["plate_state"] = plate_state

    lpr_data = fetch_lpr_data(token, from_date, to_date, filters, search_reason)

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"C:/Users/kbui/Downloads/lpr_data_export_{timestamp}.csv"
    export_to_csv(lpr_data, filename)  
