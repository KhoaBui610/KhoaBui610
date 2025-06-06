import requests
import time
# === User-provided Token ===
TOKEN = input('FususONE Token: ')
AUTH_HEADER = f"JWT {TOKEN[4:]}" if TOKEN.startswith("JWT ") else TOKEN
# === CONFIG ===
old_domain = "@cobbcounty.org"
new_domain = "@cobbcounty.gov"
page_size = 60
headers = {
    'accept': 'application/json, text/plain, */*',
    'authorization': AUTH_HEADER,
    'content-type': 'application/json',
    'user-agent': 'Mozilla/5.0',
    'origin': 'https://fususone.com'
}
base_url = "https://api.fususone.com/api/users/"
def fetch_all_users():
    print("[*] Fetching all users from API...")
    all_users = []
    page = 1
    while True:
        params = {
            'page': str(page),
            'page_size': str(page_size)
        }
        response = requests.get(base_url, headers=headers, params=params)
        if response.status_code != 200:
            print(f"[:x:] Failed to fetch page {page}: {response.status_code}")
            break
        data = response.json()
        results = data.get("results", [])
        if not results:
            break
        all_users.extend(results)
        print(f"[+] Page {page}: Fetched {len(results)} users")
        if len(results) < page_size:
            break
        page += 1
        time.sleep(0.25)  # small delay to avoid rate limiting
    print(f"[✓] Total users fetched: {len(all_users)}")
    return all_users
def patch_user(user_id, new_email, original_user):
    payload = {
        "id": user_id,
        "firstName": original_user.get("firstName"),
        "lastName": original_user.get("lastName"),
        "email": new_email,
        "isActive": original_user.get("isActive", True),
        "isLocked": original_user.get("isLocked", False),
        "mobilePhone": original_user.get("mobilePhone"),
        "badge": original_user.get("badge"),
        "title": original_user.get("title"),
        "officerInternalId": original_user.get("officerInternalId"),
        "groups": original_user.get("groups", []),
        "jwtRefreshExp": original_user.get("jwtRefreshExp", 9999),
        "passwordExpired": original_user.get("passwordExpired", False),
        "passwordAge": original_user.get("passwordAge", 0),
        "passwordDaysLeft": original_user.get("passwordDaysLeft", 365000),
        "isVideoWallUser": original_user.get("isVideoWallUser", False),
        "expirationDatetime": original_user.get("expirationDatetime"),
        "isShared": original_user.get("isShared", False),
        "mfaEnabled": original_user.get("mfaEnabled", False),
        "shareInfo": original_user.get("shareInfo"),
        "permissions": original_user.get("permissions", []),
        "roles": original_user.get("roles", [])
    }
    response = requests.patch(f"{base_url}{user_id}/", headers=headers, json=payload)
    if response.status_code == 200:
        print(f"[:white_check_mark:] Updated {original_user.get('firstName')} {original_user.get('lastName')}")
        return True
    else:
        print(f"[:x:] Failed to update {original_user.get('firstName')} {original_user.get('lastName')}: {response.status_code}")
        print(f"[DEBUG] Response: {response.text}")
        return False
def main():
    users = fetch_all_users()
    matching_users = [u for u in users if u.get("email", "").lower().endswith(old_domain)]
    print(f"[✓] Users matching '{old_domain}': {len(matching_users)}")
    for user in matching_users:
        user_id = user["id"]
        old_email = user["email"]
        new_email = old_email.replace(old_domain, new_domain)
        print(f"[*] Updating {old_email} -> {new_email}")
        patch_user(user_id, new_email, user)
        time.sleep(0.25)  # avoid rate limiting
if __name__ == "__main__":
    main()
