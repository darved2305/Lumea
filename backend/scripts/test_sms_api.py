"""
Test SMS API Endpoint in Docker

Tests the /api/sms/test endpoint by logging in and sending a test SMS.
"""
import httpx
import asyncio

BASE_URL = "http://localhost:8000"


async def test_sms_via_api():
    """Test SMS sending via API endpoint."""
    
    print("=" * 60)
    print("TESTING SMS VIA API ENDPOINT")
    print("=" * 60)
    
    async with httpx.AsyncClient() as client:
        # Step 1: Login to get JWT token
        print("\n1. Logging in to get JWT token...")
        
        # Try with a test user - you may need to create one first
        login_data = {
            "username": "test@example.com",  # Update with your test user
            "password": "testpassword"       # Update with your test password
        }
        
        try:
            response = await client.post(
                f"{BASE_URL}/api/auth/token",
                data=login_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code != 200:
                print(f"   ❌ Login failed: {response.status_code}")
                print(f"   Response: {response.text}")
                print("\n   💡 Tip: You may need to register a user first or use existing credentials")
                return False
            
            token_data = response.json()
            token = token_data.get("access_token")
            print(f"   ✅ Got JWT token: {token[:20]}...")
            
        except Exception as e:
            print(f"   ❌ Login error: {e}")
            return False
        
        # Step 2: Call the SMS test endpoint
        print("\n2. Calling /api/sms/test endpoint...")
        
        try:
            response = await client.post(
                f"{BASE_URL}/api/sms/test",
                json={"message": "🏥 Hello from API test! Lumea Health SMS is working."},
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }
            )
            
            print(f"   Status Code: {response.status_code}")
            result = response.json()
            print(f"   Response: {result}")
            
            if response.status_code == 200 and result.get("success"):
                print("\n✅ SMS test successful!")
                return True
            else:
                print(f"\n❌ SMS test failed: {result.get('message', 'Unknown error')}")
                return False
                
        except Exception as e:
            print(f"   ❌ API call error: {e}")
            return False


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("LUMEA HEALTH - API SMS TEST")
    print("=" * 60)
    
    success = asyncio.run(test_sms_via_api())
    
    print("\n" + "=" * 60)
    if success:
        print("✅ API SMS test completed successfully!")
    else:
        print("❌ API SMS test failed. Check configuration.")
    print("=" * 60 + "\n")
