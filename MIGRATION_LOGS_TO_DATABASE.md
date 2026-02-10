# Migration: Logs from R2 to Database

## Overview
Migrated application logs from Cloudflare R2 (JSON files) to PostgreSQL database for faster queries, simpler code, and better integration with the existing database.

## Changes Made

### 1. Database Schema
Added new `app_logs` table to [db/db.py](db/db.py):
- Stores log entries with user_id, level, message, timestamp
- Includes metadata: app_version, platform, batch_timestamp
- Indexed on user_id, level, timestamp for fast queries
- Foreign key to users table with CASCADE delete

### 2. API Endpoints Restructured

**Mobile App Endpoint (routes/logs.py):**
- **POST /api/logs/write** or **POST /api/logs/app** - Write logs from mobile app (authenticated users)

**Admin Endpoints (admin/admin_logs.py):**
- **GET /admin/logs/summary** - Daily log summary with counts by level
- **GET /admin/logs/recent** - Get recent logs with optional level filter
- **GET /admin/logs/errors/recent** - Get errors from last N hours
- **GET /admin/logs/stats** - Dashboard statistics (counts, top errors, top error users)
- **GET /admin/logs/user/{user_id}** - Get logs for specific user
- **GET /admin/logs/user/email/{email}** - Search logs by email
- **DELETE /admin/logs/cleanup** - Delete old logs
- `cleanup_old_logs_job()` - Background job for automatic cleanup

**Separation of Concerns:**
- Mobile app writes logs to `/api/logs/write` (no admin access needed)
- All viewing/management is admin-only under `/admin/logs/*`

### 3. Dependencies & Imports
- Removed boto3 and R2 client from log writing
- Updated [main.py](main.py) to include `admin_logs_router`
- Updated [utils/scheduler.py](utils/scheduler.py) to import cleanup function from admin module

## SQL Commands

### Create Table Manually (if needed)

```sql
CREATE TABLE app_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    level VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    "timestamp" TIMESTAMP NOT NULL,
    batch_timestamp TIMESTAMP,
    app_version VARCHAR(50),
    platform VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW() NOT NULL
);

-- Create indexes for fast queries
CREATE INDEX idx_app_logs_user_id ON app_logs(user_id);
CREATE INDEX idx_app_logs_level ON app_logs(level);
CREATE INDEX idx_app_logs_timestamp ON app_logs("timestamp");
CREATE INDEX idx_app_logs_user_timestamp ON app_logs(user_id, "timestamp");

-- Add table comment
COMMENT ON TABLE app_logs IS 'Stores application logs from mobile apps';
COMMENT ON COLUMN app_logs.level IS 'Log level: info, warn, error, network';
COMMENT ON COLUMN app_logs."timestamp" IS 'Log timestamp from client';
COMMENT ON COLUMN app_logs.batch_timestamp IS 'Batch submission timestamp';
```

### Connect to Railway PostgreSQL

```bash
# Option 1: Using DATABASE_URL from Railway
psql "postgresql://postgres:YOUR_PASSWORD@HOST:PORT/railway"

# Option 2: If you have DATABASE_URL environment variable 
psql "$DATABASE_URL"

# Option 3: Copy from Railway Variables tab and use directly
psql "postgresql://postgres:PASSWORD@containers-us-west-123.railway.app:7654/railway"
```

### Get DATABASE_URL from Railway
1. Go to Railway Dashboard → Your Project
2. Click on PostgreSQL service
3. Go to **Variables** tab
4. Copy **DATABASE_URL** value (or **DATABASE_PUBLIC_URL** for external access)
5. Use it in the psql command above

### Verify Table Creation

```sql
-- Check if table exists
\dt app_logs

-- Check table structure
\d app_logs

-- Check indexes
\di app_logs*

-- Count logs (should be 0 initially)
SELECT COUNT(*) FROM app_logs;
```

## Migration Notes

### Existing R2 Logs
- Historical logs in R2 are NOT automatically migrated
- Old R2 logs can remain for archival purposes
- New logs will only go to database from deployment forward
- To migrate existing logs, you would need a custom script (not included)

### Testing
1. Test the write endpoint first: POST /api/logs/write
2. Verify logs appear in database
3. Test admin endpoints for querying logs
4. Verify cleanup job runs successfully

## Benefits
✅ **10-100x faster queries** - Indexed database vs scanning JSON files  
✅ **Simpler code** - ~600 lines → ~300 lines  
✅ **Lower costs** - No R2 storage fees for logs  
✅ **Better filtering** - Native SQL WHERE/JOIN clauses  
✅ **Better analytics** - Can analyze with SQL, JOIN with users/sessions  
✅ **No external dependencies** - No boto3 or R2 credentials needed for logging  
✅ **Better separation of concerns** - App writes, admin views/manages

## File Structure
```
routes/logs.py           → Mobile app log writing only
admin/admin_logs.py      → Admin log viewing/management
db/db.py                 → AppLog model definition
utils/scheduler.py       → Background cleanup job
main.py                  → Router registration
```

## Rollback (if needed)
If you need to rollback:
1. Restore the old `routes/logs.py` from git history
2. Keep the `app_logs` table (doesn't hurt to have it)
3. Re-enable R2 credentials

## Deployment Steps
1. Pull latest code
2. Run migration to create `app_logs` table (or run SQL above manually)
3. Deploy application
4. Test log writing from mobile app
5. Verify logs appear in database
6. (Optional) Remove R2 logging environment variables
