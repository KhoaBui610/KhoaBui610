import requests
import os
import time

TOKEN_FILE = "fusus_token.txt"

# === TOKEN MANAGEMENT FUNCTIONS ===
def save_token(token):
    with open(TOKEN_FILE, "w") as f:
        f.write(token)

def load_token():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            return f.read().strip()
    return None

def refresh_token(token):
    headers = {
        "authority": "api.fususone.com",
        "accept": "application/json, text/plain, */*",
        "origin": "https://fususone.com",
    }
    payload = {"token": token[4:] if token.startswith("JWT ") else token}

    try:
        print("\n🔁 Refreshing token...")
        response = requests.post(
            "https://api.fususone.com/api/auth/jwt/refresh/",
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        new_token = response.json().get("token")
        if new_token:
            print("✅ Token successfully refreshed.\n")
            return "JWT " + new_token
    except Exception as e:
        print(f"❌ Token refresh failed: {e}")
    return None

# === CORE CHECK FUNCTIONS ===
def check_core_ai(token, core_id):
    url = f"https://api.fususone.com/api/service/camera-appliances/?search={core_id}"
    headers = {"Authorization": token, "Accept": "application/json", "Origin": "https://fususone.com"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    results = response.json().get("results", [])
    if results:
        base_type = results[0].get('baseType', {}).get('id')
        is_ai = base_type in [4, 8]
        ai_types = results[0].get('supportedAiDetections', [])
        return is_ai, ai_types
    return False, []

def check_core_cameras(token, core_id):
    url = f"https://api.fususone.com/api/service/camera/?appliance_sn__icontains={core_id}&page_size=60"
    headers = {"Authorization": token, "Accept": "application/json", "Origin": "https://fususone.com"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    results = response.json().get("results", [])
    return results

def enable_ai_on_camera(token, camera_id, ai_settings):
    url = f"https://api.fususone.com/api/service/camera/{camera_id}/"
    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
        "Origin": "https://fususone.com"
    }

    payload = {
        "isAiEnabled": True,
        "aiDetectionTypes": [{
            "id": ai_settings["id"],
            "confidence": ai_settings.get("confidence", 50),
            "detectionTimeout": ai_settings.get("detectionTimeout", 100),
            "labels": ai_settings.get("labels", []),
            "roi": ai_settings.get("roi", []),
            "schedules": ai_settings.get("schedules", [
                "* * * * 0", "* * * * 1", "* * * * 2",
                "* * * * 3", "* * * * 4", "* * * * 5", "* * * * 6"
            ]),
            "type": ai_settings.get("type")
        }],
        "aiFrameTimeout": 500,
        "aiImageCompression": 40,
        "aiPullCamera": False,
        "aiStreamType": 0
    }

    response = requests.patch(url, json=payload, headers=headers)
    try:
        response.raise_for_status()
        return response.ok
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP Error ({response.status_code}): {response.text}")
        print(f"Payload sent:\n{payload}")
        return False


# === MAIN EXECUTION ===
if __name__ == "__main__":
    token = None

    if os.path.exists(TOKEN_FILE):
        use_saved = input("💾 Use saved token from fusus_token.txt? (y/n): ").strip().lower()
        if use_saved == "y":
            token = load_token()
            token = refresh_token(token) or token

    if not token:
        token = input("Paste your fresh JWT token from DevTools: ").strip()
        if not token.startswith("JWT "):
            token = "JWT " + token
        save_token(token)

    core_id = input("Enter core ID to check and configure AI: ").strip()

    print(f"\n🔍 Checking core: {core_id}")
    is_ai, ai_types = check_core_ai(token, core_id)
    print(f"   AI Core: {'✅ Yes' if is_ai else '❌ No'}")

    if not is_ai:
        print("⚠️ Core is not AI-enabled. Exiting.")
        exit()

    cameras = check_core_cameras(token, core_id)
    ai_enabled_cameras = [cam for cam in cameras if cam['isAiEnabled']]
    non_ai_cameras = [cam for cam in cameras if not cam['isAiEnabled']]

    print(f"   Total Cameras: {len(cameras)}")
    print(f"   AI-enabled Cameras: {len(ai_enabled_cameras)}")
    print(f"   Cameras without AI: {len(non_ai_cameras)}")

    count_to_enable = int(input("How many cameras do you want to enable AI on?: ").strip())
    if count_to_enable > len(non_ai_cameras):
        print(f"⚠️ Only {len(non_ai_cameras)} cameras available without AI. All will be enabled.")
        count_to_enable = len(non_ai_cameras)

    print("\nAvailable AI Detection Types:")
    for idx, det in enumerate(ai_types):
        print(f"{idx + 1}. {det['name']}")

    choice = int(input("Choose detection type number: ").strip()) - 1
    selected_ai = ai_types[choice]

    labels_choice = input("Labels (basic/advance/no label): ").strip().lower()

    labels = []
    if labels_choice == 'advance':
        print("\nAvailable Labels (choose by number, comma-separated):")
        for idx, lbl in enumerate(selected_ai['allowedLabels']):
            print(f"{idx + 1}. {lbl}")
        label_indices = input("Enter label numbers: ").strip()
        indices = [int(i) - 1 for i in label_indices.split(',')]
        labels = [selected_ai['allowedLabels'][i] for i in indices]

    schedule_choice = input("Schedule (entire day/office hours/after hours/custom): ").strip().lower()
if schedule_choice == "entire day":
    schedules = ["* * * * 0", "* * * * 1", "* * * * 2", "* * * * 3", "* * * * 4", "* * * * 5", "* * * * 6"]
elif schedule_choice == "office hours":
    schedules = ["0 9-17 * * 1-5"]
elif schedule_choice == "after hours":
    schedules = ["0 0-9,17-24 * * 1-5", "* * * * 6", "* * * * 0"]
else:
    custom_schedule_input = input("Enter custom cron schedule(s), comma-separated: ").strip()
    if custom_schedule_input:
        schedules = [s.strip() for s in custom_schedule_input.split(',') if s.strip()]
        if not schedules:
            print("⚠️ No valid schedules entered. Defaulting to entire day.")
            schedules = ["* * * * 0", "* * * * 1", "* * * * 2", "* * * * 3", "* * * * 4", "* * * * 5", "* * * * 6"]
    else:
        print("⚠️ No schedules entered. Defaulting to entire day.")
        schedules = ["* * * * 0", "* * * * 1", "* * * * 2", "* * * * 3", "* * * * 4", "* * * * 5", "* * * * 6"]

    ai_settings = {
        "id": selected_ai['id'],
        "type": selected_ai['type'],
        "confidence": 50,
        "detectionTimeout": 100,
        "labels": labels,
        "roi": [],
        "schedules": schedules
    }

    confirm = input("Proceed with enabling AI? (y/n): ").strip().lower()
    if confirm == 'y':
        enabled_cameras = []
        for cam in non_ai_cameras[:count_to_enable]:
            try:
                if enable_ai_on_camera(token, cam['id'], ai_settings):
                    enabled_cameras.append(cam['name'])
                    print(f"✅ AI enabled on {cam['name']}")
            except Exception as e:
                print(f"❌ Error enabling AI on {cam['name']}: {e}")
            time.sleep(1)

        if enabled_cameras:
            print("\nAI enabled on the following cameras:")
            for cam_name in enabled_cameras:
                print(f"- {cam_name}")
        else:
            print("⚠️ No cameras were enabled due to errors.")
    else:
        print("Operation cancelled.")
