# Full Pipeline Integration Test

Comprehensive end-to-end test of the complete transcription pipeline without WebSocket/Auth dependencies.

## Pipeline Flow

```
Audio File(s)
    ↓
[1] Whisper Transcription
    • Hallucination filtering (no_speech_prob)
    • Common phrase filtering ("You", "Thank you", etc.)
    • Character cleaning
    ↓
[2] Preprocessing
    • Taglish validation
    • Language forcing (tl/en only)
    • Character verification
    ↓
[3] Translation
    • NLLB or Qwen (based on config)
    • Tagalog/English → English
    ↓
[4] Summarization (every 10 segments)
    • BART-based summarization
    • Combines last 10 chunks
    • Compression metrics
    ↓
Output Results
```

## Features

### ✅ Tests All Components
- **Whisper**: Transcription with hallucination filtering
- **Preprocessing**: Taglish validation and cleaning
- **Translation**: Both NLLB and Qwen models supported
- **Summarization**: Automatic summaries every 10 segments

### ✅ Real Production Flow
- Matches the WebSocket endpoint logic exactly
- Same parameters and configurations
- Same error handling and validation

### ✅ Two Test Modes
1. **Auto-detect**: Finds audio files in `audiios/` directory
2. **Manual**: Specify custom audio file paths

### ✅ Rich Output
- Color-coded console output
- Step-by-step progress tracking
- Detailed metrics and results
- Summary generation feedback

## Usage

### Run the Test

```bash
# From project root
python tests/test_full_pipeline.py
```

### Test Mode 1: Auto-detect
```
Select test mode:
  1. Auto-detect sample audio from audiios/
  2. Manual audio file paths

Choice (1 or 2): 1
```

Automatically finds and tests audio files from the first session in `audiios/` directory. Tests up to 15 segments.

### Test Mode 2: Manual Paths
```
Select test mode:
  1. Auto-detect sample audio from audiios/
  2. Manual audio file paths

Choice (1 or 2): 2

Enter audio file paths (one per line, empty line to finish):
Audio file 1: C:/audio/segment1.wav
Audio file 2: C:/audio/segment2.wav
Audio file 3: [press Enter to finish]
```

## Sample Output

```
======================================================================
🧪 FULL PIPELINE INTEGRATION TEST
======================================================================
Audio → Whisper → Preprocessing → Translation → Summarization
======================================================================

🔍 SEARCHING FOR SAMPLE AUDIO FILES
Using session: session_1
✅ Found 12 audio files
  - segment_1.wav
  - segment_2.wav
  ...

======================================================================
🎯 FULL PIPELINE TEST - MULTIPLE SEGMENTS + SUMMARIZATION
======================================================================
Number of Audio Files: 12
Translation Model: NLLB
Summarization: Every 10 segments

──────────────────────────────────────────────────────────────────────
Processing Segment 1/12: segment_1.wav
──────────────────────────────────────────────────────────────────────

[STEP 1] Whisper Transcription (with hallucination filtering)
✅ Transcription completed
  Original Text: Magandang umaga po sa inyong lahat...
  Language: tl (confidence: 98.50%)
  Duration: 4.20s
  Segments: 1

[STEP 2] Preprocessing - Taglish Validation
✅ Text validated as Taglish

[STEP 3] Translation to English (NLLB)
✅ Translation completed
  English: Good morning to all of you...

──────────────────────────────────────────────────────────────────────
Processing Segment 10/12: segment_10.wav
──────────────────────────────────────────────────────────────────────

[STEP 4] Generating Summary (Segments 1 to 10)
✅ Summary generated
  Summary: The meeting discussed implementing real-time transcription...
  Chunks: 10
  Compression: 45/230 words

======================================================================
📊 PIPELINE TEST RESULTS
======================================================================
Total Segments Processed: 12
Summaries Generated: 1

All Transcriptions:
  Segment #1:
    Original: Magandang umaga po sa inyong lahat...
    English:  Good morning to all of you...

Generated Summaries:
  Chunks 1-10:
    The meeting discussed implementing real-time transcription...
```

## What Gets Tested

### ✅ Whisper Transcription
- Audio file loading
- Language detection
- Hallucination filtering (`no_speech_prob > 0.6`)
- Common phrase filtering ("You", "Thank you", etc.)
- Character cleaning
- Segment-level details

### ✅ Preprocessing
- Taglish character validation
- Non-Latin character detection
- Language code forcing (tl/en only)
- Empty transcription handling

### ✅ Translation
- NLLB model translation
- Qwen LLM translation
- Language code mapping
- Error handling

### ✅ Summarization
- Every 10 segments triggering
- Last 10 chunks selection
- BART summarization
- Compression metrics

## Configuration

The test respects your environment configuration:

```python
# From config/config.py
ENABLE_TAGLISH_PREPROCESSING = True
```

Translation uses NLLB-200 model for Tagalog to English translation.

## Requirements

All dependencies from the main application:
- `faster-whisper`
- `transformers`
- `torch`
- `nllb` or `qwen` model files

## Notes

### GPU vs CPU
The test uses CUDA (GPU) by default:
```python
device="cuda"
```

To force CPU mode, edit the test file and change to:
```python
device="cpu"
```

### Audio File Formats
Supported formats:
- `.wav`
- `.mp3`
- `.webm`

### Hallucination Filtering
The test includes the new hallucination detection:
- Filters segments with `no_speech_prob > 0.6`
- Removes common Whisper hallucinations
- Warns about filtered segments

### Performance
Processing time depends on:
- Audio file length
- Number of segments
- GPU availability

## Troubleshooting

### No audio files found
```
❌ No session directories found in audiios/
```
**Solution**: Use manual mode (option 2) or add audio files to `audiios/session_1/`

### Translation fails
```
❌ Translation failed: Model not loaded
```
**Solution**: Check that NLLB model is downloaded and configured in `ai_models/translator/`

### Out of memory
```
❌ CUDA out of memory
```
**Solution**: 
- Reduce number of test files
- Use CPU mode
- Close other GPU applications

### Summarization fails
```
❌ Summarization failed: BART model not found
```
**Solution**: The BART model will download automatically (~1.6GB) on first run

## Integration with WebSocket Endpoint

This test replicates the exact flow from `routes/whisper.py`:

| WebSocket Endpoint | Test Pipeline |
|-------------------|---------------|
| WebSocket receive audio | Load audio file |
| Whisper transcription | ✅ Same |
| Hallucination filtering | ✅ Same |
| Taglish validation | ✅ Same |
| Translation (NLLB/Qwen) | ✅ Same |
| Summarization every 10 | ✅ Same |
| WebSocket send response | Print to console |
| Database save | ❌ Skipped (test only) |

The only differences:
- No WebSocket communication
- No authentication
- No database saving
- Results printed instead of sent to client
