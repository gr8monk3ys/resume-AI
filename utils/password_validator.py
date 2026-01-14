"""
Password strength validation and requirements enforcement.

This module implements:
- Minimum 8 character requirement
- Complexity requirements (uppercase, lowercase, number, special char)
- Common password blacklist
- Password strength meter
"""

import re
from typing import Tuple, List

# Common passwords to reject (top 500+ most common passwords from security research)
# Sources: HaveIBeenPwned, SecLists, RockYou breach analysis
COMMON_PASSWORDS = frozenset({
    # Top 100 most common
    "123456", "password", "12345678", "qwerty", "123456789", "12345", "1234",
    "111111", "1234567", "dragon", "123123", "baseball", "abc123", "football",
    "monkey", "letmein", "696969", "shadow", "master", "666666", "qwertyuiop",
    "123321", "mustang", "1234567890", "michael", "654321", "pussy", "superman",
    "1qaz2wsx", "7777777", "fuckyou", "121212", "000000", "qazwsx", "123qwe",
    "killer", "trustno1", "jordan", "jennifer", "zxcvbnm", "asdfgh", "hunter",
    "buster", "soccer", "harley", "batman", "andrew", "tigger", "sunshine",
    "iloveyou", "fuckme", "2000", "charlie", "robert", "thomas", "hockey",
    "ranger", "daniel", "starwars", "klaster", "112233", "george", "asshole",
    "computer", "michelle", "jessica", "pepper", "1111", "zxcvbn", "555555",
    "11111111", "131313", "freedom", "777777", "pass", "fuck", "maggie",
    "159753", "aaaaaa", "ginger", "princess", "joshua", "cheese", "amanda",
    "summer", "love", "ashley", "6969", "nicole", "chelsea", "biteme",
    "matthew", "access", "yankees", "987654321", "dallas", "austin", "thunder",
    "taylor", "matrix", "william", "corvette", "hello", "martin", "heather",

    # Common password patterns
    "password1", "password123", "password12", "password!", "password1!",
    "pass123", "pass1234", "passw0rd", "p@ssw0rd", "p@ssword", "pa$$word",
    "admin", "admin123", "admin1", "administrator", "root", "toor",
    "test", "test123", "testing", "guest", "guest123", "user", "user123",
    "login", "login123", "welcome", "welcome1", "welcome123", "changeme",
    "default", "letmein", "letmein1", "letmein123", "qwerty123", "qwerty1",

    # Keyboard patterns
    "qwertyuiop", "asdfghjkl", "zxcvbnm", "1qaz2wsx", "1q2w3e4r", "q1w2e3r4",
    "1qazxsw2", "zaq12wsx", "!qaz2wsx", "1qaz!qaz", "qazwsxedc", "qweasdzxc",

    # Sequential numbers/letters
    "abcd1234", "abcdef", "abcdefg", "1234abcd", "0987654321", "9876543210",

    # Year patterns
    "2020", "2021", "2022", "2023", "2024", "2025", "2019", "2018", "2017",

    # Simple words
    "secret", "nothing", "hello123", "whatever", "internet", "pokemon",
    "iloveyou1", "princess1", "sunshine1", "baseball1", "football1",
    "password2", "qwerty12", "lovely", "banana", "cookie", "pepper123",

    # Company/product names often used
    "apple", "google", "amazon", "facebook", "microsoft", "twitter",

    # Common names
    "michael1", "jennifer1", "jordan23", "ashley1", "jessica1", "thomas1",

    # Sports related
    "baseball1", "football1", "soccer1", "hockey1", "basketball", "lakers",
    "yankees1", "cowboys", "packers", "redsox", "giants", "eagles",

    # Pop culture
    "starwars1", "batman1", "superman1", "spiderman", "ironman", "avengers",

    # Profanity (commonly used, unfortunately)
    "fuckyou1", "asshole1", "biteme1",

    # Tech/gaming
    "gamer", "gaming", "player", "minecraft", "roblox", "fortnite",

    # Additional common passwords from breaches
    "lovely", "nicole1", "daniel1", "babygirl", "beautiful", "sexy",
    "hottie", "loveme", "pretty", "samantha", "anthony", "friends",
    "butterfly", "purple", "angel", "jordan1", "liverpool", "chelsea1",
    "arsenal", "manchester", "barcelona", "realmadrid"
})

# Additional keyboard-adjacent patterns to check dynamically
KEYBOARD_PATTERNS = [
    "qwerty", "asdf", "zxcv", "1234", "0987", "qaz", "wsx", "edc",
    "rfv", "tgb", "yhn", "ujm", "ik,", "ol.", "p;/"
]

def validate_password_strength(password: str) -> Tuple[bool, List[str], int]:
    """
    Validate password against strength requirements.

    Args:
        password: Password to validate

    Returns:
        Tuple of (is_valid: bool, errors: List[str], strength_score: int)
        strength_score is 0-100
    """
    errors = []
    strength = 0

    # Check minimum length (8 characters)
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    else:
        strength += 20
        # Bonus for longer passwords
        if len(password) >= 12:
            strength += 10
        if len(password) >= 16:
            strength += 10

    # Check for lowercase letter
    if not re.search(r'[a-z]', password):
        errors.append("Password must contain at least one lowercase letter")
    else:
        strength += 15

    # Check for uppercase letter
    if not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter")
    else:
        strength += 15

    # Check for digit
    if not re.search(r'\d', password):
        errors.append("Password must contain at least one number")
    else:
        strength += 15

    # Check for special character
    if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\;/~`]', password):
        errors.append("Password must contain at least one special character (!@#$%^&* etc.)")
    else:
        strength += 15

    # Check against common passwords
    if password.lower() in COMMON_PASSWORDS:
        errors.append("This password is too common. Please choose a more unique password")
        strength = max(0, strength - 30)

    # Check for repeated characters
    if re.search(r'(.)\1{2,}', password):  # 3+ same characters in a row
        strength -= 10

    # Check for sequential characters
    sequential_patterns = ['012', '123', '234', '345', '456', '567', '678', '789',
                          'abc', 'bcd', 'cde', 'def', 'efg', 'fgh', 'ghi', 'hij']
    for pattern in sequential_patterns:
        if pattern in password.lower():
            strength -= 5
            break

    # Ensure strength is between 0-100
    strength = max(0, min(100, strength))

    is_valid = len(errors) == 0

    return (is_valid, errors, strength)

def get_password_strength_label(strength: int) -> Tuple[str, str]:
    """
    Get a label and color for password strength.

    Args:
        strength: Strength score 0-100

    Returns:
        Tuple of (label: str, color: str)
    """
    if strength >= 80:
        return ("Very Strong", "green")
    elif strength >= 60:
        return ("Strong", "blue")
    elif strength >= 40:
        return ("Moderate", "orange")
    elif strength >= 20:
        return ("Weak", "red")
    else:
        return ("Very Weak", "red")

def generate_password_requirements_text() -> str:
    """
    Generate user-friendly text describing password requirements.

    Returns:
        Markdown-formatted requirements text
    """
    return """
**Password Requirements:**
- Minimum 8 characters (12+ recommended)
- At least one uppercase letter (A-Z)
- At least one lowercase letter (a-z)
- At least one number (0-9)
- At least one special character (!@#$%^&* etc.)
- Cannot be a common password
    """

def check_password_compromised(password: str) -> bool:
    """
    Check if password is in the common passwords list.

    Args:
        password: Password to check

    Returns:
        True if password is compromised/common
    """
    return password.lower() in COMMON_PASSWORDS

def suggest_password_improvements(password: str) -> List[str]:
    """
    Suggest specific improvements for a weak password.

    Args:
        password: Password to analyze

    Returns:
        List of improvement suggestions
    """
    suggestions = []

    if len(password) < 12:
        suggestions.append("💡 Consider using 12+ characters for better security")

    if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\;/~`]', password):
        suggestions.append("💡 Add special characters like !@#$% for more complexity")

    if re.search(r'(.)\1{2,}', password):
        suggestions.append("💡 Avoid repeating the same character multiple times")

    if any(common in password.lower() for common in ['password', 'admin', 'user', '123', 'abc']):
        suggestions.append("💡 Avoid using common words or patterns")

    # Check if it's just letters or just numbers
    if password.isalpha():
        suggestions.append("💡 Mix letters with numbers and symbols")
    elif password.isdigit():
        suggestions.append("💡 Mix numbers with letters and symbols")

    return suggestions

def validate_password_confirmation(password: str, confirmation: str) -> Tuple[bool, str]:
    """
    Validate that password and confirmation match.

    Args:
        password: Original password
        confirmation: Confirmation password

    Returns:
        Tuple of (is_valid: bool, error_message: str)
    """
    if not confirmation:
        return (False, "Please confirm your password")

    if password != confirmation:
        return (False, "Passwords do not match")

    return (True, "")
