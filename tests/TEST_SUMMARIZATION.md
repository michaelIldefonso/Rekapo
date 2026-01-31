# Summarization Tests

Comprehensive test suite for BART-based meeting summarization functionality.

## Test Coverage

The test suite includes 6 different test scenarios:

1. **Model Loading & Caching** - Verifies the summarizer model loads correctly and caching works
2. **Basic Text Summarization** - Tests simple text summarization with compression metrics
3. **Empty Text Handling** - Ensures empty inputs are handled gracefully
4. **Transcription Chunks** - Tests summarizing multiple Taglish transcription chunks
5. **Meeting Segments with Timing** - Tests summarizing segments with timestamps and durations
6. **Long Text** - Tests real-world meeting scenario with longer text

## Running the Tests

### Prerequisites
```bash
# Make sure you have the required packages
pip install transformers torch
```

### Run Tests
```bash
# From the project root
python tests/test_summarization.py
```

### First Run Note
⚠️ **The first run will download the BART model (~1.6GB) from HuggingFace.**

This may take several minutes depending on your internet connection. Subsequent runs will use the cached model.

## Sample Output

```
🧪 SUMMARIZATION TEST SUITE
======================================================================
Testing BART-based summarization for meeting transcriptions
Model: facebook/bart-large-cnn
Device: CPU (for testing)

======================================================================
🧪 Test 1: Basic Text Summarization
======================================================================
📝 Original Text:
In today's meeting, we discussed the implementation...
📊 Original Length: 80 words

✅ Summarization Successful!
  Summary: The team decided to use faster-whisper for improved...
  Original Word Count: 80
  Compression Ratio: 65.0%

======================================================================
📊 TEST SUMMARY
======================================================================
  ✅ PASS: Model Loading
  ✅ PASS: Basic Summarization
  ✅ PASS: Empty Text
  ✅ PASS: Transcription Chunks
  ✅ PASS: Meeting Segments
  ✅ PASS: Long Text

----------------------------------------------------------------------
  Total: 6/6 tests passed (100.0%)
======================================================================
```

## Test Parameters

- **Device**: CPU (for testing compatibility)
- **Model**: facebook/bart-large-cnn
- **Max Length**: 80-150 tokens (varies by test)
- **Min Length**: 20-50 tokens (varies by test)

## Integration with Main Application

The summarization is used in the WebSocket endpoint (`/api/ws/transcribe`) which automatically generates summaries every 10 transcription chunks.

## Troubleshooting

### Out of Memory
If you get OOM errors, the model is trying to use GPU. Force CPU mode:
```python
result = summarize_text(text="...", device="cpu")
```

### Model Download Fails
If the download fails, manually download:
```python
from transformers import pipeline
pipeline("summarization", model="facebook/bart-large-cnn")
```

### Import Errors
Make sure you're running from the project root and the virtual environment is activated.
