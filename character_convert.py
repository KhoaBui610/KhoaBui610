def convert_special_to_hex(text):
    result = ''
    for char in text:
        # Check if the character is a special character
        if not char.isalnum():  # If not alphanumeric, it's a special character
            result += '%' + format(ord(char), 'x')  # Convert to hex
        else:
            result += char
    return result

# Prompt the user for a password input
password_input = input("Please enter the password to be converted: ")

# Convert the password's special characters to hex
converted_password = convert_special_to_hex(password_input)

# Output the converted result
print(f"Converted password: {converted_password}")

# Pause at the end to allow the user to copy the result
input("Press Enter to exit after copying the converted password...")
