import requests
import os
import csv
import time
from datetime import datetime

# === CONFIGURATION ===
TOKEN_FILE = "fusus_token.txt"
CAMERA_API_URL = "https://api.fususone.com/api/cameras/"
EXPORT_FOLDER = r"C:/Users/kbui/Downloads"

# === TOKEN HANDLING ===
def load_token():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            return f.read().strip()
    return None

def save_token(token):
    with open(TOKEN_FILE, "w") as f:
        f.write(token)

def refresh_token(token):
    headers = {
        "Origin": "https://fususone.com",
        "Content-Type": "application/json"
    }
    payload = {"token": token[4:] if token.startswith("JWT ") else token}
    try:
        print("🔁 Refreshing token...")
        response = requests.post(
            CAMERA_API_URL.replace("/cameras/", "/auth/jwt/refresh/"),
            headers=headers,
            json=payload,
            timeout=15
        )
        response.raise_for_status()
        new_token = response.json().get("token")
        if new_token:
            print("✅ Token refreshed successfully.\n")
            return "JWT " + new_token
    except Exception as e:
        print(f"❌ Token refresh failed: {e}")
    return token

# === CAMERA FETCH FUNCTION WITH INFINITE RETRIES ===
def fetch_all_shared_cameras(token):
    headers = {
        "Authorization": token,
        "Accept": "application/json",
        "Origin": "https://fususone.com"
    }

    page = 1
    page_size = 20
    all_cameras = []

    while True:
        print(f"📄 Fetching page {page}...")
        params = {
            "isOwned": "false",
            "ordering": "name",
            "page": page,
            "pageSize": page_size
        }

        success = False
        while not success:
            try:
                response = requests.get(CAMERA_API_URL, headers=headers, params=params, timeout=30)
                if response.status_code == 401:
                    print(f"🔐 401 Unauthorized. Refreshing token and retrying...")
                    token = refresh_token(token)
                    headers["Authorization"] = token
                    save_token(token)
                    continue
                if response.status_code == 404:
                    print(f"✅ Reached end of pages at page {page}.")
                    return all_cameras

                response.raise_for_status()
                data = response.json()
                results = data.get("results", [])
                if not results:
                    print("✅ No more cameras found. Done!")
                    return all_cameras

                all_cameras.extend(results)
                success = True
            except requests.exceptions.RequestException as e:
                print(f"⚠️ Error fetching page {page}: {e}")
                print("⏳ Waiting 5 seconds and retrying...")
                time.sleep(5)

        page += 1

# === CSV EXPORT FUNCTION ===
def export_to_csv(cameras, export_path):
    print(f"\n💾 Exporting {len(cameras)} cameras to {export_path}...")
    try:
        with open(export_path, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["Camera Name", "Status", "ID", "IP Address", "Location"])
            for cam in cameras:
                writer.writerow([
                    cam.get("name", ""),
                    cam.get("status", ""),
                    cam.get("id", ""),
                    cam.get("ip_address", "N/A"),
                    (cam.get("location") or {}).get("name", "")
                ])
        print("✅ Export complete!")
    except Exception as e:
        print(f"❌ Failed to export CSV: {e}")

# === MAIN ===
if __name__ == "__main__":
    print("📦 Fusus - Full Shared Camera Export (Reliable Mode)")

    token = None
    if os.path.exists(TOKEN_FILE):
        use_saved = input("💾 Use saved token from fusus_token.txt? (y/n): ").strip().lower()
        if use_saved == "y":
            token = load_token()

    if not token:
        token = input("🔑 Paste your JWT token: ").strip()
        if not token.startswith("JWT "):
            token = "JWT " + token

    token = refresh_token(token)
    save_token(token)

    cameras = fetch_all_shared_cameras(token)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename = f"shared_cameras_full_export_{timestamp}.csv"
    full_path = os.path.join(EXPORT_FOLDER, filename)

    export_to_csv(cameras, full_path)
