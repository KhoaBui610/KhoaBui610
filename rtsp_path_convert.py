import urllib.parse

def escape_password(password):
    """
    Escapes only problematic characters in the password for RTSP compatibility with ffprobe.
    """
    # Characters to keep as is (safe for ffprobe)
    safe_characters = "!$-_.+!*'(),~"

    # Escape the password, leaving safe characters untouched
    escaped_password = urllib.parse.quote(password, safe=safe_characters)

    return escaped_password

# Prompt the user for the password
password = input("Enter the password to escape for RTSP: ")

# Escape the password
escaped_password = escape_password(password)

# Display the results
print("\nOriginal Password:")
print(password)
print("\nEscaped Password:")
print(escaped_password)
