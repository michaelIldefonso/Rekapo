# Quick Reference: User Profile APIs

## Endpoints Overview

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/users/me` | Get current user profile | ✓ |
| PATCH | `/api/users/me/username` | Change username | ✓ |
| PATCH | `/api/users/me/photo` | Upload profile photo | ✓ |
| DELETE | `/api/users/me/photo` | Delete profile photo | ✓ |

## Quick Examples

### JavaScript/Fetch

```javascript
// Get profile
const profile = await fetch('/api/users/me', {
  headers: { 'Authorization': `Bearer ${token}` }
}).then(r => r.json());

// Change username
await fetch('/api/users/me/username', {
  method: 'PATCH',
  headers: { 
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ username: 'newusername' })
});

// Upload photo
const formData = new FormData();
formData.append('file', fileInput.files[0]);
await fetch('/api/users/me/photo', {
  method: 'PATCH',
  headers: { 'Authorization': `Bearer ${token}` },
  body: formData
});
```

### Python/Requests

```python
import requests

headers = {'Authorization': f'Bearer {token}'}

# Get profile
profile = requests.get('http://localhost:8000/api/users/me', headers=headers)

# Change username
requests.patch(
    'http://localhost:8000/api/users/me/username',
    headers={**headers, 'Content-Type': 'application/json'},
    json={'username': 'newusername'}
)

# Upload photo
with open('photo.jpg', 'rb') as f:
    files = {'file': f}
    requests.patch('http://localhost:8000/api/users/me/photo', 
                   headers=headers, files=files)
```

### cURL

```bash
# Get profile
curl http://localhost:8000/api/users/me \
  -H "Authorization: Bearer YOUR_TOKEN"

# Change username
curl -X PATCH http://localhost:8000/api/users/me/username \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"username": "newusername"}'

# Upload photo
curl -X PATCH http://localhost:8000/api/users/me/photo \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@photo.jpg"

# Delete photo
curl -X DELETE http://localhost:8000/api/users/me/photo \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Validation Rules

### Username
- ✓ 3-50 characters
- ✓ Letters, numbers, underscore (_), hyphen (-)
- ✓ Must be unique
- ✗ No spaces or special characters

### Profile Photo
- ✓ JPG, JPEG, PNG, GIF, WebP
- ✓ Max 5MB
- ✗ Other file types rejected

## Response Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad request (validation failed) |
| 401 | Unauthorized (invalid/expired token) |
| 403 | Forbidden (account disabled) |
| 404 | Not found |
| 409 | Conflict (username taken) |
| 500 | Server error |

## Error Response Format

```json
{
  "detail": "Error message here"
}
```

## Success Response Examples

### Username Change
```json
{
  "success": true,
  "message": "Username updated successfully",
  "username": "newusername"
}
```

### Photo Upload
```json
{
  "success": true,
  "message": "Profile photo updated successfully",
  "profile_picture_path": "uploads/profile_photos/user_1_abc123.jpg"
}
```

### Get Profile
```json
{
  "id": 1,
  "google_id": "...",
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
