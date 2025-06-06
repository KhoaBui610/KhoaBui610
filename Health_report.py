# Khoa Bui – Unified Core Health Checker with Optional MAC Info
import requests
import urllib.parse
from datetime import datetime
import sqlite3
import os
import re

BALENA_TOKEN = "ha1qh71kOrRuUTigZpQeIIF1QR2xcosx"
FUSUS_TOKEN_FILE = "fusus_token.txt"

# === FORMAT HELPERS ===
def format_time(timestamp):
    try:
        dt = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%fZ")
        return dt.strftime("%b %d, %I:%M %p UTC")
    except:
        return timestamp or "N/A"

def parse_input_line(line):
    parts = line.strip().split('\t')
    if len(parts) != 5:
        raise ValueError(f"Invalid input format: {line}")
    return {
        "core_id": parts[0],
        "org": parts[1].replace('--', '').strip(),
        "location": parts[2].replace('--', '').strip(),
        "offline_time": parts[3],
        "camera_count": parts[4]
    }

# === BALENA ===
def get_balena_status(core_id):
    filter_str = f"device_name eq '{core_id}'"
    encoded_filter = urllib.parse.quote(filter_str)
    url = (
        f"https://api.balena-cloud.com/v7/device?"
        f"$filter={encoded_filter}"
        f"&$select=device_name,id,is_online,last_connectivity_event,overall_status"
    )
    headers = {"Authorization": f"Bearer {BALENA_TOKEN}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        devices = response.json().get("d", [])
        if devices:
            device = devices[0]
            return {
                "online": bool(device.get("is_online", False)),
                "last_seen": format_time(device.get("last_connectivity_event")),
                "overall_status": device.get("overall_status", "").lower(),
                "device_id": device.get("id")
            }
    return {"online": False, "last_seen": "N/A", "overall_status": "unknown", "device_id": None}

def get_installed_service_ids(device_id):
    headers = {"Authorization": f"Bearer {BALENA_TOKEN}"}
    url = f"https://api.balena-cloud.com/v6/service_install?$filter=device eq {device_id}&$expand=installs__service"
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return []
    service_ids = []
    for s in response.json().get("d", []):
        services = s.get("installs__service")
        if isinstance(services, dict):
            service_ids.append(services["id"])
        elif isinstance(services, list):
            for svc in services:
                service_ids.append(svc.get("id"))
    return service_ids

def get_mac_vars_for_services(service_ids):
    headers = {"Authorization": f"Bearer {BALENA_TOKEN}"}
    vars = {}
    for sid in service_ids:
        url = f"https://api.balena-cloud.com/v6/service_environment_variable?$filter=service eq {sid}"
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            for v in response.json().get("d", []):
                vars[v["name"]] = v["value"]
    return vars

# === FUSUS ===
def load_fusus_token():
    if os.path.exists(FUSUS_TOKEN_FILE):
        with open(FUSUS_TOKEN_FILE, "r") as f:
            return f.read().strip()
    return None

def save_fusus_token(token):
    with open(FUSUS_TOKEN_FILE, "w") as f:
        f.write(token)

def refresh_fusus_token(token):
    headers = {
        "authority": "api.fususone.com",
        "accept": "application/json, text/plain, */*",
        "origin": "https://fususone.com",
    }
    payload = {"token": token[4:] if token.startswith("JWT ") else token}
    try:
        response = requests.post("https://api.fususone.com/api/auth/jwt/refresh/", headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        new_token = response.json().get("token")
        if new_token:
            return "JWT " + new_token
    except Exception:
        pass
    return None

def get_fusus_status(token, core_id):
    url = f"https://api.fususone.com/api/service/camera-appliances/?search={core_id}"
    headers = {
        "Authorization": token,
        "Accept": "application/json",
        "Origin": "https://fususone.com"
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            results = response.json().get("results", [])
            if results:
                status = results[0].get("status", "Unknown")
                print(f"🟣 Fusus status for {core_id}: {status}")
                return status
        return "Unknown"
    except Exception as e:
        print(f"❌ Error checking Fusus for {core_id}: {e}")
        return "Error"
    
# === CONTACTS ===
def get_pocs_by_org(org):
    conn = sqlite3.connect("poc_contacts.db")
    c = conn.cursor()
    c.execute("SELECT name, email, phone FROM pocs WHERE org = ?", (org,))
    results = c.fetchall()
    conn.close()
    return [{
        'name': name,
        'email': email or 'N/A',
        'phone': phone or 'N/A'
    } for name, email, phone in results]

def get_location_contact(location_name, org, fusus_token):
    if not fusus_token.startswith("JWT "):
        fusus_token = "JWT " + fusus_token
    fusus_token = refresh_fusus_token(fusus_token) or fusus_token

    headers = {
        "Authorization": fusus_token,
        "Accept": "application/json"
    }

    url = f"https://api.fususone.com/api/service/locations/?search={urllib.parse.quote(location_name)}"
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()

        for loc in data.get("results", []):
            loc_name = loc.get("name", "").lower()
            loc_org = (loc.get("organization", {}).get("name") or "").strip().lower()
            if org.lower() != loc_org:
                continue
            if location_name.lower() not in loc_name and loc_name not in location_name.lower():
                continue

            return {
                "name": loc.get("contactName", "") or "N/A",
                "email": loc.get("contactEmail", "") or "N/A",
                "phone": loc.get("contactPhone", "") or "N/A"
            }
    except Exception as e:
        print(f"❌ Fusus location lookup failed: {e}")

    return None

# === EMAIL GENERATOR ===
def generate_email(entries, fusus_token):
    if not entries:
        return "✅ No cores were found offline in both systems."

    org = entries[0].get("org", "Unknown Org")
    core_count = len(entries)
    core_ids = [e["core_id"] for e in entries]
    unique_locations = list(set(e["location"] for e in entries))
    location_info = f" - [{unique_locations[0]}]" if len(unique_locations) == 1 else ""

    if core_count <= 2:
        subject = f"{core_count} FususCore{'s' if core_count > 1 else ''} Offline - [{org}]{location_info} - {' - '.join(core_ids)}"
    else:
        subject = f"{core_count} FususCores Offline - [{org}]{location_info}"

    lines = [
        f"Core {e['core_id']} at {e['location']} has been offline since {format_time(e['offline_time'])}, with {e['camera_count']} cameras connected to it."
        for e in entries
    ]

    body = f"""Subject: {subject}

Hello,

Our daily health report indicates that {core_count} Core{'s are' if core_count > 1 else ' is'} offline:\n""" + "\n".join(lines)

    body += """

Could you confirm if there have been any network issues or power outages at the location? A simple power cycle of the core might resolve the issue. If you require any assistance, please don't hesitate to contact the help desk."""

    fusus_contact = get_location_contact(entries[0]['location'], org, fusus_token)
    local_contacts = get_pocs_by_org(org)

    if fusus_contact:
        body += "\n\n📇 Fusus Contact Info:\n"
        body += f"{fusus_contact['name']}\n{fusus_contact['email']}\n{fusus_contact['phone']}\n"

    if local_contacts:
        body += "\n\n📂 Local DB Contacts:\n"
        for poc in local_contacts:
            body += f"{poc['name']}\n{poc['email']}\n{poc['phone']}\n"

    if not fusus_contact and not local_contacts:
        body += "\n\nSuggested POC: No contact on file for this org."

    return body

# === MAIN SCRIPT ===
print("🛠 Unified Core Health Checker (Balena + Fusus + Email + MAC + POC)")

use_saved = input("💾 Use saved Fusus token? (y/n): ").strip().lower() == "y"
fusus_token = load_fusus_token() if use_saved else input("Paste your JWT token: ").strip()
if not fusus_token.startswith("JWT "):
    fusus_token = "JWT " + fusus_token
fusus_token = refresh_fusus_token(fusus_token) or fusus_token
save_fusus_token(fusus_token)

print("\nPaste your tab-separated core entries (press Enter twice to finish):")
input_lines = []
while True:
    line = input()
    if line.strip() == '':
        break
    input_lines.append(line)

entries = [parse_input_line(line) for line in input_lines]
show_mac = input("🔧 Show MAC environment variables? (y/n): ").strip().lower() == 'y'

print("\n🔍 Cross-checking Balena and Fusus status...\n")
conflicts = []
confirmed_offline = []
mac_info = []

for entry in entries:
    core_id = entry["core_id"]
    balena = get_balena_status(core_id)
    fusus = get_fusus_status(fusus_token, core_id)

    is_balena_offline = balena["online"] is False
    fusus_status_clean = (fusus or "").strip().lower()
    print(f"[DEBUG] {core_id} Fusus status: {fusus_status_clean}")
    is_fusus_online = fusus_status_clean in ["connected", "online"]
    is_fusus_offline = fusus_status_clean in ["disconnected", "unreachable", "offline", "down"]

    if show_mac and balena["device_id"]:
        service_ids = get_installed_service_ids(balena["device_id"])
        vars = get_mac_vars_for_services(service_ids)
        mac_info.append({
            "core_id": core_id,
            "CAMERA_MAC_CHECK": vars.get("CAMERA_MAC_CHECK", "Not set"),
            "CAMERA_MAC_SCAN_TYPE": vars.get("CAMERA_MAC_SCAN_TYPE", "Not set")
        })

    if not is_balena_offline and is_fusus_offline:
        conflicts.append((entry, "Balena says ONLINE, Fusus says OFFLINE"))
    elif is_balena_offline and not is_fusus_offline:
        conflicts.append((entry, "Balena says OFFLINE, Fusus says ONLINE"))
    elif is_balena_offline and is_fusus_offline:
        confirmed_offline.append(entry)

if show_mac and mac_info:
    print("\n🧠 MAC Environment Variables (All Cores):\n")
    for mac in mac_info:
        print(f"  Core: {mac['core_id']}")
        print(f"    CAMERA_MAC_CHECK:     {mac['CAMERA_MAC_CHECK']}")
        print(f"    CAMERA_MAC_SCAN_TYPE: {mac['CAMERA_MAC_SCAN_TYPE']}\n")

if conflicts:
    print("⚠️ Conflict Detected:")
    for entry, message in conflicts:
        print(f" - {entry['core_id']} {entry['org']} {entry['location']}: {message}")

email_text = generate_email(confirmed_offline, fusus_token)
print("\n📨 Generated Email:\n")
print(email_text)
