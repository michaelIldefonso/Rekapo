# Logging Guide for Rekapo

## Overview
All logging has been refactored to use Python's standard `logging` module for production-ready observability. This is ideal for thesis testing as you can control verbosity without changing code.

## Log Levels

- **DEBUG** (10): Detailed diagnostic information
  - Audio file sizes, preprocessing details, file operations
  - Translation/transcription parameters
  - Context building, file renaming operations
  
- **INFO** (20): General informational messages ⭐ **Recommended for thesis testing**
  - Session lifecycle (created, initialized, completed)
  - Segment processing (transcription, translation, summary)
  - WebSocket connections/disconnections
  - Database operations (saves, updates)
  - Model operations (transcription started/completed)
  
- **WARNING** (30): Warning messages
  - Skipped segments (empty, non-Taglish characters)
  - Client disconnections during processing
  - File cleanup failures
  - Preprocessing failures (fallback to raw text)
  
- **ERROR** (40): Error messages
  - Database save errors
  - Translation failures
  - Summarization failures
  - WebSocket errors
  - Session status update failures

## Configuration

### Set Log Level via Environment Variable

```bash
# In your .env file

# For thesis testing (RECOMMENDED) - shows all key operations
LOG_LEVEL=INFO

# For debugging issues - shows ALL details
LOG_LEVEL=DEBUG

# For production - only warnings and errors
LOG_LEVEL=WARNING

# For critical issues only
LOG_LEVEL=ERROR
```

### Default Behavior
If `LOG_LEVEL` is not set, it defaults to **INFO** level.

## Key Logs for Thesis Analysis

### Session Tracking
```
INFO [routes.whisper] 📝 Session 123 initialized in connection manager
INFO [routes.whisper] ✅ Session 123 marked as 'completed' (15 segments recorded)
INFO [routes.whisper] 📝 Generating final summary for session 123...
```

### Transcription Pipeline
```
INFO [routes.whisper] 🎙️ Starting transcription - Session: 123, Model: fine-tuned, Beam: 5, Temp: 0.2
INFO [routes.whisper] ✅ Transcription complete - Lang: tl, Confidence: 0.97, Duration: 3.45s
INFO [routes.whisper] 📝 Preprocessing applied - Session: 123
INFO [routes.whisper] 🌐 Starting translation - Session: 123, Lang: tl -> EN
INFO [routes.whisper] ✅ Translation complete - Session: 123
```

### Database Operations
```
INFO [routes.whisper] 💾 Segment saved to database - Session: 123, Segment: 5, Path: r2://...
```

### Summarization
```
INFO [routes.whisper] 📊 Summarization Check - Session: 123
INFO [routes.whisper]    Current Segment: #10
INFO [routes.whisper]    Total Segments: 10
INFO [routes.whisper]    Trigger Summary: True (every 10 segments)
INFO [routes.whisper] 🔄 TRIGGERING SUMMARIZATION - Session: 123, Segment: 10
INFO [routes.whisper] 📚 Fetched 10 transcriptions for session 123
INFO [routes.whisper] ✅ Summary generated - Session: 123, Length: 245 chars
INFO [routes.whisper] 💾 Summary saved to database - Session: 123, Range: 1-10
```

### Mobile Communication
```
INFO [routes.whisper] 📱 WebSocket connected - ready for recording
INFO [routes.whisper] 📱 Processing segment for session 123
INFO [routes.whisper] 📱 Transcription sent - Session: 123, Segment: #5, Lang: tl, Duration: 3.45s
INFO [routes.whisper] 📱 Summary sent - Session: 123, Chunks: 10
```

### Issues & Skipped Content
```
WARNING [routes.whisper] ⚠️ Empty transcription detected - Session: 123, Duration: 1.23s
WARNING [routes.whisper] ⚠️ Non-Taglish characters detected - Session: 123, Text: 你好...
WARNING [routes.whisper] 📱 Segment skipped - Session: 123, Reason: Segment was empty
WARNING [routes.whisper] Whisper detected unexpected language 'zh', defaulting to Tagalog
```

## Log Output Format

All logs follow this format:
```
2026-02-08 14:23:45 INFO [routes.whisper] 📱 WebSocket connected - ready for recording
^                   ^    ^                ^
Timestamp           Level Module          Message
```

## Log File Redirection

To save logs to a file for analysis:

```bash
# Redirect all output to file
python main.py > logs/rekapo_$(date +%Y%m%d_%H%M%S).log 2>&1

# Or with uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 > logs/rekapo.log 2>&1

# Or run in background with nohup
nohup uvicorn main:app --host 0.0.0.0 --port 8000 > logs/rekapo.log 2>&1 &
```

## Analyzing Logs for Thesis

### Count sessions processed today
```bash
grep "✅ Session.*marked as 'completed'" rekapo.log | wc -l
```

### Find average segments per session
```bash
grep "✅ Session.*marked as 'completed'" rekapo.log | grep -oP '\d+ segments' | awk '{sum+=$1; count++} END {print sum/count}'
```

### Find preprocessing application rate
```bash
echo "Total transcriptions: $(grep '✅ Transcription complete' rekapo.log | wc -l)"
echo "Preprocessing applied: $(grep '📝 Preprocessing applied' rekapo.log | wc -l)"
```

### Track skipped segments
```bash
grep "📱 Segment skipped" rekapo.log | wc -l
```

### Session duration analysis
```bash
grep "✅ Session.*marked as 'completed'" rekapo.log
```

## Tips for Thesis Testing

1. **Use INFO level** - Perfect balance of detail without overwhelming output
2. **Save logs to file** - Easier to analyze later with grep/awk
3. **Add session metadata** - Recording logging already includes session IDs for tracing
4. **Monitor warnings** - Track how often segments are skipped and why
5. **Capture full sessions** - Each session's logs are connected via session_id

## Troubleshooting

### Too much output?
Set `LOG_LEVEL=WARNING` to reduce noise

### Need more detail for debugging?
Set `LOG_LEVEL=DEBUG` to see all operations

### Want to track specific sessions?
```bash
grep "Session: 123" rekapo.log
```

### Monitor real-time
```bash
tail -f logs/rekapo.log
```

## Emojis in Logs

Emojis help quickly identify log categories:
- 📱 Mobile/WebSocket communication
- 🎙️ Transcription operations
- 🌐 Translation operations
- 📝 Text processing/preprocessing
- 📊 Statistics/analysis
- 💾 Database operations
- ✅ Success operations
- ⚠️ Warnings
- ❌ Errors
- 🔄 Background/async operations
- 🚀 Startup/initialization
- 🛑 Shutdown

These are safe for terminal output and log files, but if needed you can strip them:
```bash
sed 's/[^\x00-\x7F]//g' rekapo.log > rekapo_clean.log
```
