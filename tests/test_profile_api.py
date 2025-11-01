"""
Simple test script to verify user profile endpoints.
Run this after starting the server to test the new endpoints.
"""
import requests
import os
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:8000/api"
# You'll need to replace this with a real token from Google auth
TEST_TOKEN = os.getenv("TEST_TOKEN", "")

def test_get_profile():
    """Test getting current user profile"""
    print("\n=== Testing GET /users/me ===")
    response = requests.get(
        f"{BASE_URL}/users/me",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"}
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.json() if response.status_code == 200 else None

def test_change_username(new_username):
    """Test changing username"""
    print(f"\n=== Testing PATCH /users/me/username (username: {new_username}) ===")
    response = requests.patch(
        f"{BASE_URL}/users/me/username",
        headers={
            "Authorization": f"Bearer {TEST_TOKEN}",
            "Content-Type": "application/json"
        },
        json={"username": new_username}
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 200

def test_upload_photo(image_path):
    """Test uploading profile photo"""
    print(f"\n=== Testing PATCH /users/me/photo ===")
    
    if not os.path.exists(image_path):
        print(f"Error: Image file not found at {image_path}")
        return False
    
    with open(image_path, "rb") as f:
        files = {"file": (os.path.basename(image_path), f, "image/jpeg")}
        response = requests.patch(
            f"{BASE_URL}/users/me/photo",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
            files=files
        )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 200

def test_delete_photo():
    """Test deleting profile photo"""
    print(f"\n=== Testing DELETE /users/me/photo ===")
    response = requests.delete(
        f"{BASE_URL}/users/me/photo",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"}
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 200

def test_invalid_username():
    """Test username validation"""
    print(f"\n=== Testing invalid username (should fail) ===")
    response = requests.patch(
        f"{BASE_URL}/users/me/username",
        headers={
            "Authorization": f"Bearer {TEST_TOKEN}",
            "Content-Type": "application/json"
        },
        json={"username": "invalid username!@#"}
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 400

if __name__ == "__main__":
    if not TEST_TOKEN:
        print("ERROR: Please set TEST_TOKEN environment variable with a valid JWT token")
        print("You can get a token by authenticating via /api/auth/google-mobile")
        exit(1)
    
    print("Starting User Profile API Tests")
    print("=" * 50)
    
    # Test 1: Get current profile
    profile = test_get_profile()
    
    if profile:
        # Test 2: Change username
        test_change_username("test_user_123")
        
        # Test 3: Invalid username
        test_invalid_username()
        
        # Test 4: Upload photo (you'll need a test image)
        test_image = "test_profile.jpg"
        if os.path.exists(test_image):
            test_upload_photo(test_image)
        else:
            print(f"\nSkipping photo upload test (no test image at {test_image})")
        
        # Test 5: Delete photo
        # test_delete_photo()  # Uncomment if you want to test deletion
        
        # Final: Get profile again to see changes
        test_get_profile()
    
    print("\n" + "=" * 50)
    print("Tests completed!")
