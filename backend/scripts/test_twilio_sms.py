"""
Test Twilio SMS Integration

Simple standalone script to test Twilio SMS sending.
Run from the backend directory:
    python scripts/test_twilio_sms.py
"""
import os
import sys
from pathlib import Path

# Add the backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Load environment variables from .env
from dotenv import load_dotenv
load_dotenv(backend_dir / ".env")

def test_twilio_sms():
    """Test sending SMS via Twilio."""
    
    # Print configuration (mask sensitive data)
    print("=" * 60)
    print("TWILIO SMS TEST")
    print("=" * 60)
    
    # Get credentials from environment
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_FROM_NUMBER")
    to_number = os.getenv("SMS_TEST_TO_NUMBER")
    sms_mode = os.getenv("SMS_MODE", "mock")
    
    print(f"\nConfiguration:")
    print(f"  SMS_MODE: {sms_mode}")
    print(f"  TWILIO_ACCOUNT_SID: {'***' + account_sid[-4:] if account_sid else 'NOT SET'}")
    print(f"  TWILIO_AUTH_TOKEN: {'***' + auth_token[-4:] if auth_token else 'NOT SET'}")
    print(f"  TWILIO_FROM_NUMBER: {from_number or 'NOT SET'}")
    print(f"  SMS_TEST_TO_NUMBER: {to_number or 'NOT SET'}")
    
    # Validate configuration
    if not all([account_sid, auth_token, from_number, to_number]):
        print("\n❌ ERROR: Missing Twilio configuration!")
        print("Please set all required environment variables in .env:")
        print("  - TWILIO_ACCOUNT_SID")
        print("  - TWILIO_AUTH_TOKEN")
        print("  - TWILIO_FROM_NUMBER")
        print("  - SMS_TEST_TO_NUMBER")
        return False
    
    if sms_mode != "twilio":
        print(f"\n⚠️  WARNING: SMS_MODE is '{sms_mode}', not 'twilio'")
        print("   Change SMS_MODE=twilio in .env to send real SMS")
        
    print("\n" + "-" * 60)
    print("Attempting to send test SMS...")
    print("-" * 60)
    
    try:
        from twilio.rest import Client
        
        client = Client(account_sid, auth_token)
        
        message = client.messages.create(
            body="🏥 Lumea Health Test: Your Twilio SMS configuration is working correctly! This is a test message.",
            from_=from_number,
            to=to_number
        )
        
        print(f"\n✅ SUCCESS! SMS sent successfully!")
        print(f"   Message SID: {message.sid}")
        print(f"   Status: {message.status}")
        print(f"   From: {from_number}")
        print(f"   To: {to_number}")
        print(f"   Date Created: {message.date_created}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: Failed to send SMS")
        print(f"   Error Type: {type(e).__name__}")
        print(f"   Error Message: {str(e)}")
        
        # Common error explanations
        error_msg = str(e).lower()
        if "authenticate" in error_msg or "credentials" in error_msg:
            print("\n   💡 Tip: Check your TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN")
        elif "unverified" in error_msg:
            print("\n   💡 Tip: In trial mode, you can only send to verified numbers.")
            print("         Verify your phone number at: https://console.twilio.com/")
        elif "invalid" in error_msg and "number" in error_msg:
            print("\n   💡 Tip: Check phone number format. Should be E.164 format: +1234567890")
        
        return False


def test_api_endpoint():
    """Test the /api/sms/test endpoint."""
    print("\n" + "=" * 60)
    print("TESTING API ENDPOINT")
    print("=" * 60)
    
    print("\nTo test via API, make a POST request:")
    print('  curl -X POST http://localhost:8000/api/sms/test \\')
    print('       -H "Content-Type: application/json" \\')
    print('       -H "Authorization: Bearer <your_jwt_token>" \\')
    print('       -d \'{"message": "Test message from API"}\'')


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("LUMEA HEALTH - TWILIO SMS TEST SCRIPT")
    print("=" * 60)
    
    success = test_twilio_sms()
    test_api_endpoint()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ All tests passed! Twilio is configured correctly.")
    else:
        print("❌ Some tests failed. Please check the configuration above.")
    print("=" * 60 + "\n")
    
    sys.exit(0 if success else 1)
