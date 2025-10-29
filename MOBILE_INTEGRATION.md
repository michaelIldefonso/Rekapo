# Mobile Integration Guide - Rekapo Meeting Summarizer

## Overview
This guide shows how to integrate the Rekapo backend with your mobile app for real-time meeting transcription with Taglish support.

## WebSocket Endpoint
```
ws://your-server:8000/api/ws/transcribe
```

## Workflow

### 1. Start a Meeting Session
Create a session in your database before starting the WebSocket connection:
```http
POST /api/sessions
{
  "user_id": 123,
  "session_title": "Team Standup Meeting"
}
```

### 2. Connect to WebSocket
```javascript
// Example for React Native / JavaScript
const ws = new WebSocket('ws://localhost:8000/api/ws/transcribe');

ws.onopen = () => {
  console.log('Connected to transcription service');
};

ws.onmessage = (event) => {
  const response = JSON.parse(event.data);
  
  if (response.status === 'connected') {
    console.log('Ready to send audio');
  }
  
  if (response.status === 'success') {
    console.log('Transcription:', response.transcription);
    console.log('Language:', response.language);
    // Display to user
  }
};
```

### 3. Send Audio Chunks (with VAD)
When VAD detects speech, send the audio chunk:

```javascript
// Convert audio buffer to base64
function arrayBufferToBase64(buffer) {
  let binary = '';
  const bytes = new Uint8Array(buffer);
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

// Send audio chunk
function sendAudioChunk(audioBuffer, sessionId, segmentNumber) {
  const base64Audio = arrayBufferToBase64(audioBuffer);
  
  ws.send(JSON.stringify({
    session_id: sessionId,
    segment_number: segmentNumber,
    audio: base64Audio,
    filename: `segment_${segmentNumber}.wav`,
    language: null,  // Auto-detect Tagalog/English
    model: "small"   // Can use "base" for faster, "medium" for better accuracy
  }));
}
```

### 4. Receive Transcription
```javascript
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch(data.status) {
    case 'connected':
      console.log('WebSocket connected');
      break;
      
    case 'processing':
      console.log(`Processing segment ${data.segment_number}...`);
      showLoadingIndicator();
      break;
      
    case 'success':
      hideLoadingIndicator();
      displayTranscription({
        text: data.transcription,
        language: data.language,
        segmentNumber: data.segment_number,
        duration: data.duration
      });
      break;
      
    case 'error':
      console.error('Error:', data.message);
      showErrorMessage(data.message);
      break;
  }
};
```

## Message Format

### Request (Mobile → Server)
```json
{
  "session_id": 123,
  "segment_number": 1,
  "audio": "base64_encoded_audio_data",
  "filename": "chunk_1.wav",
  "language": null,
  "model": "small"
}
```

### Response (Server → Mobile)
```json
{
  "status": "success",
  "message": "Transcription completed",
  "session_id": 123,
  "segment_number": 1,
  "transcription": "Kumusta! Let's start the meeting.",
  "english_translation": null,
  "language": "tl",
  "language_probability": 0.95,
  "duration": 3.5,
  "segments": [
    {
      "start": 0.0,
      "end": 1.5,
      "text": "Kumusta!"
    },
    {
      "start": 1.5,
      "end": 3.5,
      "text": "Let's start the meeting."
    }
  ]
}
```

## Best Practices for Mobile

### 1. VAD Configuration
- Use Web Audio API's `analyser` or a library like `@ricky0123/vad-web`
- Recommended threshold: -50dB to -30dB
- Minimum speech duration: 300ms
- Pause duration before sending: 500-800ms

### 2. Audio Format
- **Recommended**: WAV, 16kHz, mono, 16-bit
- Smaller file size: Opus or AAC (Whisper supports most formats)
- Lower sample rates (8kHz-16kHz) work well for speech

### 3. Chunk Size
- **Optimal**: 2-5 seconds per chunk
- Too small: Poor accuracy, high overhead
- Too large: Increased latency, worse mobile experience

### 4. Network Handling
```javascript
// Reconnection logic
let reconnectAttempts = 0;
const maxReconnectAttempts = 5;

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  if (reconnectAttempts < maxReconnectAttempts) {
    setTimeout(() => {
      reconnectAttempts++;
      console.log(`Reconnecting... (${reconnectAttempts}/${maxReconnectAttempts})`);
      connectWebSocket();
    }, 2000 * reconnectAttempts); // Exponential backoff
  }
};
```

### 5. Battery Optimization
- Only connect WebSocket when actively recording
- Disconnect when app goes to background
- Use efficient audio encoding

## Model Selection

### Speed vs Accuracy Trade-off
| Model | Speed | Accuracy | Best For |
|-------|-------|----------|----------|
| `tiny` | Fastest | Basic | Quick notes, simple speech |
| `base` | Very Fast | Good | Most mobile use cases |
| `small` | **Recommended** | Very Good | **Balanced mobile performance** |
| `medium` | Slow | Excellent | High accuracy needed |
| `large-v3` | Very Slow | Best | Server-side only |

**For mobile: Use `small` or `base`**

## Example: React Native Implementation

```javascript
import { Audio } from 'expo-av';

class MeetingRecorder {
  constructor(sessionId) {
    this.sessionId = sessionId;
    this.segmentNumber = 0;
    this.ws = null;
    this.recording = null;
  }

  async connect() {
    this.ws = new WebSocket('ws://your-server:8000/api/ws/transcribe');
    
    this.ws.onopen = () => {
      console.log('Connected to Rekapo');
    };
    
    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.handleTranscription(data);
    };
  }

  async startRecording() {
    await Audio.requestPermissionsAsync();
    
    const { recording } = await Audio.Recording.createAsync(
      Audio.RecordingOptionsPresets.HIGH_QUALITY
    );
    
    this.recording = recording;
  }

  async sendChunk() {
    if (!this.recording) return;
    
    await this.recording.stopAndUnloadAsync();
    const uri = this.recording.getURI();
    
    // Read file as base64
    const base64Audio = await FileSystem.readAsStringAsync(uri, {
      encoding: FileSystem.EncodingType.Base64,
    });
    
    // Send to server
    this.segmentNumber++;
    this.ws.send(JSON.stringify({
      session_id: this.sessionId,
      segment_number: this.segmentNumber,
      audio: base64Audio,
      filename: `segment_${this.segmentNumber}.wav`,
      model: 'small'
    }));
    
    // Start new recording for next chunk
    await this.startRecording();
  }

  handleTranscription(data) {
    if (data.status === 'success') {
      // Update UI with transcription
      console.log('Transcription:', data.transcription);
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
    }
    if (this.recording) {
      this.recording.stopAndUnloadAsync();
    }
  }
}
```

## Database Schema Reference

Your mobile app should create sessions via API:

```sql
-- Create session
INSERT INTO sessions (user_id, session_title, start_time, status)
VALUES (123, 'Team Meeting', NOW(), 'recording');

-- Backend automatically saves transcriptions to:
-- recording_segments table with:
--   - session_id
--   - segment_number
--   - audio_path
--   - transcript_text (Taglish)
--   - english_translation (when implemented)
```

## Next Steps

1. **Translation**: Add LLM for English translation of Taglish text
2. **Summarization**: Implement meeting summary generation
3. **Speaker Diarization**: Identify different speakers
4. **Search**: Full-text search across meetings

## Troubleshooting

### Connection Issues
- Check CORS settings in production
- Verify WebSocket URL (ws:// not http://)
- Check firewall/network settings

### Audio Quality Issues
- Ensure 16kHz sample rate
- Use mono channel
- Check microphone permissions

### Performance Issues
- Reduce model size (use `base` instead of `small`)
- Increase chunk size
- Enable VAD filtering

## Support
For issues or questions, check the API docs at `/docs`
