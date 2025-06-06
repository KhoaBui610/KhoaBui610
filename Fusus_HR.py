from datetime import datetime

def generate_email(core_id, org, location, offline_time, camera_count):
    # Convert the offline time to a readable format
    offline_time_obj = datetime.strptime(offline_time, "%Y-%m-%dT%H:%M:%S.%fZ")
    formatted_time = offline_time_obj.strftime("%b %d, %I:%M %p") + " UTC"  # Add UTC to the formatted time

    # Clean up '--' in org and location
    org = org.replace('--', '').strip()
    location = location.replace('--', '').strip()

    # Create the email subject in the required format
    subject = f"FususCore Offline - [{org}] - [{location}] - {core_id}"

    # Create the email body
    email_body = f"""
Subject: {subject}

Hello,

Our daily health report indicates that Core {core_id} at {location} has been offline since {formatted_time}, with {camera_count} cameras connected to it.

Could you confirm if there have been any network issues or power outages at the location? A simple power cycle of the core might resolve the issue. If you require any assistance, please don’t hesitate to contact the help desk.

Thank you,
[Your Name]
[Your Contact Information]
    """
    return email_body.strip()

# Ask for input
user_input = input("Enter the details (e.g., '7c8334403553 Fulton County - GA-- Southwest Atlanta Library (SWALIB) 2025-01-09T03:14:05.584681Z 13'): ")

# Split input
parts = user_input.split()
core_id = parts[0]

# Identify where org and location end
offline_time = parts[-2]
camera_count = parts[-1]

# Parse org and location
org_location_split = " ".join(parts[1:-2]).split('--')
org = org_location_split[0].strip()
location = org_location_split[1].strip()

# Generate the email
email = generate_email(core_id, org, location, offline_time, camera_count)

# Print the generated email
print("\nGenerated Email:")
print(email)
