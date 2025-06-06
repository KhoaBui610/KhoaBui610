# Fusus – Location Sharing Script with Dual Token Support (Support + One + Fallback)

import requests
import os

# === CONFIG ===
SUPPORT_TOKEN_FILE = "fusus_support_token.txt"
ONE_TOKEN_FILE = "fusus_one_token.txt"
ORG_LOOKUP_URL = "https://api.fususone.com/api/organizations/"
LOCATION_LIST_URL = "https://api.fususone.com/api/locations/"
SHARE_URL_TEMPLATE = "https://api.fususone.com/api/locations/{}/shares/"

# === TOKEN HANDLERS ===
def load_token(filename):
    if os.path.exists(filename):
        with open(filename, "r") as f:
            return f.read().strip()
    return None

def save_token(filename, token):
    with open(filename, "w") as f:
        f.write(token)

def refresh_token(token):
    headers = {
        "Origin": "https://fususone.com",
        "Content-Type": "application/json"
    }
    payload = {"token": token[4:] if token.startswith("JWT ") else token}
    try:
        print("🔁 Refreshing token...")
        response = requests.post("https://api.fususone.com/api/auth/jwt/refresh/", headers=headers, json=payload)
        response.raise_for_status()
        new_token = response.json().get("token")
        if new_token:
            print("✅ Token refreshed successfully.")
            return "JWT " + new_token
    except Exception as e:
        print(f"❌ Token refresh failed: {e}")
    return token

# === ORG LOOKUP ===
def get_org_id(token_support, token_one, org_name):
    headers_support = {
        "Authorization": token_support,
        "Accept": "application/json",
        "Origin": "https://www.fusussupport.com",
        "Referer": "https://www.fusussupport.com/",
        "User-Agent": "Mozilla/5.0"
    }
    params = {"search": org_name, "page": 1, "page_size": 100}
    try:
        response = requests.get("https://api.fususone.com/api/service/organizations/brief/", headers=headers_support, params=params)
        response.raise_for_status()
        results = response.json().get("results", [])
        for org in results:
            if org_name.lower() in org.get("name", "").lower():
                return org.get("id"), org.get("name")
    except Exception as e:
        print(f"⚠️ Support org lookup failed, falling back: {e}")

    # Fallback to /organizations/ with One token
    headers_one = {
        "Authorization": token_one,
        "Accept": "application/json"
    }
    try:
        response = requests.get(ORG_LOOKUP_URL, headers=headers_one, params={"search": org_name, "page": 1, "pageSize": 100})
        response.raise_for_status()
        results = response.json().get("results", [])
        for org in results:
            if org_name.lower() in org.get("name", "").lower():
                return org.get("id"), org.get("name")
    except Exception as e:
        print(f"❌ Fallback org lookup also failed: {e}")

    return None, None

# === LOCATION LOOKUP ===
def get_location_ids(token, location_names):
    headers = {"Authorization": token, "Accept": "application/json"}
    page = 1
    all_locations = []
    while True:
        try:
            response = requests.get(LOCATION_LIST_URL, headers=headers, params={"page": page, "pageSize": 100})
            if response.status_code == 404:
                break
            response.raise_for_status()
            results = response.json().get("results", [])
            if not results:
                break
            all_locations.extend(results)
            page += 1
        except Exception as e:
            print(f"❌ Error fetching locations: {e}")
            break

    matched = {}
    not_found = []
    for name in location_names:
        found = False
        for loc in all_locations:
            if loc.get("name") == name:
                matched[name] = loc.get("id")
                found = True
                break
        if not found:
            not_found.append(name)
    return matched, not_found

# === SHARE LOCATION ===
def share_location(token, org_id, location_id, location_name, perms):
    url = SHARE_URL_TEMPLATE.format(location_id)
    headers = {
        "Authorization": token,
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Origin": "https://fususone.com"
    }
    payload = {
        "target_organization": org_id,
        "permissions": "View",
        "isAdminOnly": perms["is_admin_only"],
        "permissionsDetails": {
            "viewLiveVideo": perms["view_live"],
            "viewPlayback": perms["view_playback"],
            "enablePtzControl": perms["ptz_control"]
        }
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code in [200, 201]:
            print(f"✅ Shared location '{location_name}' successfully.")
        elif response.status_code == 400 and "already shared" in response.text.lower():
            print(f"ℹ️ Location '{location_name}' is already shared with the org.")
        else:
            print(f"❌ Failed to share '{location_name}': {response.text}")
    except Exception as e:
        print(f"❌ Error sharing '{location_name}': {e}")

# === MAIN ===
print("🚀 Fusus – Share Locations with Access Options (Dual Token with Fallback)")

# Load FususSupport token
support_token = None
if os.path.exists(SUPPORT_TOKEN_FILE):
    use_support_saved = input("💾 Use saved FususSupport token? (y/n): ").strip().lower()
    if use_support_saved == "y":
        support_token = load_token(SUPPORT_TOKEN_FILE)

if not support_token:
    support_token = input("🔑 Enter your FususSupport JWT token: ").strip()
    if not support_token.startswith("JWT "):
        support_token = "JWT " + support_token
    save_token(SUPPORT_TOKEN_FILE, support_token)

# Load FususOne token
one_token = None
if os.path.exists(ONE_TOKEN_FILE):
    use_one_saved = input("💾 Use saved FususOne token? (y/n): ").strip().lower()
    if use_one_saved == "y":
        one_token = load_token(ONE_TOKEN_FILE)

if not one_token:
    one_token = input("🔑 Enter your FususOne JWT token: ").strip()
    if not one_token.startswith("JWT "):
        one_token = "JWT " + one_token
    save_token(ONE_TOKEN_FILE, one_token)

one_token = refresh_token(one_token)
save_token(ONE_TOKEN_FILE, one_token)

org_name = input("🏢 Enter target organization name (to share with): ").strip()
location_names = []
print("\n📍 Enter location name(s) (one per line). Press Enter twice to finish:")
while True:
    line = input().strip()
    if not line:
        break
    location_names.append(line)

print("\n🎛️ Set access options:")
view_live = input("👁️  Allow live video? (y/n): ").strip().lower() == "y"
view_playback = input("⏪ Allow playback access? (y/n): ").strip().lower() == "y"
ptz_control = input("🎮 Allow PTZ control? (y/n): ").strip().lower() == "y"
is_admin_only = input("🔒 Restrict to admin-only access? (y/n): ").strip().lower() == "y"

permissions = {
    "view_live": view_live,
    "view_playback": view_playback,
    "ptz_control": ptz_control,
    "is_admin_only": is_admin_only
}

print("\n🔍 Looking up organization and location IDs...")
org_id, matched_org_name = get_org_id(support_token, one_token, org_name)
matched_locations, not_found_locations = get_location_ids(one_token, location_names)

if not org_id:
    print("❌ Target organization not found. Aborting.")
    exit()
if not matched_locations:
    print("❌ No valid locations found. Aborting.")
    exit()

print(f"\n✅ Organization found: {matched_org_name} (ID: {org_id})")
print("📍 Locations to be shared:")
for name, loc_id in matched_locations.items():
    print(f" - {name} → ID: {loc_id}")

if not_found_locations:
    print("\n⚠️ The following location(s) were not found or not owned by your org:")
    for name in not_found_locations:
        print(f" - {name}")

confirm = input("\n🛑 Proceed with sharing these locations? (y/n): ").strip().lower()
if confirm != "y":
    print("❌ Operation canceled.")
    exit()

print("\n🚀 Sharing locations...")
for name, loc_id in matched_locations.items():
    share_location(one_token, org_id, loc_id, name, permissions)

print("\n✅ All done.")
