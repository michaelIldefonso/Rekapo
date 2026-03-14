# System Statistics API Documentation

## Overview
The System Statistics API provides endpoints for managing and viewing aggregated system metrics. These statistics are calculated daily and include user activity, session counts, and performance metrics.

**Base URL**: `/admin/statistics`

**Authentication**: All endpoints require admin authentication via Bearer token.

---

## Endpoints

### 1. List System Statistics (Paginated)

Get a paginated list of system statistics with optional date filters.

**Endpoint**: `GET /admin/statistics`

**Query Parameters**:
- `page` (integer, optional): Page number (default: 1, minimum: 1)
- `page_size` (integer, optional): Items per page (default: 20, minimum: 1, maximum: 100)
- `start_date` (date, optional): Filter statistics from this date onwards (format: YYYY-MM-DD)
- `end_date` (date, optional): Filter statistics up to this date (format: YYYY-MM-DD)

**Response**: `SystemStatisticsListResponse`
```json
{
  "total": 100,
  "page": 1,
  "page_size": 20,
  "statistics": [
    {
      "id": 1,
      "stat_date": "2026-01-10",
      "total_users": 150,
      "active_users": 45,
      "total_sessions": 78,
      "average_session_duration": 23.5,
      "calculated_at": "2026-01-11T00:05:00"
    }
  ]
}
```

**Example Request**:
```bash
curl -X GET "http://localhost:8000/admin/statistics?page=1&page_size=20&start_date=2026-01-01&end_date=2026-01-31" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

---

### 2. Get Statistics by ID

Get detailed system statistics for a specific ID.

**Endpoint**: `GET /admin/statistics/{stat_id}`

**Path Parameters**:
- `stat_id` (integer, required): The ID of the statistics record

**Response**: `SystemStatisticsResponse`
```json
{
  "id": 1,
  "stat_date": "2026-01-10",
  "total_users": 150,
  "active_users": 45,
  "total_sessions": 78,
  "average_session_duration": 23.5,
  "calculated_at": "2026-01-11T00:05:00"
}
```

**Example Request**:
```bash
curl -X GET "http://localhost:8000/admin/statistics/1" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

---

### 3. Get Statistics by Date

Get system statistics for a specific date.

**Endpoint**: `GET /admin/statistics/date/{stat_date}`

**Path Parameters**:
- `stat_date` (date, required): The date to retrieve statistics for (format: YYYY-MM-DD)

**Response**: `SystemStatisticsResponse`
```json
{
  "id": 1,
  "stat_date": "2026-01-10",
  "total_users": 150,
  "active_users": 45,
  "total_sessions": 78,
  "average_session_duration": 23.5,
  "calculated_at": "2026-01-11T00:05:00"
}
```

**Example Request**:
```bash
curl -X GET "http://localhost:8000/admin/statistics/date/2026-01-10" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

---

### 4. Create Statistics

Manually create a new system statistics entry.

**Endpoint**: `POST /admin/statistics`

**Request Body**: `CreateSystemStatisticsRequest`
```json
{
  "stat_date": "2026-01-10",
  "total_users": 150,
  "active_users": 45,
  "total_sessions": 78,
  "average_session_duration": 23.5
}
```

**Response**: `SystemStatisticsResponse` (Status: 201 Created)

**Example Request**:
```bash
curl -X POST "http://localhost:8000/admin/statistics" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "stat_date": "2026-01-10",
    "total_users": 150,
    "active_users": 45,
    "total_sessions": 78,
    "average_session_duration": 23.5
  }'
```

---

### 5. Update Statistics

Update an existing system statistics entry.

**Endpoint**: `PUT /admin/statistics/{stat_id}`

**Path Parameters**:
- `stat_id` (integer, required): The ID of the statistics record to update

**Request Body**: `UpdateSystemStatisticsRequest`
```json
{
  "total_users": 155,
  "active_users": 48,
  "total_sessions": 82,
  "average_session_duration": 24.2
}
```

**Note**: All fields are optional. Only provided fields will be updated.

**Response**: `SystemStatisticsResponse`

**Example Request**:
```bash
curl -X PUT "http://localhost:8000/admin/statistics/1" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "total_users": 155,
    "active_users": 48
  }'
```

---

### 6. Delete Statistics

Delete a system statistics entry.

**Endpoint**: `DELETE /admin/statistics/{stat_id}`

**Path Parameters**:
- `stat_id` (integer, required): The ID of the statistics record to delete

**Response**:
```json
{
  "message": "Statistics deleted successfully",
  "stat_id": 1,
  "stat_date": "2026-01-10"
}
```

**Example Request**:
```bash
curl -X DELETE "http://localhost:8000/admin/statistics/1" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

---

### 7. Calculate Statistics (Auto-compute)

Calculate and store system statistics for a specific date based on actual database data.
This endpoint automatically computes metrics from the database:
- **Total Users**: Count of all users created up to that date
- **Active Users**: Users who created at least one session on that date
- **Total Sessions**: Number of sessions started on that date
- **Average Session Duration**: Average duration (in minutes) of completed sessions on that date

If statistics already exist for the date, they will be updated with new calculations.

**Endpoint**: `POST /admin/statistics/calculate/{stat_date}`

**Path Parameters**:
- `stat_date` (date, required): The date to calculate statistics for (format: YYYY-MM-DD)

**Response**: `SystemStatisticsResponse`
```json
{
  "id": 1,
  "stat_date": "2026-01-10",
  "total_users": 150,
  "active_users": 45,
  "total_sessions": 78,
  "average_session_duration": 23.5,
  "calculated_at": "2026-01-11T10:30:00"
}
```

**Example Request**:
```bash
curl -X POST "http://localhost:8000/admin/statistics/calculate/2026-01-10" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

---

## Data Models

### SystemStatisticsResponse
```json
{
  "id": 1,
  "stat_date": "2026-01-10",
  "total_users": 150,
  "active_users": 45,
  "total_sessions": 78,
  "average_session_duration": 23.5,
  "calculated_at": "2026-01-11T00:05:00"
}
```

**Fields**:
- `id` (integer): Unique identifier for the statistics record
- `stat_date` (date): The date these statistics represent
- `total_users` (integer, nullable): Total number of registered users (cumulative up to this date)
- `active_users` (integer, nullable): Number of users who had at least one session on this date
- `total_sessions` (integer, nullable): Total number of sessions started on this date
- `average_session_duration` (float, nullable): Average duration of completed sessions in minutes
- `calculated_at` (datetime): Timestamp when these statistics were calculated

---

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Statistics already exist for date: 2026-01-10"
}
```

### 401 Unauthorized
```json
{
  "detail": "Not authenticated"
}
```

### 403 Forbidden
```json
{
  "detail": "Admin access required"
}
```

### 404 Not Found
```json
{
  "detail": "Statistics not found"
}
```

---

## Use Cases

### 1. Daily Automated Calculation
Set up a scheduled task (cron job) to calculate statistics daily:
```bash
# Run daily at 00:05 AM
curl -X POST "http://localhost:8000/admin/statistics/calculate/$(date -d 'yesterday' +%Y-%m-%d)" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

### 2. View Monthly Trends
```bash
# Get all statistics for January 2026
curl -X GET "http://localhost:8000/admin/statistics?start_date=2026-01-01&end_date=2026-01-31&page_size=31" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

### 3. Recalculate Past Statistics
```bash
# Recalculate statistics for a specific date
curl -X POST "http://localhost:8000/admin/statistics/calculate/2026-01-05" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

---

## Notes

1. **Admin Access Required**: All endpoints require an authenticated admin user.
2. **Unique Date Constraint**: Only one statistics record can exist per date.
3. **Automatic Calculation**: Use the `/calculate/{stat_date}` endpoint for accurate, database-driven statistics.
4. **Manual Entry**: Use POST/PUT endpoints for manual adjustments or external data imports.
5. **Average Duration**: Calculated only for completed sessions with both start and end times.
6. **Pagination**: Default page size is 20, maximum is 100 items per page.
7. **Date Format**: All dates use ISO 8601 format (YYYY-MM-DD).

---

## Testing with Swagger UI

Visit `http://localhost:8000/docs` to access the interactive API documentation and test all endpoints directly in your browser.
