# User Profile API Documentation

This document describes the API endpoints for managing user profiles, including username changes and profile photo uploads.

## Authentication

All user profile endpoints require authentication using a Bearer token obtained from the `/api/auth/google-mobile` endpoint.

Include the token in the `Authorization` header:
```
Authorization: Bearer <your_access_token>
```

## Endpoints

### 1. Get Current User Profile

**Endpoint:** `GET /api/users/me`

**Description:** Retrieve the current authenticated user's profile information.

**Response:**
```json
{
  "id": 1,
  "google_id": "1234567890",
  "email": "user@example.com",
  "name": "John Doe",
  "username": "johndoe",
  "profile_picture_path": "uploads/profile_photos/user_1_abc123.jpg",
  "data_usage_consent": true,
  "is_admin": false,
  "is_disabled": false,
  "created_at": "2025-11-01T10:30:00"
}
```

---

### 2. Change Username

**Endpoint:** `PATCH /api/users/me/username`

**Description:** Update the current user's username.

**Request Body:**
```json
{
  "username": "new_username"
}
```

**Validation Rules:**
- Username must be 3-50 characters long
- Can only contain letters, numbers, underscores (_), and hyphens (-)
- Must be unique across all users

**Success Response (200):**
```json
{
  "success": true,
  "message": "Username updated successfully",
  "username": "new_username"
}
```

**Error Responses:**

- **400 Bad Request** - Invalid username format
```json
{
  "detail": "Username can only contain letters, numbers, underscores, and hyphens"
}
```

- **409 Conflict** - Username already taken
```json
{
  "detail": "Username already taken"
}
```

**cURL Example:**
```bash
curl -X PATCH "http://localhost:8000/api/users/me/username" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"username": "new_username"}'
```

---

### 3. Upload Profile Photo

**Endpoint:** `PATCH /api/users/me/photo`

**Description:** Upload a new profile photo for the current user.

**Request:** Multipart form data with file upload

**Supported Formats:** JPG, JPEG, PNG, GIF, WebP

**Maximum File Size:** 5 MB

**Success Response (200):**
```json
{
  "success": true,
  "message": "Profile photo updated successfully",
  "profile_picture_path": "uploads/profile_photos/user_1_abc12345.jpg"
}
```

**Error Responses:**

- **400 Bad Request** - Invalid file type
```json
{
  "detail": "Invalid file type. Allowed types: .jpg, .jpeg, .png, .gif, .webp"
}
```

- **400 Bad Request** - File too large
```json
{
  "detail": "File too large. Maximum size: 5.0MB"
}
```

**cURL Example:**
```bash
curl -X PATCH "http://localhost:8000/api/users/me/photo" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@profile.jpg"
```

**JavaScript/Fetch Example:**
```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);

const response = await fetch('http://localhost:8000/api/users/me/photo', {
  method: 'PATCH',
  headers: {
    'Authorization': `Bearer ${accessToken}`
  },
  body: formData
});

const result = await response.json();
console.log(result);
```

---

### 4. Delete Profile Photo

**Endpoint:** `DELETE /api/users/me/photo`

**Description:** Delete the current user's profile photo.

**Notes:**
- Google profile photos (URLs starting with http) will only have their reference removed
- Local uploaded photos will be deleted from the server

**Success Response (200):**
```json
{
  "success": true,
  "message": "Profile photo deleted successfully"
}
```

**Error Responses:**

- **404 Not Found** - No profile photo to delete
```json
{
  "detail": "No profile photo to delete"
}
```

**cURL Example:**
```bash
curl -X DELETE "http://localhost:8000/api/users/me/photo" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Error Handling

All endpoints may return the following authentication errors:

- **401 Unauthorized** - Invalid or expired token
```json
{
  "detail": "Invalid authentication credentials"
}
```

- **403 Forbidden** - User account is disabled
```json
{
  "detail": "User account is disabled"
}
```

## File Storage

Profile photos are stored in the `uploads/profile_photos/` directory with the naming convention:
```
user_{user_id}_{random_hash}{file_extension}
```

Example: `user_123_abc12345.jpg`

When a user uploads a new profile photo, the previous local photo (if any) is automatically deleted to save storage space.

## Mobile Integration

For mobile apps using React Native or similar frameworks:

1. **Get User Profile:**
```javascript
const getUserProfile = async (token) => {
  const response = await fetch('http://your-api/api/users/me', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  return await response.json();
};
```

2. **Update Username:**
```javascript
const updateUsername = async (token, newUsername) => {
  const response = await fetch('http://your-api/api/users/me/username', {
    method: 'PATCH',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ username: newUsername })
  });
  return await response.json();
};
```

3. **Upload Profile Photo (React Native):**
```javascript
import * as ImagePicker from 'expo-image-picker';

const uploadProfilePhoto = async (token) => {
  // Pick image
  const result = await ImagePicker.launchImageLibraryAsync({
    mediaTypes: ImagePicker.MediaTypeOptions.Images,
    allowsEditing: true,
    aspect: [1, 1],
    quality: 0.8,
  });

  if (!result.canceled) {
    const formData = new FormData();
    formData.append('file', {
      uri: result.assets[0].uri,
      type: 'image/jpeg',
      name: 'profile.jpg',
    });

    const response = await fetch('http://your-api/api/users/me/photo', {
      method: 'PATCH',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
      body: formData,
    });

    return await response.json();
  }
};
```

## Security Considerations

1. **File Validation:** Only allowed image formats are accepted
2. **Size Limits:** Files are limited to 5MB to prevent abuse
3. **Authentication:** All endpoints require valid JWT tokens
4. **Username Uniqueness:** Usernames are validated for uniqueness at the database level
5. **File Naming:** Random hashes prevent filename conflicts and guessing
6. **Old File Cleanup:** Previous profile photos are automatically deleted
