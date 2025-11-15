# Session History API Documentation

This document describes the session history API endpoints for retrieving user sessions and their details.

## API Flow

1. **List Sessions** - User sees all their sessions with titles
2. **Get Session Details** - User clicks a session to view full transcription, translation, and summaries

---

## 1. List All Sessions (Session History)

**Endpoint:** `GET /api/sessions`

**Description:** Retrieves a list of all sessions for the authenticated user, showing session titles and basic information.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `skip` (optional): Number of sessions to skip for pagination (default: 0)
- `limit` (optional): Maximum number of sessions to return (default: 50, max: 100)

**Response:** `200 OK`

```json
[
  {
    "id": 1,
    "user_id": 123,
    "session_title": "Team Meeting - Project Alpha",
    "start_time": "2025-11-11T10:00:00",
    "end_time": "2025-11-11T11:30:00",
    "status": "completed",
    "created_at": "2025-11-11T10:00:00"
  },
  {
    "id": 2,
    "user_id": 123,
    "session_title": "Client Discussion",
    "start_time": "2025-11-10T14:00:00",
    "end_time": null,
    "status": "recording",
    "created_at": "2025-11-10T14:00:00"
  }
]
```

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/sessions?limit=20" \
  -H "Authorization: Bearer your_token_here"
```

---

## 2. Get Complete Session Details

**Endpoint:** `GET /api/sessions/{session_id}/details`

**Description:** Retrieves complete session data including all recording segments with transcriptions, translations, and summaries. Called when user clicks on a session title.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Path Parameters:**
- `session_id` (required): The ID of the session to retrieve

**Response:** `200 OK`

```json
{
  "id": 1,
  "user_id": 123,
  "session_title": "Team Meeting - Project Alpha",
  "start_time": "2025-11-11T10:00:00",
  "end_time": "2025-11-11T11:30:00",
  "status": "completed",
  "created_at": "2025-11-11T10:00:00",
  "recording_segments": [
    {
      "id": 1,
      "segment_number": 1,
      "audio_path": "audiios/session_1/segment_1.wav",
      "transcript_text": "Magandang umaga po, welcome sa meeting natin today.",
      "english_translation": "Good morning, welcome to our meeting today.",
      "created_at": "2025-11-11T10:01:30"
    },
    {
      "id": 2,
      "segment_number": 2,
      "audio_path": "audiios/session_1/segment_2.wav",
      "transcript_text": "Tatalakayin natin ang progress ng Project Alpha.",
      "english_translation": "We will discuss the progress of Project Alpha.",
      "created_at": "2025-11-11T10:02:45"
    },
    {
      "id": 3,
      "segment_number": 3,
      "audio_path": "audiios/session_1/segment_3.wav",
      "transcript_text": "Ang development team ay natapos na yung backend API.",
      "english_translation": "The development team has finished the backend API.",
      "created_at": "2025-11-11T10:04:12"
    }
  ],
  "summaries": [
    {
      "id": 1,
      "chunk_range_start": 1,
      "chunk_range_end": 10,
      "summary_text": "The team discussed the progress of Project Alpha. The backend API development has been completed. Frontend integration is scheduled for next week. The team reviewed blockers and assigned action items.",
      "generated_at": "2025-11-11T10:15:00"
    },
    {
      "id": 2,
      "chunk_range_start": 11,
      "chunk_range_end": 20,
      "summary_text": "Discussion about deployment strategy and timeline. Team agreed to use staging environment for testing. Production deployment planned for end of month after QA approval.",
      "generated_at": "2025-11-11T10:30:00"
    }
  ],
  "total_segments": 25,
  "total_duration": null
}
```

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/sessions/1/details" \
  -H "Authorization: Bearer your_token_here"
```

**Response Fields:**

### Session Information
- `id`: Session ID
- `user_id`: Owner's user ID
- `session_title`: Title of the meeting
- `start_time`: When recording started
- `end_time`: When recording ended (null if still recording)
- `status`: Session status (`recording`, `completed`, `failed`)
- `created_at`: Timestamp when session was created

### Recording Segments
Array of audio segments with:
- `id`: Segment ID
- `segment_number`: Sequential segment number
- `audio_path`: Path to audio file
- `transcript_text`: Original transcription (Taglish/Filipino)
- `english_translation`: English translation
- `created_at`: When segment was processed

### Summaries
Array of AI-generated summaries (created every 10 segments):
- `id`: Summary ID
- `chunk_range_start`: First segment number in summary
- `chunk_range_end`: Last segment number in summary
- `summary_text`: AI-generated summary
- `generated_at`: When summary was created

### Statistics
- `total_segments`: Total number of recording segments
- `total_duration`: Total duration in seconds (currently null, can be added later)

---

## Error Responses

**404 Not Found** - Session doesn't exist or user doesn't have access
```json
{
  "detail": "Session not found"
}
```

**401 Unauthorized** - Invalid or missing authentication token
```json
{
  "detail": "Not authenticated"
}
```

---

## Mobile App Integration Example

```javascript
// 1. Fetch session list on history page load
async function loadSessionHistory() {
  const response = await fetch('http://api.rekapo.com/api/sessions?limit=50', {
    headers: {
      'Authorization': `Bearer ${userToken}`
    }
  });
  const sessions = await response.json();
  
  // Display sessions in list view
  displaySessionList(sessions);
}

// 2. When user clicks a session, fetch complete details
async function loadSessionDetails(sessionId) {
  const response = await fetch(`http://api.rekapo.com/api/sessions/${sessionId}/details`, {
    headers: {
      'Authorization': `Bearer ${userToken}`
    }
  });
  const sessionDetails = await response.json();
  
  // Display full transcription, translations, and summaries
  displayTranscripts(sessionDetails.recording_segments);
  displaySummaries(sessionDetails.summaries);
}
```

---

## Notes

- All timestamps are in ISO 8601 format
- Sessions are ordered by `start_time` in descending order (newest first)
- Recording segments are ordered by `segment_number` in ascending order
- Summaries are ordered by `chunk_range_start` in ascending order
- Users can only access their own sessions
- Soft-deleted sessions are not included in results
