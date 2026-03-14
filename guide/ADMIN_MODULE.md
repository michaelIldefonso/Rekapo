# Admin Module Documentation

## Overview

The Admin Module provides a comprehensive administrative interface for managing users, sessions, system logs, and analytics. It implements a secure Google OAuth2-based authentication system and offers powerful tools for system monitoring, user management, and data analysis.

## Architecture

The admin module is organized into the following components:

- **Authentication** (`admin_auth.py`) - Google OAuth2 login system
- **User Management** (`admin_users.py`) - User CRUD operations and analytics
- **Session Management** (`admin_sessions.py`) - Session monitoring and training data access
- **Logs Management** (`admin_logs.py`) - Application log viewing and analysis
- **Statistics** (`admin_statistics.py`) - System-wide metrics and analytics
- **User Analytics** (`admin_user_analytics.py`) - Comprehensive user activity analytics
- **Services** (`services.py`) - Business logic layer
- **Schemas** (`schemas.py`) - Pydantic models for requests/responses
- **Utils** (`utils.py`) - JWT token generation and validation

---

## Authentication System

### Overview
The admin authentication uses **Google OAuth2** with JWT tokens for secure admin access.

### Endpoints

#### 1. **POST** `/admin/auth/login`
Initiates Google OAuth2 login flow.

**Response:**
```json
{
  "authorization_url": "https://accounts.google.com/o/oauth2/auth?...",
  "state": "random_state_string"
}
```

#### 2. **GET** `/admin/auth/callback`
Handles OAuth2 callback from Google.

**Query Parameters:**
- `code` - Authorization code from Google
- `state` - State parameter for CSRF protection
- `error` - Error message (if authentication failed)

**Success:** Redirects to frontend with JWT token
```
{ADMIN_FRONTEND_URL}/auth/success?token=<JWT_TOKEN>
```

**Error Redirects:**
- `/login?error=unauthorized` - User is not an admin
- `/login?error=account_disabled` - Admin account is disabled
- `/login?error=auth_failed` - Authentication failed

#### 3. **POST** `/admin/auth/verify`
Verifies admin JWT token and returns user information.

**Headers:**
```
Authorization: Bearer <JWT_TOKEN>
```

**Response:**
```json
{
  "access_token": "new_jwt_token",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "admin@example.com",
    "name": "Admin User",
    "username": "admin",
    "is_admin": true,
    "is_disabled": false,
    "created_at": "2024-01-01T00:00:00"
  }
}
```

#### 4. **POST** `/admin/auth/logout`
Logs out admin user (client should discard token).

**Response:**
```json
{
  "message": "Logged out successfully"
}
```

---

## User Management

All user management endpoints require admin authentication via JWT token in the `Authorization` header.

### Endpoints

#### 1. **GET** `/admin/users`
Get paginated list of users with optional filters.

**Query Parameters:**
- `page` (int, default: 1) - Page number
- `page_size` (int, default: 20, max: 100) - Items per page
- `search` (string, optional) - Search by user ID (numeric), email, name, or username
- `is_admin` (boolean, optional) - Filter by admin status
- `is_disabled` (boolean, optional) - Filter by disabled status

**Response:**
```json
{
  "total": 150,
  "page": 1,
  "page_size": 20,
  "users": [
    {
      "id": 1,
      "google_id": "123456789",
      "email": "user@example.com",
      "name": "John Doe",
      "username": "johndoe",
      "profile_picture_path": "https://...",
      "is_admin": false,
      "is_disabled": false,
      "data_usage_consent": true,
      "created_at": "2024-01-01T00:00:00",
      "disabled_at": null,
      "disabled_by": null,
      "disabled_reason": null
    }
  ]
}
```

#### 2. **GET** `/admin/users/{user_id}`
Get detailed information about a specific user.

**Response:**
```json
{
  "id": 1,
  "email": "user@example.com",
  "name": "John Doe",
  "username": "johndoe",
  "is_admin": false,
  "is_disabled": false,
  "data_usage_consent": true,
  "created_at": "2024-01-01T00:00:00"
}
```

#### 3. **POST** `/admin/users/{user_id}/disable`
Disable a user account.

**Request Body:**
```json
{
  "reason": "Violation of terms of service"
}
```

**Response:** User object with updated disabled status

**Note:** Admins cannot disable themselves.

#### 4. **POST** `/admin/users/{user_id}/enable`
Enable a previously disabled user account.

**Response:** User object with updated enabled status

#### 5. **PATCH** `/admin/users/{user_id}/admin-status`
Update admin status of a user (promote/demote).

**Request Body:**
```json
{
  "is_admin": true
}
```

**Response:** User object with updated admin status

**Note:** Admins cannot demote themselves.

#### 6. **GET** `/admin/users/{user_id}/analytics`
Get comprehensive analytics for a specific user.

**Response:**
```json
{
  "user_id": 1,
  "email": "user@example.com",
  "name": "John Doe",
  "username": "johndoe",
  "is_admin": false,
  "is_disabled": false,
  "created_at": "2024-01-01T00:00:00",
  "total_sessions": 50,
  "completed_sessions": 45,
  "failed_sessions": 3,
  "deleted_sessions": 2,
  "active_sessions": 0,
  "average_session_duration": 15.5,
  "total_recording_time": 697.5,
  "longest_session_duration": 45.2,
  "total_recording_segments": 250,
  "total_transcribed_words": 12500,
  "last_session_date": "2024-02-10T10:30:00",
  "days_since_last_session": 2,
  "account_age_days": 42
}
```

#### 7. **DELETE** `/admin/users/{user_id}`
Permanently delete a user account and all associated data.

**Response:**
```json
{
  "message": "User deleted successfully",
  "user_id": 1
}
```

**Note:** Admins cannot delete themselves. This operation is irreversible.

---

## Session Management

### Endpoints

#### 1. **GET** `/admin/sessions`
Get paginated list of sessions with optional filters.

**Query Parameters:**
- `page` (int, default: 1) - Page number
- `page_size` (int, default: 20, max: 100) - Items per page
- `user_id` (int, optional) - Filter by user ID
- `status` (string, optional) - Filter by status: "recording", "completed", "failed"
- `is_deleted` (boolean, optional) - Filter by deleted status
- `session_title` (string, optional) - Search by session title
- `training_consent` (boolean, optional) - Filter by user's training consent
- `require_consent` (boolean, default: false) - If true, ONLY return sessions with training consent

**Response:**
```json
{
  "total": 500,
  "page": 1,
  "page_size": 20,
  "sessions": [
    {
      "id": 1,
      "user_id": 5,
      "session_title": "Meeting Notes",
      "start_time": "2024-02-10T10:00:00",
      "end_time": "2024-02-10T10:30:00",
      "is_deleted": false,
      "deleted_at": null,
      "deleted_by": null,
      "status": "completed",
      "created_at": "2024-02-10T10:00:00",
      "user": {
        "user_id": 5,
        "email": "user@example.com",
        "name": "John Doe",
        "username": "johndoe",
        "data_usage_consent": true
      }
    }
  ]
}
```

#### 2. **GET** `/admin/sessions/{session_id}/detailed`
Get comprehensive session details including all recording segments and transcriptions.

**Query Parameters:**
- `require_consent` (boolean, default: false) - If true, return 403 if user hasn't consented

**Response:**
```json
{
  "id": 1,
  "user_id": 5,
  "session_title": "Meeting Notes",
  "start_time": "2024-02-10T10:00:00",
  "end_time": "2024-02-10T10:30:00",
  "is_deleted": false,
  "deleted_at": null,
  "deleted_by": null,
  "status": "completed",
  "created_at": "2024-02-10T10:00:00",
  "user": {
    "user_id": 5,
    "email": "user@example.com",
    "name": "John Doe",
    "username": "johndoe",
    "data_usage_consent": true
  },
  "recording_segments": [
    {
      "id": 1,
      "session_id": 1,
      "segment_number": 1,
      "audio_path": "/audio/session_1/segment_1.wav",
      "transcript_text": "This is the transcribed text...",
      "english_translation": "This is the English translation...",
      "rating": 5,
      "created_at": "2024-02-10T10:05:00"
    }
  ],
  "summaries": [
    {
      "id": 1,
      "session_id": 1,
      "chunk_range_start": 1,
      "chunk_range_end": 5,
      "summary_text": "Summary of the session...",
      "is_final_summary": false,
      "generated_at": "2024-02-10T10:30:00"
    }
  ],
  "total_segments": 10,
  "total_summaries": 2,
  "session_duration_minutes": 30.0
}
```

#### 3. **GET** `/admin/training-data/sessions/{session_id}`
Get complete session data for AI training purposes.

**Security:** This endpoint ALWAYS enforces training consent check and cannot be bypassed. Returns 403 if:
- User has not consented to training data usage
- Session is marked as deleted

**Response:** Same as detailed session endpoint

#### 4. **DELETE** `/admin/sessions/{session_id}`
Soft delete a session (marks as deleted, doesn't remove from database).

**Response:**
```json
{
  "message": "Session deleted successfully",
  "session_id": 1
}
```

---

## Logs Management

### Endpoints

#### 1. **GET** `/admin/logs/summary`
Get summary of logs grouped by date.

**Query Parameters:**
- `date` (string, optional) - Filter by date (YYYY-MM-DD)

**Response:**
```json
{
  "summary": [
    {
      "date": "2024-02-10",
      "total": 1500,
      "errors": 25,
      "warnings": 150,
      "info": 1325
    }
  ],
  "count": 1
}
```

#### 2. **GET** `/admin/logs/recent`
Get recent logs from database.

**Query Parameters:**
- `limit` (int, default: 100, max: 1000) - Number of logs to retrieve
- `level` (string, optional) - Filter by log level: "error", "warn", "info"

**Response:**
```json
{
  "logs": [
    {
      "id": 1,
      "user_id": 5,
      "user_email": "user@example.com",
      "level": "error",
      "message": "Error message...",
      "timestamp": "2024-02-10T10:30:00",
      "app_version": "1.0.0",
      "platform": "iOS"
    }
  ],
  "count": 100
}
```

#### 3. **GET** `/admin/logs/errors/recent`
Get all errors from last N hours.

**Query Parameters:**
- `hours` (int, default: 24, max: 168) - Hours to look back

**Response:**
```json
{
  "errors": [
    {
      "user_id": 5,
      "user_email": "user@example.com",
      "timestamp": "2024-02-10T10:30:00",
      "message": "Error message...",
      "app_version": "1.0.0",
      "platform": "iOS"
    }
  ],
  "count": 25,
  "hours": 24,
  "cutoff_time": "2024-02-09T10:30:00"
}
```

#### 4. **GET** `/admin/logs/stats`
Get log statistics for dashboard widgets.

**Query Parameters:**
- `hours` (int, default: 24, max: 168) - Hours to look back

**Response:**
```json
{
  "period_hours": 24,
  "total_logs": 1500,
  "errors": 25,
  "warnings": 150,
  "info": 1325,
  "top_errors": [
    {
      "message": "Database connection failed...",
      "count": 10
    }
  ],
  "top_error_users": [
    {
      "email": "user@example.com",
      "count": 5
    }
  ]
}
```

#### 5. **GET** `/admin/logs/user/{user_id}`
Get all logs for a specific user.

**Query Parameters:**
- `hours` (int, default: 24, max: 168) - Hours to look back
- `level` (string, optional) - Filter by log level

**Response:**
```json
{
  "user_id": 5,
  "logs": [...],
  "count": 50,
  "hours": 24
}
```

#### 6. **GET** `/admin/logs/user/email/{email}`
Search logs by user email.

**Query Parameters:**
- `hours` (int, default: 24, max: 168) - Hours to look back
- `level` (string, optional) - Filter by log level

**Response:**
```json
{
  "email": "user@example.com",
  "logs": [...],
  "count": 50,
  "hours": 24
}
```

#### 7. **DELETE** `/admin/logs/cleanup`
Delete logs older than specified days.

**Query Parameters:**
- `days` (int, default: 30, max: 365) - Delete logs older than N days

**Response:**
```json
{
  "deleted": 1500,
  "days": 30,
  "cutoff_date": "2024-01-10T00:00:00"
}
```

---

## System Statistics

### Endpoints

#### 1. **GET** `/admin/statistics`
Get paginated list of system statistics.

**Query Parameters:**
- `page` (int, default: 1) - Page number
- `page_size` (int, default: 20, max: 100) - Items per page
- `start_date` (date, optional) - Filter by start date
- `end_date` (date, optional) - Filter by end date

**Response:**
```json
{
  "total": 30,
  "page": 1,
  "page_size": 20,
  "statistics": [
    {
      "id": 1,
      "stat_date": "2024-02-10",
      "total_users": 150,
      "active_users": 45,
      "total_sessions": 500,
      "average_session_duration": 15.5,
      "calculated_at": "2024-02-10T23:59:00"
    }
  ]
}
```

#### 2. **GET** `/admin/statistics/{stat_id}`
Get system statistics by ID.

#### 3. **GET** `/admin/statistics/date/{stat_date}`
Get system statistics for a specific date.

#### 4. **POST** `/admin/statistics`
Create new system statistics entry.

**Request Body:**
```json
{
  "stat_date": "2024-02-10",
  "total_users": 150,
  "active_users": 45,
  "total_sessions": 500,
  "average_session_duration": 15.5
}
```

#### 5. **PUT** `/admin/statistics/{stat_id}`
Update existing system statistics entry.

**Request Body:**
```json
{
  "total_users": 150,
  "active_users": 45,
  "total_sessions": 500,
  "average_session_duration": 15.5
}
```

#### 6. **DELETE** `/admin/statistics/{stat_id}`
Delete system statistics entry.

#### 7. **POST** `/admin/statistics/calculate/{stat_date}`
Calculate and store system statistics for a specific date based on actual data.

**Response:** System statistics object with calculated values

---

## User Analytics

### Endpoints

#### 1. **GET** `/admin/analytics/users`
Get comprehensive analytics for all users.

**Query Parameters:**
- `page` (int, default: 1) - Page number
- `page_size` (int, default: 20, max: 100) - Items per page
- `time_period` (string, default: "all") - Time period: "24h", "7d", "30d", "90d", "all"
- `search` (string, optional) - Search by user ID, email, name, or username

**Response:**
```json
{
  "total": 150,
  "page": 1,
  "page_size": 20,
  "time_period": "30d",
  "analytics": [
    {
      "user_id": 1,
      "email": "user@example.com",
      "name": "John Doe",
      "username": "johndoe",
      "is_admin": false,
      "is_disabled": false,
      "created_at": "2024-01-01T00:00:00",
      "total_sessions": 50,
      "completed_sessions": 45,
      "failed_sessions": 3,
      "deleted_sessions": 2,
      "active_sessions": 0,
      "average_session_duration": 15.5,
      "total_recording_time": 697.5,
      "longest_session_duration": 45.2,
      "total_recording_segments": 250,
      "total_transcribed_words": 12500,
      "last_session_date": "2024-02-10T10:30:00",
      "days_since_last_session": 2,
      "account_age_days": 42
    }
  ]
}
```

---

## Security Features

### JWT Token Authentication
- All admin endpoints require a valid JWT token in the `Authorization` header
- Token format: `Bearer <JWT_TOKEN>`
- Tokens are generated after successful Google OAuth2 authentication
- Tokens contain user ID and admin status

### Safety Checks
1. **Self-Operation Prevention:**
   - Admins cannot disable themselves
   - Admins cannot demote themselves
   - Admins cannot delete themselves

2. **Training Data Access Control:**
   - Training data endpoints enforce user consent checks
   - Cannot be bypassed with query parameters
   - Deleted sessions cannot be used for training
   - Returns 403 Forbidden if consent is not given

3. **Admin-Only Access:**
   - All endpoints require `is_admin=True` in user account
   - Non-admin users attempting to access admin routes receive 403 Forbidden
   - Disabled admin accounts cannot access admin routes

### Logging
- All admin actions are logged with admin ID and details
- User information is masked in logs (email masking)
- Comprehensive audit trail for compliance

---

## Data Models

### User
- `id` - User ID
- `google_id` - Google OAuth ID
- `email` - User email
- `name` - User's full name
- `username` - Username
- `profile_picture_path` - Profile picture URL
- `is_admin` - Admin status
- `is_disabled` - Account disabled status
- `data_usage_consent` - Training data consent
- `created_at` - Account creation timestamp
- `disabled_at` - Account disable timestamp
- `disabled_by` - Admin ID who disabled account
- `disabled_reason` - Reason for disabling

### Session
- `id` - Session ID
- `user_id` - User ID
- `session_title` - Session title
- `start_time` - Session start timestamp
- `end_time` - Session end timestamp
- `status` - Session status: "recording", "completed", "failed"
- `is_deleted` - Soft delete status
- `deleted_at` - Deletion timestamp
- `deleted_by` - Admin ID who deleted session
- `created_at` - Session creation timestamp

### RecordingSegment
- `id` - Segment ID
- `session_id` - Session ID
- `segment_number` - Segment order number
- `audio_path` - Path to audio file
- `transcript_text` - Transcribed text
- `english_translation` - English translation
- `rating` - User rating
- `created_at` - Segment creation timestamp

### Summary
- `id` - Summary ID
- `session_id` - Session ID
- `chunk_range_start` - Start segment number
- `chunk_range_end` - End segment number
- `summary_text` - Summary content
- `is_final_summary` - Final summary flag
- `generated_at` - Summary generation timestamp

### SystemStatistics
- `id` - Statistics ID
- `stat_date` - Date of statistics
- `total_users` - Total registered users
- `active_users` - Active users on date
- `total_sessions` - Total sessions created
- `average_session_duration` - Average session duration (minutes)
- `calculated_at` - Calculation timestamp

---

## Environment Variables

Required environment variables for admin module:

```env
# Google OAuth2 Configuration
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
ADMIN_REDIRECT_URI=http://localhost:8000/admin/auth/callback
ADMIN_FRONTEND_URL=http://localhost:3000

# JWT Configuration
ADMIN_JWT_SECRET=your_secret_key
ADMIN_JWT_ALGORITHM=HS256
ADMIN_JWT_EXPIRATION_DAYS=7
```

---

## Usage Examples

### Authentication Flow

1. **Frontend initiates login:**
```javascript
// Call login endpoint
const response = await fetch('/admin/auth/login');
const { authorization_url } = await response.json();

// Redirect user to Google
window.location.href = authorization_url;
```

2. **Google redirects to callback:**
```
GET /admin/auth/callback?code=<auth_code>&state=<state>
```

3. **Backend redirects to frontend with token:**
```
Redirect to: http://localhost:3000/auth/success?token=<JWT_TOKEN>
```

4. **Frontend stores token and makes authenticated requests:**
```javascript
const response = await fetch('/admin/users', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
```

### Search Users
```javascript
// Search by email
const response = await fetch('/admin/users?search=john@example.com', {
  headers: { 'Authorization': `Bearer ${token}` }
});

// Search by user ID
const response = await fetch('/admin/users?search=123', {
  headers: { 'Authorization': `Bearer ${token}` }
});
```

### Get User Analytics
```javascript
// Get analytics for last 30 days
const response = await fetch('/admin/analytics/users?time_period=30d&page=1&page_size=50', {
  headers: { 'Authorization': `Bearer ${token}` }
});
```

### Access Training Data
```javascript
// This will return error if user hasn't consented
const response = await fetch('/admin/training-data/sessions/123', {
  headers: { 'Authorization': `Bearer ${token}` }
});
```

---

## Rate Limiting & Best Practices

1. **Pagination:** Always use pagination for list endpoints to avoid large responses
2. **Filtering:** Use filters to narrow down results before pagination
3. **Time Periods:** Use time period filters for analytics to improve query performance
4. **Batch Operations:** Plan bulk operations during off-peak hours
5. **Log Cleanup:** Schedule regular log cleanup to maintain database performance

---

## Error Responses

All endpoints return standard error responses:

```json
{
  "detail": "Error message description"
}
```

Common HTTP status codes:
- `400` - Bad Request (invalid parameters)
- `401` - Unauthorized (missing or invalid token)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found (resource doesn't exist)
- `500` - Internal Server Error (server-side error)

---

## Future Enhancements

Potential improvements for the admin module:
- Real-time dashboard with WebSocket updates
- Advanced filtering and sorting options
- Bulk user operations (bulk disable, bulk delete)
- Export functionality (CSV, Excel) for analytics
- Role-based access control (multiple admin levels)
- Admin activity audit log
- Scheduled reports via email
- Advanced search with Elasticsearch
- API rate limiting and throttling
- Two-factor authentication for admins
