# Session Status Handling

## Session Status Values

A session can have one of three statuses:

### 1. **recording** (Default)
- Active session with WebSocket connected
- User is currently recording audio segments
- Can receive new audio chunks

### 2. **completed** (Auto-set on disconnect with segments)
- Session ended (either manually by user OR automatically when WebSocket disconnects)
- Has at least 1 recorded segment
- All segments are saved to database
- User can view full transcription in session history
- Can optionally generate full session summary via API

### 3. **failed** (Auto-set)
- WebSocket disconnected with no segments recorded
- OR unexpected error occurred during session
- Indicates session had no usable content
- Typically can be safely deleted

---

## Automatic Status Updates

### On WebSocket Disconnect

When a WebSocket connection is lost (app closed, internet dropped, etc.), the backend automatically:

```python
if session.status == "recording":
    if segment_count > 0:
        session.status = "completed"  # Has content, mark as done
    else:
        session.status = "failed"     # No content, mark as failed
    session.end_time = datetime.now()
```

**Key point:** All segments are saved in real-time as they arrive, so nothing is lost on disconnect.

### On WebSocket Error

If an unexpected error occurs:
- Session status is set to `"failed"`
- End time is recorded
- Error is logged

---

## Best Practices

### Mobile App Flow

```javascript
// 1. Start recording
const session = await createSession({ title: "Meeting" });
const ws = new WebSocket(`/api/ws/transcribe`);

// 2. When user explicitly clicks "End Meeting" button
async function endMeeting(sessionId) {
  // Mark as completed
  await fetch(`/api/sessions/${sessionId}`, {
    method: 'PATCH',
    body: JSON.stringify({ status: "completed" })
  });
  
  // Optional: Generate full session summary
  const summary = await fetch(`/api/sessions/${sessionId}/generate-summary`, {
    method: 'POST'
  });
  
  // Close WebSocket
  ws.close();
  
  // Show summary to user
  displaySummary(summary.data);
}

// Note: If user force-closes app or internet drops, backend automatically
// marks session as "completed" (if has segments) or "failed" (if no segments).
// No client-side handling needed - everything is saved in real-time.
```

### Backend API Usage

**Check session status:**
```http
GET /api/sessions/123
```

**Update status manually:**
```http
PATCH /api/sessions/123
{
  "status": "completed"
}
```

**Generate full session summary:**
```http
POST /api/sessions/123/generate-summary
```

---

## Session Lifecycle Diagram

```
┌─────────────┐
│  recording  │ ◄── Initial status when session created
└──────┬──────┘
       │
       ├── User clicks "End Meeting" button (manual)
       │   └──► completed
       │         └──► Generate full summary (optional)
       │
       ├── WebSocket disconnects (has segments) - AUTO
       │   └──► completed
       │         └──► All segments already saved
       │              User can view in history
       │
       └── WebSocket disconnects (no segments) or error - AUTO
           └──► failed
                 └──► Can be deleted
```

---

## Migration Notes

If you have existing sessions with status "recording" from before this update:
- They will remain as "recording" indefinitely
- You can manually update them via API
- Or the next websocket disconnect will auto-update them

To clean up old "recording" sessions:
```sql
UPDATE sessions 
SET status = 'completed', end_time = NOW() 
WHERE status = 'recording' 
  AND created_at < NOW() - INTERVAL '1 day';
```

---

## Status Summary Table

| Status | How Set | Has Segments | End Time | Next Action |
|--------|---------|--------------|----------|-------------|
| recording | Auto (on create) | Maybe | NULL | Continue recording |
| completed | Manual OR Auto (disconnect) | Yes | Set | View in history / Generate summary |
| failed | Auto (error/empty) | No | Set | Delete or retry |
