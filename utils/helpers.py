import re

def format_phone(phone):
    """Format phone number to international format"""
    # Remove all non-digit characters
    phone = re.sub(r'\D', '', phone)
    
    # Add plus sign if not present
    if not phone.startswith('+'):
        phone = '+' + phone
    
    return phone

def validate_otp(otp):
    """Validate OTP format"""
    # OTP should be digits only
    return otp.isdigit()

def sanitize_message(message):
    """Sanitize message to prevent injection"""
    # Remove any potentially harmful characters
    return re.sub(r'[<>]', '', message)
