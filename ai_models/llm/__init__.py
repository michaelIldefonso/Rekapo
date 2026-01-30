"""
Taglish-to-English Translation Module

This module provides translation capabilities optimized for Filipino code-switched text.

Components:
- preprocessing.py: Text preprocessing pipeline (dictionary, phonetics, context analysis)
- llm.py: Qwen-based translation model interface

Usage:
    from ai_models.llm.llm import translate_taglish_to_english
    from ai_models.llm.preprocessing import preprocess_taglish_text
"""

# Import preprocessing (no heavy dependencies)
from .preprocessing import (
    preprocess_taglish_text,
    apply_phonetic_correction,
    detect_language_segments,
    calculate_context_score,
    TAGLISH_DICTIONARY,
    PHONETIC_PATTERNS
)

# Lazy import for LLM functions (require transformers, torch, etc.)
def __getattr__(name):
    if name in ['translate_taglish_to_english', 'translate_taglish_batch']:
        from .llm import translate_taglish_to_english, translate_taglish_batch
        globals()[name] = locals()[name]
        return locals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    # Main translation functions (lazy loaded)
    'translate_taglish_to_english',
    'translate_taglish_batch',
    
    # Preprocessing functions (always available)
    'preprocess_taglish_text',
    'apply_phonetic_correction',
    'detect_language_segments',
    'calculate_context_score',
    
    # Data structures
    'TAGLISH_DICTIONARY',
    'PHONETIC_PATTERNS',
]
