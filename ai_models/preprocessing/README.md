# Taglish Preprocessing Module

Advanced text preprocessing for Tagalog-English (Taglish) code-switched text. Designed to improve machine translation quality by providing linguistic context and corrections.

## Features

### 📚 Comprehensive Dictionary (47,695 words)
- Tagalog-English translations with part-of-speech tags
- Loaded automatically from `tagalog_dictionary.json`
- Fallback to 30 essential words if dictionary unavailable

### 🔤 Tagalog Morphology
- **Affix Stripping**: Removes 15+ prefixes, 5 suffixes, 6 circumfixes
- **Reduplication Detection**: Handles full (bili-bili) and CV-reduplication (tatakbo→takbo)
- Finds root words for better dictionary lookup

### 💬 Multi-word Phrase Detection (50+ phrases)
Treats common expressions as single units:
- "hindi ko alam" → "I don't know"
- "sige na" → "come on"
- "grabe naman" → "that's too much"

### ⌨️ Text-speak Normalization (60+ patterns)
Corrects internet slang and abbreviations:
- `kc` → kasi, `cnxa` → sensya
- `nkklk` → nakakaloka (overwhelming)
- `char` → just kidding

### 🏷️ Proper Noun Preservation
Detects and preserves:
- Names: "Si Juan" → keeps "Juan"
- Places: "Manila City"
- Brands: "Jollibee"

### 📊 Analysis & Segmentation
- Language-aware tokenization (Tagalog vs English)
- Code-switching analysis (mix ratios, complexity)
- Context scoring

## Installation

No additional dependencies required (uses standard library only).

## Usage

### Basic Preprocessing

```python
from ai_models.preprocessing import preprocess_taglish_text

result = preprocess_taglish_text("hindi ko alam kung kumakain na sila")

# Access results
print(result['corrected_text'])    # After phonetic corrections
print(result['annotated_text'])    # With [translations]
print(result['detected_phrases'])  # Multi-word expressions found
print(result['context_score'])     # Language mix analysis
```

### Output Example

```python
{
    "original_text": "hindi ko alam kung kumakain na sila",
    "corrected_text": "hindi ko alam kung kumakain na sila",
    "annotated_text": "kung[if/when] kumakain[verb:to eat] na[already] sila[they]",
    "segments": [("kung", "tl"), ("kumakain", "tl"), ...],
    "detected_phrases": [("hindi ko alam", "I don't know")],
    "context_score": {
        "tagalog_ratio": 1.0,
        "english_ratio": 0.0,
        "switch_count": 0,
        "complexity": "simple",
        "dominant_language": "tagalog",
        "total_words": 6
    }
}
```

### Individual Functions

```python
from ai_models.preprocessing import (
    apply_phonetic_correction,
    strip_tagalog_affixes,
    detect_reduplication,
    detect_phrases
)

# Text-speak correction
corrected = apply_phonetic_correction("kc gutom na ako")  
# Output: "kasi gutom na ako"

# Affix stripping
root, affixes = strip_tagalog_affixes("kumakain")
# Output: ('kain', ['um', 'ka'])

# Reduplication detection
base, is_redup = detect_reduplication("bili-bili")
# Output: ('bili', True)

# Phrase detection
phrases = detect_phrases("hindi ko alam kung pwede")
# Output: [("hindi ko alam", "I don't know", 0, 14)]
```

### With NLLB Translation

```python
from ai_models.translator.inference import translate_text

# Preprocessing is applied automatically
result = translate_text(
    text="kumain na ako kc gutom eh",
    source_lang="tgl_Latn",
    target_lang="eng_Latn",
    use_preprocessing=True  # Default: applies all enhancements
)

print(result['translated_text'])      # Clean English output
print(result['preprocessing_info'])   # Shows what was corrected
```

## Files

```
ai_models/preprocessing/
├── __init__.py                 # Module exports
├── taglish.py                  # Main preprocessing logic
├── tagalog_dictionary.json     # 47,695 word dictionary
└── README.md                   # This file
```

## Extending

### Add Text-speak Patterns

Edit `PHONETIC_PATTERNS` in [taglish.py](taglish.py):

```python
PHONETIC_PATTERNS = {
    r'\byawa\b': 'yawa',          # New slang
    r'\bkeme\b': 'kikay',         # New abbreviation
    # ...
}
```

### Add Multi-word Phrases

Edit `COMMON_PHRASES` in [taglish.py](taglish.py):

```python
COMMON_PHRASES = {
    "wala kang magagawa": "you can't do anything about it",
    "hindi pwede": "not allowed",
    # ...
}
```

### Expand Dictionary

Edit [tagalog_dictionary.json](tagalog_dictionary.json):

```json
{
  "magluto": "verb to cook",
  "palengke": "noun market",
  "kompyuter": "noun computer"
}
```

## Performance

- **Dictionary Loading**: ~0.5s (cached after first import)
- **Preprocessing**: ~1-5ms per sentence
- **Memory**: ~15MB (dictionary in memory)

## Migration from `ai_models.llm.preprocessing`

Old imports:
```python
from ai_models.llm.preprocessing import preprocess_taglish_text
```

New imports:
```python
from ai_models.preprocessing import preprocess_taglish_text
```

All function signatures remain the same.

## Testing

Run comprehensive tests:

```bash
python tests/test_enhanced_preprocessing.py
```

## License

Part of the Rekapo project.
