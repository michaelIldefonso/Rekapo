# Rekapo Backend - Logging & Cron Jobs Setup Guide

## ✅ Implementation Complete

This guide covers the newly implemented logging system and automated cron jobs.

---

## 🎯 Features Implemented

### 1. **Mobile App Logging System (Cloudflare R2)**
- Logs from React Native app are sent to backend
- Stored in Cloudflare R2 (S3-compatible object storage)
- Organized by date: `logs/2026/02/09/user_123_14-30-00.json`
- Admin endpoints to view, search, and filter logs

### 2. **Automated Cron Jobs**
- **Daily Statistics Calculation** - Runs at 2:00 AM
  - Calculates system statistics for the previous day
  - Includes: total users, active users, sessions, avg duration
- **Log Cleanup** - Runs at 3:00 AM
  - Deletes logs older than 7 days automatically
  - Keeps R2 storage usage minimal

---

## 📋 Required Environment Variables

Add these to your `.env` file:

```env
# Cloudflare R2 Configuration
R2_ENDPOINT_URL=https://xxxxx.r2.cloudflarestorage.com
R2_ACCESS_KEY_ID=your_access_key_here
R2_SECRET_ACCESS_KEY=your_secret_here
R2_REGION=auto
R2_BUCKET_NAME=rekapo
R2_ENABLED=true
```

---

## 🚀 Setup Instructions

### Step 1: Setup R2 Bucket (Already Done)

Your existing `rekapo` bucket will be used. Logs will be stored in a `logs/` folder within the bucket for organization.

### Step 2: Verify R2 Credentials (Already Done)

Your existing R2 credentials in `.env` will be used. No additional setup needed.

### Step 3: Install Dependencies

```bash
pip install boto3 apscheduler
# Or install all requirements
pip install -r requirements.txt
```

### Step 4: Restart Backend

```bash
# Development
uvicorn main:app --reload

# Production
uvicorn main:app --host 0.0.0.0 --port 8000
```

You should see in the startup logs:
```
✓ R2 client initialized successfully
⏰ Initializing Background Scheduler
✓ Scheduled: Daily Statistics Calculation at 2:00 AM
✓ Scheduled: Log Cleanup at 3:00 AM (deletes logs >7 days old)
✓ Background Scheduler Started Successfully
```

---

## 📡 API Endpoints

### User Endpoints

#### `POST /api/logs/write`
Write logs from mobile app to R2.

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "logs": [
    {
      "level": "info",
      "message": "User viewed profile",
      "timestamp": "2026-02-09T14:30:00.000Z"
    },
    {
      "level": "error",
      "message": "Failed to upload photo: Network timeout",
      "timestamp": "2026-02-09T14:30:05.000Z"
    }
  ],
  "batch_timestamp": "2026-02-09T14:30:10.000Z"
}
```

**Response:**
```json
{
  "status": "success",
  "logs_written": 2,
  "file": "logs/2026/02/09/user_123_14-30-00.json"
}
```

---

### Admin Endpoints (Admin Only)

#### `GET /api/logs/files?date=2026-02-09`
List all log files, optionally filtered by date.

**Response:**
```json
{
  "files": [
    {
      "key": "logs/2026/02/09/user_123_14-30-00.json",
      "size": 1024,
      "last_modified": "2026-02-09T14:30:10.000Z"
    }
  ],
  "count": 1
}
```

#### `GET /api/logs/view/{file_path}?level=error`
View contents of a specific log file, optionally filter by level.

**Response:**
```json
{
  "file": "logs/2026/02/09/user_123_14-30-00.json",
  "user_id": 123,
  "user_email": "user@example.com",
  "batch_timestamp": "2026-02-09T14:30:10.000Z",
  "logs": [
    {
      "level": "error",
      "message": "Failed to upload photo: Network timeout",
      "timestamp": "2026-02-09T14:30:05.000Z"
    }
  ],
  "count": 1
}
```

#### `GET /api/logs/errors/recent?hours=24`
Get all errors from the last N hours (default: 24, max: 168).

**Response:**
```json
{
  "errors": [
    {
      "user_id": 123,
      "user_email": "user@example.com",
      "timestamp": "2026-02-09T14:30:05.000Z",
      "message": "Failed to upload photo: Network timeout",
      "file": "logs/2026/02/09/user_123_14-30-00.json"
    }
  ],
  "count": 1,
  "hours": 24,
  "cutoff_time": "2026-02-08T14:30:00.000Z"
}
```

#### `DELETE /api/logs/cleanup?days=7`
Manually trigger log cleanup (delete logs older than N days).

**Response:**
```json
{
  "deleted": 45,
  "days": 7,
  "cutoff_date": "2026-02-02T14:30:00.000Z"
}
```

---

## 🤖 Automated Cron Jobs

### Job 1: Daily Statistics Calculation
- **Schedule:** Every day at 2:00 AM
- **Function:** `calculate_daily_statistics_job()`
- **What it does:**
  - Calculates statistics for the previous day
  - Metrics: total users, active users, sessions, average duration
  - Creates/updates record in `system_statistics` table

**Example Log Output:**
```
[Statistics Job] Calculating statistics for 2026-02-08
[Statistics Job] ✓ Statistics calculated - Date: 2026-02-08, Users: 1500, Active: 450, Sessions: 890, Avg Duration: 12.34 min
```

### Job 2: Log Cleanup (7 days)
- **Schedule:** Every day at 3:00 AM
- **Function:** `cleanup_old_logs_job()`
- **What it does:**
  - Finds logs older than 7 days in R2
  - Deletes them to save storage
  - Logs the number of deleted files

**Example Log Output:**
```
[Cleanup Job] ✓ Deleted 45 old log files (cutoff: 2026-02-02)
```

---

## 📊 R2 Storage Structure

```
rekapo/
├── profile_photos/
├── audios/
└── logs/
    └── 2026/
        └── 02/
            └── 09/
                ├── user_123_14-30-00.json
                ├── user_123_14-40-00.json
                ├── user_456_15-20-00.json
                └── user_789_16-05-00.json
```

**Each file contains:**
```json
{
  "user_id": 123,
  "user_email": "user@example.com",
  "batch_timestamp": "2026-02-09T14:30:10.000Z",
  "logs": [
    {
      "level": "error",
      "message": "Failed to upload photo: Network timeout",
      "timestamp": "2026-02-09T14:30:00.000Z"
    },
    {
      "level": "info",
      "message": "User logged in successfully",
      "timestamp": "2026-02-09T14:28:00.000Z"
    }
  ]
}
```

---

## 🎛️ Viewing Logs

### Option 1: Admin API (Easiest)
Use the admin endpoints above with your admin token.

### Option 2: Cloudflare Dashboard
1. Go to [Cloudflare R2 Dashboard](https://dash.cloudflare.com/)
2. Click bucket: `rekapo`
3. Browse: `logs/2026/02/09/`
4. Click file to download and view

### Option 3: AWS CLI (Advanced)
```bash
# Configure with R2 credentials
aws configure set aws_access_key_id YOUR_KEY
aws configure set aws_secret_access_key YOUR_SECRET

# List files
aws s3 ls s3://rekapo/logs/2026/02/09/ \
  --endpoint-url=YOUR_R2_ENDPOINT

# Download file
aws s3 cp s3://rekapo/logs/2026/02/09/user_123.json . \
  --endpoint-url=YOUR_R2_ENDPOINT
```

---

## 💰 Cost & Storage

### Cloudflare R2 Pricing
- **Free Tier:** 10 GB storage forever
- **Operations:** 1M reads/month, 1M writes/month (free)
- **Egress:** FREE (no bandwidth charges)

### Your Estimated Usage
- **1000 users** × **100 logs/day** = 100,000 logs/day
- **Average log size:** ~1 KB
- **Daily storage:** ~100 MB
- **Monthly storage:** ~3 GB
- **With 7-day retention:** Always under 1 GB

**Result:** ✅ FREE for years!

---

## 🔧 Troubleshooting

### R2 Client Not Initialized
**Error:** `R2 client not configured`

**Solution:**
1. Check `.env` file has all R2 credentials (R2_ENDPOINT_URL, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME)
2. Restart the backend server
3. Check logs for R2 initialization message

### Scheduler Not Starting
**Error:** Jobs not running at scheduled time

**Solution:**
1. Check server timezone: `date` (Linux/Mac) or `Get-Date` (Windows)
2. Verify logs show: `✓ Background Scheduler Started Successfully`
3. Check for errors in startup logs

### Log Files Not Appearing in R2
**Error:** Logs sent but not in R2 bucket

**Solution:**
1. Check R2 bucket name is correct in `.env` (R2_BUCKET_NAME)
2. Verify API token has **Edit** permissions
3. Check backend logs for write errors
4. Test with: `GET /api/logs/files` (admin endpoint)
5. Verify logs appear in the `logs/` folder within your bucket

### Statistics Not Calculating
**Error:** No statistics in database after 2 AM

**Solution:**
1. Check backend is running continuously (use PM2 or systemd)
2. View logs around 2:00 AM for job execution
3. Manually trigger: `POST /admin/statistics/calculate/2026-02-08` (admin)

---

## 🧪 Testing

### Test Log Writing (Development)
```bash
# Get auth token first
TOKEN="your_jwt_token"

# Send test logs
curl -X POST "http://localhost:8000/api/logs/write" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "logs": [
      {"level": "info", "message": "Test log", "timestamp": "2026-02-09T14:30:00.000Z"}
    ],
    "batch_timestamp": "2026-02-09T14:30:10.000Z"
  }'
```

### Test Admin Endpoints
```bash
ADMIN_TOKEN="your_admin_jwt_token"

# List log files
curl "http://localhost:8000/api/logs/files?date=2026-02-09" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Get recent errors
curl "http://localhost:8000/api/logs/errors/recent?hours=24" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Manual cleanup (test with higher value to be safe)
curl -X DELETE "http://localhost:8000/api/logs/cleanup?days=14" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### Test Cron Jobs Manually
You can trigger the jobs manually in Python:

```python
from utils.scheduler import calculate_daily_statistics_job, cleanup_old_logs_job

# Test statistics calculation
calculate_daily_statistics_job()

# Test log cleanup
cleanup_old_logs_job()
```

---

## 📚 Related Documentation

- [LOGGER_BACKEND_SETUP.md](./LOGGER_BACKEND_SETUP.md) - Original setup guide
- [SYSTEM_STATISTICS_API.md](./SYSTEM_STATISTICS_API.md) - Statistics API docs
- [Cloudflare R2 Docs](https://developers.cloudflare.com/r2/)
- [APScheduler Docs](https://apscheduler.readthedocs.io/)

---

## ✅ Summary

**What's been implemented:**
1. ✅ Complete logging API with R2 storage
2. ✅ Admin endpoints for viewing and managing logs
3. ✅ Automated log cleanup (7-day retention)
4. ✅ Automated daily statistics calculation
5. ✅ Background scheduler with 2 cron jobs
6. ✅ Proper error handling and logging

**Files created/modified:**
- `routes/logs.py` - New logging API endpoints
- `utils/scheduler.py` - New scheduler with cron jobs
- `main.py` - Added scheduler startup/shutdown + logs router
- `requirements.txt` - Added apscheduler
- `config/config.py` - Added R2 logs prefix config

**Next steps:**
1. ~~Create R2 bucket~~ (Already done - using `rekapo` bucket)
2. ~~Get R2 credentials~~ (Already configured in `.env`)
3. Install dependencies: `pip install -r requirements.txt`
4. Restart backend
5. Test with mobile app logging

---

**Need help?** Check the troubleshooting section or review the server logs for detailed error messages.
