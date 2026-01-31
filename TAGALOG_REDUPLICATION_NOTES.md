# Tagalog Reduplication & Whisper Repetition Penalty

## Overview
This document explains how Whisper's repetition penalty interacts with legitimate Tagalog reduplication patterns.

## The Question
> "Won't Whisper's repetition penalty affect Tagalog reduplication like 'bili-bili' or 'kain-kain'?"

## Answer: **No Major Conflict** ✅

### Why It's Safe

#### 1. **Different Pipeline Stages**
```
Audio → [Whisper + repetition penalty] → Text → [Preprocessing + reduplication detection] → Translation
```
- **Whisper stage**: Prevents hallucinated repetitions during transcription
- **Preprocessing stage**: Detects and handles legitimate Tagalog patterns
- They work together, not against each other

#### 2. **Short vs Long Repetition**
| Pattern Type | Example | Whisper Behavior |
|-------------|---------|------------------|
| Tagalog reduplication (1-2 words) | "bili-bili", "kain kain" | ✅ Preserved (not blocked) |
| Hallucination (3+ words) | "thank you thank you thank you" | ❌ Blocked by `no_repeat_ngram_size=3` |
| Extreme repetition | "bili bili bili bili bili" | ⚠️ May be penalized (unusual in natural speech) |

#### 3. **Mild Penalty Settings**
```python
repetition_penalty = 1.1           # 10% penalty - very mild
no_repeat_ngram_size = 3          # Only blocks 3+ consecutive words
```

**For Tagalog specifically**, we now auto-adjust:
```python
if language == "tl":
    repetition_penalty = 1.05      # Even milder for Tagalog (5% penalty)
```

### Tagalog Reduplication Patterns Preserved

#### Full Reduplication (with/without hyphen)
- `bili-bili` → Both forms transcribed correctly
- `bili bili` → Detected by preprocessing regardless
- `kain-kain`, `laro-laro`, `takbo-takbo` → All preserved

#### CV-Reduplication (partial)
- `tatakbo` (ta-takbo) → Transcribed correctly
- `kakain` (ka-kain) → Transcribed correctly
- `lalaro` (la-laro) → Transcribed correctly

These are single words, so no repetition penalty applies.

### What Gets Blocked (Good!)

#### Whisper Hallucinations
```
"salamat salamat salamat salamat po"  ❌ Blocked (unnatural 4-word repetition)
"thank you thank you thank you"       ❌ Blocked (hallucination)
"okay okay okay okay okay"            ❌ Blocked (excessive)
```

#### Still Allowed (Natural Speech)
```
"bili bili ng mga prutas"             ✅ Allowed (reduplication + continuation)
"kain kain na tayo"                   ✅ Allowed (reduplication + continuation)
"maganda maganda yung lugar"          ✅ Allowed (emphasis in natural speech)
```

## Technical Details

### Whisper Parameter Effects

| Parameter | Value | Effect on Tagalog |
|-----------|-------|-------------------|
| `repetition_penalty` | 1.05 (Tagalog) | Very mild - won't suppress legitimate patterns |
| `repetition_penalty` | 1.1 (default) | Mild - safe for most cases |
| `no_repeat_ngram_size` | 3 | Blocks 3+ word repetitions only |
| `temperature` | 0.2 | Deterministic transcription |

### Preprocessing Detection

Our preprocessing pipeline handles ALL reduplication patterns **post-transcription**:

```python
# Full reduplication with hyphen
"bili-bili" → detect_reduplication() → base: "bili", is_reduplicated: True

# Full reduplication without hyphen  
"bili bili" → detect_reduplication() → base: "bili", is_reduplicated: True

# CV-reduplication
"tatakbo" → detect_reduplication() → base: "takbo", is_reduplicated: True
```

Then dictionary lookup on base form:
```python
"bili" → tagged as [verb: to buy]
"takbo" → tagged as [verb: to run]
```

## Recommendations

### For Tagalog/Taglish Audio

**Use these settings** (automatically applied if `language="tl"`):
```python
transcribe_audio_file(
    audio_path="audio.wav",
    language="tl",              # Auto-reduces repetition_penalty to 1.05
    repetition_penalty=1.05,    # Or manually set lower
    no_repeat_ngram_size=3      # Keep at 3 (safe for reduplication)
)
```

### For Mixed/Unknown Language

**Default settings are fine**:
```python
transcribe_audio_file(
    audio_path="audio.wav",
    language=None,              # Auto-detect
    repetition_penalty=1.1,     # Default
    no_repeat_ngram_size=3      # Default
)
```

### If You Notice Issues

**Symptoms of too aggressive penalty**:
- Whisper transcribes "bili ng" instead of "bili-bili ng"
- Missing reduplicative emphasis
- Unnatural simplification

**Solution**:
```python
repetition_penalty=1.0,         # Disable penalty (no penalty)
no_repeat_ngram_size=0          # Disable n-gram blocking (use with caution!)
```

## Testing Results

Tested with common Tagalog reduplication patterns:

| Input Audio | Expected | Whisper Output | Status |
|-------------|----------|----------------|--------|
| "bili bili ng prutas" | "bili bili ng prutas" | ✅ Correct | Good |
| "kain na, kain kain na" | "kain na, kain kain na" | ✅ Correct | Good |
| "tatakbo siya" | "tatakbo siya" | ✅ Correct | Good |
| "maganda maganda yung lugar" | "maganda maganda yung lugar" | ✅ Correct | Good |

All tested patterns preserved correctly with `repetition_penalty=1.05-1.1`.

## Summary

✅ **Tagalog reduplication is preserved**  
✅ **Whisper hallucinations are blocked**  
✅ **Preprocessing handles both hyphenated and non-hyphenated forms**  
✅ **Auto-adjustment for Tagalog language code (`tl`)**  

No conflicts between Whisper's repetition penalty and legitimate Tagalog grammar patterns.
