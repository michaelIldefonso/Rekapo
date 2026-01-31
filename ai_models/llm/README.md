# Taglish Preprocessing Module

An advanced preprocessing system for Taglish (Tagalog-English code-switched) text that prepares it for better translation quality with NLLB-200 or other translation models.

## Architecture

The module provides comprehensive text analysis and preparation for Taglish translation:

### **Enhanced Preprocessing Pipeline** (`preprocessing.py`)

- **47,000+ Word Dictionary**: Comprehensive Tagalog-English mappings with part-of-speech tags
- **Tagalog Morphology**: Affix stripping (prefixes, suffixes, circumfixes) to find root words
- **Reduplication Detection**: Handles full and partial CV-reduplication (bili-bili → bili, tatakbo → takbo)
- **Multi-word Phrase Detection**: 50+ common Tagalog phrases treated as units
- **Expanded Text-speak**: 60+ patterns for internet slang and abbreviations 
- **Proper Noun Preservation**: Keeps names, places, brands intact
- **Context Scoring**: Analyzes code-switching patterns and complexity

## Usage

### With NLLB Translation (Recommended - Lightweight)
```python
from ai_models.translator.inference import translate_text

# Preprocessing is automatically applied
result = translate_text(
    text="kumakain na ako kanina pa, kc gutom eh",
    source_lang="tgl_Latn",  # Tagalog
    target_lang="eng_Latn",  # English
    use_preprocessing=True    # Applies all enhancements
)
print(result["translated_text"])  # "I've been eating for a while because I was hungry"
print(result["preprocessing_info"])  # Context analysis
```

### Preprocessing Only (for analysis or custom pipelines)
```python
from ai_models.llm.preprocessing import preprocess_taglish_text

prep_result = preprocess_taglish_text("hindi ko alam kung kumakain na sila")
print(prep_result["corrected_text"])    # After phonetic corrections
print(prep_result["annotated_text"])    # "kung[if/when] kumakain[to eat] na[already] sila[they]"
print(prep_result["detected_phrases"])  # [("hindi ko alam", "I don't know")]
print(prep_result["context_score"])     # {"tagalog_ratio": 1.0, "complexity": "simple", ...}
```

### Testing Individual Components
```python
from ai_models.llm.preprocessing import (
   Enhanced Preprocessing Pipeline Flow

```
Input: "hindi ko alam kung kumakain na sila"
    ↓
1. Phonetic Correction (Text-speak)
   "kc" → "kasi", "cnxa" → "sensya", "tlga" → "talaga", etc.
    ↓
2. Phrase Detection (Multi-word expressions)
   "hindi ko alam" → [PHRASE: I don't know]
   "sige na" → [PHRASE: come on / alright]
    ↓
3. Reduplication Detection
   "bili-bili" → "bili" (full reduplication)
   "tatakbo" → "takbo" (CV-reduplication)
    ↓
4. Affix Stripping & Root Extraction
   "kumakain" → root: "kain" + affixes: ["um", "ka"]
   "naglalaro" → root: "laro" + affixes: ["nag", reduplication]
   "pagkain" → root: "kain" + affixes: ["pag"]
    ↓
5. Dictionary Annotation (47,695 words)
   "kumakain[verb to eat]" "na[adv already]" "sila[pron they]"
    ↓
6. Proper Noun Preservation
   "Si Juan" → keep "Juan" unchanged
   Brand names, place names preserved
    ↓
7. Language Segmentation
   [(word, 'tl'), (word, 'en'), (name, 'proper')]
    ↓
8. Context Analysis
   {
     "tagalog_ratio": 1.0,
     "english_ratio": 0.0,
     "switch_count": 0,
     "complexity": "simple",
     "dominant_language": "tagalog"
   }
    ↓
9. NLLB Translation (with enriched context)
   "I don't know if they are already eating"
```

## What's New - Major Improvements ✨

### 1. **Tagalog Morphology (Affix Handling)**
Strips prefixes, suffixes, and circumfixes to find root words:
- **Before**: "kumakain" not in dictionary → treated as unknown
- **After**: "kumakain" → root "kain"[eat] + affixes ["um", "ka"] → better translation

### 2. **Reduplication Detection** 
Handles Tagalog intensification patterns:
- **Hyphenated**: "bili-bili", "kain-kain" → base form "bili", "kain"
- **CV-reduplication**: "tatakbo", "kakain" → "takbo", "kain"

### 3. **Multi-word Phrase Detection**
Treats 50+ common phrases as single units:
- **Before**: "hindi" + "ko" + "alam" → three separate words
- **After**: "hindi ko alam" → [PHRASE: I don't know] → better context

### 4. **E
├── llm/
│   ├── __init__.py                    # Module interface
│   ├── preprocessing.py               # ⭐ Enhanced preprocessing pipeline
│   ├── llm.py                         # Legacy Qwen support (optional)
│   ├── tagalog_dictionary.json        # 47,695 word dictionary
│   └── README.md                      # This file
└── translator/
    └── inference.py                   # NLLB translation with auto-preprocessing
```

## Return Formats

### translate_text() (from translator/inference.py)
```python
{
    "translated_text": str,              # Final English translation
    "source_lang": str,                  # "tgl_Latn" (Tagalog)
    "target_lang": str,                  # "eng_Latn" (English)
    "preprocessing_info": {              # Only for Taglish→English
        "original_text": str,            # Before preprocessing
        "corrected_text": str,           # After phonetic correction
        "context_score": {
            "tagalog_ratio": float,      # 0.0 to 1.0
            "english_ratio": float,      # 0.0 to 1.0
            "switch_count": int,         # Number of language switches
            "complexity": str,           # "simple", "mixed", "highly_mixed"
            "dominant_language": str,    # "tagalog", "english", "balanced"
            "total_words": int
        }
    }
}
```

### preprocess_taglish_text() (standalone preprocessing)
```python
{
    "original_text": str,                 # Input text
    "corrected_text": str,                # After phonetic correction
    "annotated_text": str,                # With [translations] and [PHRASE:...] markers
    "segments": [(word, lang)],           # Language-tagged tokens ('tl', 'en', 'proper')
    "detected_phrases": [(phrase, translation), ...],  # Multi-word phrases found
    "context_score": {                    # Same structure as above
        "tagalog_ratio": float,
        "english_ratio": float,
        "switch_count": int,
        "complexity": str,
        "dominant_language": str,
        "total_words": int
    }
}── preprocessing.py      # Text preprocessing functions
├── llm.py               # Qwen model & translation
└── README.md            # This file
```

## Return Format
 Expanding the Dictionary

**Current Dictionary**: 47,695 Tagalog words with English translations and part-of-speech tags

### Adding More Words

**Option 1: Edit JSON file directly**
```json
{
  "magluto": "verb to cook",
  "palengke": "noun market wet market",
  "kompyuter": "noun computer"
}
```

**Option 2: Download additional dictionaries**
- **[Wiktionary Tagalog Dictionaries](https://github.com/Vuizur/Wiktionary-Dictionaries)** - TSV format (already used)
- **[matthewdeanmartin/tagalog_enumerations](https://github.com/matthewdeanmartin/tagalog_enumerations)** - Python package
- **Community projects** - Search GitHub for "tagalog-english-dictionary"

### Fallback Behavior

If `tagalog_dictionary.json` is missing or corrupted, the module automatically falls back to a minimal 30-word dictionary with essential Tagalog words for basic functionality.

## Adding Text-Speak Patterns

Expand `PHONETIC_PATTERNS` in [preprocessing.py](preprocessing.py):

```python
PHONETIC_PATTERNS = {
    # Add your patterns here
    r'\byawa\b': 'yawa',          # New slang
    r'\bkeme\b': 'kikay',         # New abbreviation
    # Use raw strings (r'...') for regex patterns
    # Use \b for word boundaries
}
```

## Adding Multi-word Phrases

Expand `COMMON_PHRASES` in [preprocessing.py](preprocessing.py):

```python
COMMON_PHRASES = {
    "wala kang magagawa": "you can't do anything about it",
    "hindi pwede": "not allowed / can't",
    "ano na": "what's up / what now",
    # Add phrases as key: translation pairs
}
```

## Testing Your Improvements

Run the comprehensive test suite:

```bash
python tests/test_enhanced_preprocessing.py
```

This tests:
- ✓ Affix stripping
- ✓ Reduplication detection  
- ✓ Phrase detection
- ✓ Text-speak correction
- ✓ Full preprocessing pipeline
- ✓ Before/after comparisons text="kumain ako",
    model_name="Qwen/Qwen2.5-7B-Instruct",  # Change model here
    device="cuda",                           # or "cpu"
    max_new_tokens=512
)
```

## Tagalog Dictionary

The module uses a Tagalog-English dictionary loaded from `tagalog_dictionary.json` (automatically loads at module initialization).

### Expanding the Dictionary

**Option 1: Edit the JSON file directly**
```json
{
  "magluto": "cook",
  "palengke": "market",
  "kompyuter": "computer"
}
```

**Option 2: Replace with a comprehensive dictionary**

Download larger dictionaries from:
- **[matthewdeanmartin/tagalog_enumerations](https://github.com/matthewdeanmartin/tagalog_enumerations)** - Python package with extensive words
- **[Wiktionary Dumps](https://dumps.wikimedia.org/tlwiktionary/)** - Extract Tagalog entries
- **Community dictionary projects** - Search GitHub for "tagalog-english-dictionary"

Just replace `tagalog_dictionary.json` with your downloaded dictionary (must be in `key: value` format).

**Recommended size:** 10,000-50,000 words for comprehensive coverage

### Fallback Behavior

If `tagalog_dictionary.json` is missing or corrupted, the module automatically falls back to a minimal 30-word dictionary for basic functionality.

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
