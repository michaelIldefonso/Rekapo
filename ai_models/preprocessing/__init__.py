"""
Taglish Preprocessing Module

Advanced preprocessing for Tagalog-English code-switched text.
Designed for improving machine translation quality.

Main Features:
- 47,695+ word Tagalog-English dictionary
- Tagalog morphology (affix stripping, reduplication)
- Multi-word phrase detection (50+ expressions)
- Text-speak normalization (60+ patterns)
- Proper noun preservation
- Language segmentation
- Context analysis

Usage:
    from ai_models.preprocessing import preprocess_taglish_text
    
    result = preprocess_taglish_text("kumain na ako kc gutom")
    print(result['annotated_text'])  # With translations
    print(result['context_score'])    # Mix analysis
"""

from .taglish import (
    # Main preprocessing function
    preprocess_taglish_text,
    
    # Component functions
    apply_phonetic_correction,
    strip_tagalog_affixes,
    detect_reduplication,
    detect_phrases,
    detect_language_segments,
    calculate_context_score,
    is_likely_proper_noun,
    
    # Data structures
    TAGLISH_DICTIONARY,
    TAGALOG_AFFIXES,
    COMMON_PHRASES,
    PHONETIC_PATTERNS,
)

__all__ = [
    'preprocess_taglish_text',
    'apply_phonetic_correction',
    'strip_tagalog_affixes',
    'detect_reduplication',
    'detect_phrases',
    'detect_language_segments',
    'calculate_context_score',
    'is_likely_proper_noun',
    'TAGLISH_DICTIONARY',
    'TAGALOG_AFFIXES',
    'COMMON_PHRASES',
    'PHONETIC_PATTERNS',
]
