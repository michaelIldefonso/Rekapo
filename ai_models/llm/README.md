# Taglish Translation Module

A sophisticated Taglish (Tagalog-English code-switched) to English translation system using Qwen 2.5-7B with advanced preprocessing.

## Architecture

The module is separated into two main components for better maintainability:

### 1. **Preprocessing Pipeline** (`preprocessing.py`)
Handles all text analysis and preparation before translation:

- **Dictionary Lookup**: 150+ Tagalog-English word mappings
- **Phonetic Correction**: Fixes text-speak and common misspellings (30+ patterns)
- **Language-Aware Tokenization**: Identifies Tagalog vs English segments
- **Context Scoring**: Analyzes code-switching patterns and complexity

### 2. **LLM Translation** (`llm.py`)
Manages the Qwen model and translation process:

- **Model Management**: Loads and caches Qwen 2.5-7B (4-bit quantized ~8GB)
- **Translation**: Uses preprocessing results to guide translation
- **Batch Processing**: Handles multiple texts efficiently

## Usage

### Basic Translation
```python
from ai_models.llm.llm import translate_taglish_to_english

result = translate_taglish_to_english("kumain na ako")
print(result["translated_text"])  # "I already ate"
print(result["preprocessing_info"])  # Context analysis
```

### Preprocessing Only (without translation)
```python
from ai_models.llm.preprocessing import preprocess_taglish_text

prep_result = preprocess_taglish_text("kc kumain na ako")
print(prep_result["corrected_text"])  # "kasi kumain na ako"
print(prep_result["annotated_text"])  # "kasi[because] kumain[eat] na[already] ako[I]"
print(prep_result["context_score"])  # Language mix analysis
```

### Batch Translation
```python
from ai_models.llm.llm import translate_taglish_batch

texts = ["kumain ako", "pupunta na ko", "maganda weather"]
results = translate_taglish_batch(texts)
for r in results:
    print(f"{r['translated_text']}")
```

## Preprocessing Pipeline Flow

```
Input: "kc kumain na ako"
    ↓
1. Phonetic Correction
   "kc kumain na ako" → "kasi kumain na ako"
    ↓
2. Language Segmentation
   [("kasi", "tl"), ("kumain", "tl"), ("na", "tl"), ("ako", "tl")]
    ↓
3. Dictionary Annotation
   "kasi[because] kumain[eat] na[already] ako[I]"
    ↓
4. Context Analysis
   {
     "tagalog_ratio": 1.0,
     "english_ratio": 0.0,
     "switch_count": 0,
     "complexity": "simple",
     "dominant_language": "tagalog"
   }
    ↓
5. LLM Translation (with all context)
   "because I already ate"
```

## Benefits of Separation

1. **Modularity**: Use preprocessing independently or with different models
2. **Testability**: Test preprocessing and translation logic separately
3. **Maintainability**: Update dictionaries/patterns without touching model code
4. **Reusability**: Apply preprocessing to other NLP tasks
5. **Performance**: Can cache preprocessing results

## Files Structure

```
ai_models/llm/
├── __init__.py           # Module interface
├── preprocessing.py      # Text preprocessing functions
├── llm.py               # Qwen model & translation
└── README.md            # This file
```

## Return Format

### translate_taglish_to_english()
```python
{
    "translated_text": str,           # Final English translation
    "model_used": str,                # Model name used
    "preprocessing_info": {
        "corrected_text": str,        # After phonetic correction
        "context_score": {
            "tagalog_ratio": float,   # 0.0 to 1.0
            "english_ratio": float,   # 0.0 to 1.0
            "switch_count": int,      # Number of language switches
            "complexity": str,        # "simple", "mixed", "highly_mixed"
            "dominant_language": str, # "tagalog", "english", "balanced"
            "total_words": int
        }
    }
}
```

### preprocess_taglish_text()
```python
{
    "original_text": str,           # Input text
    "corrected_text": str,          # After phonetic correction
    "annotated_text": str,          # With [translations]
    "segments": [(word, lang)],     # Language-tagged tokens
    "context_score": {...}          # Same as above
}
```

## Configuration

### Model Selection
```python
# Default: Qwen 2.5-7B Instruct (8GB with 4-bit quantization)
result = translate_taglish_to_english(
    text="kumain ako",
    model_name="Qwen/Qwen2.5-7B-Instruct",  # Change model here
    device="cuda",                           # or "cpu"
    max_new_tokens=512
)
```

## Extending the Dictionary

Add new Tagalog words to `TAGLISH_DICTIONARY` in `preprocessing.py`:

```python
TAGLISH_DICTIONARY = {
    # Existing entries...
    "magluto": "cook",           # Add new verb
    "palengke": "market",        # Add new noun
    # ...
}
```

## Extending Phonetic Patterns

Add text-speak corrections to `PHONETIC_PATTERNS` in `preprocessing.py`:

```python
PHONETIC_PATTERNS = {
    # Existing patterns...
    r'\bpls\b': 'please',        # Add new pattern
    r'\bd\b': 'yung',            # Add abbreviation
    # ...
}
```
