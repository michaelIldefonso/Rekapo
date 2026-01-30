"""
Taglish Text Preprocessing Module

Provides advanced preprocessing for Taglish (Tagalog-English code-switched) text:
- Dictionary lookup for common Tagalog words
- Phonetic correction for text-speak and misspellings
- Language-aware tokenization
- Context scoring for code-switching analysis
"""

import re
from typing import List, Dict, Tuple
from collections import Counter


# Taglish dictionary: Common Tagalog words and their English translations
TAGLISH_DICTIONARY = {
    # Common verbs
    "kumain": "eat", "kain": "eat", "kinain": "ate",
    "uminom": "drink", "inom": "drink", "ininom": "drank",
    "pumunta": "go", "punta": "go", "napunta": "went",
    "umuwi": "go home", "uwi": "go home", "umuwi": "went home",
    "natulog": "slept", "tulog": "sleep", "matulog": "sleep",
    "gising": "wake up", "gumising": "woke up",
    "lakad": "walk", "lumakad": "walked",
    "takbo": "run", "tumakbo": "ran",
    "bili": "buy", "bumili": "bought", "nabili": "bought",
    "gawa": "do/make", "gumawa": "did/made", "ginawa": "did/made",
    "sabi": "said", "nagsabi": "said", "sinabi": "said",
    "kita": "see", "nakita": "saw", "makita": "see",
    "dinig": "hear", "narinig": "heard",
    "alam": "know", "nakaalam": "knew",
    "naman": "also/too", "din": "also/too", "rin": "also/too",
    "lang": "just/only", "lamang": "just/only",
    "pa": "still/yet/more",
    "na": "already/now",
    "nga": "indeed/really",
    
    # Common nouns
    "bahay": "house", "tahanan": "home",
    "pera": "money", "salapi": "money",
    "pagkain": "food", "kain": "food",
    "tubig": "water", "inumin": "drink",
    "oras": "time", "panahon": "time/weather",
    "araw": "day/sun", "buwan": "month/moon",
    "gabi": "night", "umaga": "morning",
    "tao": "person/people", "mga tao": "people",
    "trabaho": "work", "hanapbuhay": "work/livelihood",
    "kotse": "car", "sasakyan": "vehicle",
    "telepono": "phone", "cellphone": "cellphone",
    "libro": "book", "aklat": "book",
    
    # Common adjectives
    "maganda": "beautiful/nice", "ganda": "beauty/beautiful",
    "pangit": "ugly/bad",
    "mabuti": "good", "buti": "good",
    "masama": "bad",
    "malaki": "big", "laki": "size/big",
    "maliit": "small", "liit": "small",
    "mataas": "tall/high", "taas": "height",
    "mababa": "short/low", "baba": "low/chin",
    "mainit": "hot", "init": "heat",
    "malamig": "cold", "lamig": "cold",
    "mahal": "expensive/love", "minamahal": "loved",
    "mura": "cheap",
    
    # Common expressions
    "oo": "yes", "opo": "yes (formal)",
    "hindi": "no/not", "di": "no/not",
    "sige": "okay/go ahead", "sigue": "okay",
    "tara": "let's go", "tayo": "let's go/we",
    "salamat": "thank you", "thanks": "thank you",
    "sorry": "sorry", "pasensya": "sorry",
    "talaga": "really/truly", "totoo": "true/really",
    "kasi": "because", "dahil": "because",
    "pero": "but", "ngunit": "but",
    "tapos": "then/finished", "pagkatapos": "after/then",
    "kaya": "so/can", "kaya nga": "that's why",
    "baka": "might/maybe", "siguro": "maybe/probably",
    "gusto": "want/like", "gustong": "want to",
    "ayaw": "don't want", "ayoko": "I don't want",
    "pwede": "can/possible", "puwede": "can/possible",
    
    # Pronouns
    "ako": "I/me", "ko": "my/me",
    "ikaw": "you", "mo": "your/you",
    "siya": "he/she", "niya": "his/her",
    "tayo": "we (inclusive)", "natin": "our (inclusive)",
    "kami": "we (exclusive)", "namin": "our (exclusive)",
    "kayo": "you (plural)", "ninyo": "your (plural)",
    "sila": "they", "nila": "their",
    "ito": "this", "nito": "of this",
    "iyan": "that", "niyan": "of that",
    "iyon": "that (far)", "niyon": "of that",
    
    # Question words
    "ano": "what", "anong": "what",
    "sino": "who", "sinong": "who",
    "saan": "where", "nasaan": "where is",
    "kailan": "when", "kelan": "when",
    "paano": "how", "pano": "how",
    "bakit": "why",
    "ilan": "how many", "ilang": "how many",
    "magkano": "how much",
}

# Phonetic correction patterns for common Taglish misspellings
PHONETIC_PATTERNS = {
    # Common substitutions
    r'\bpwede\b': 'pwede',  # normalize
    r'\bpwedi\b': 'pwede',
    r'\bpwidi\b': 'pwede',
    r'\bkc\b': 'kasi',  # text speak
    r'\bkse\b': 'kasi',
    r'\bd2\b': 'dito',
    r'\bdi\b': 'hindi',
    r'\bdi2\b': 'dito',
    r'\bun\b': 'yun',
    r'\bng\b': 'nang',  # context-dependent
    r'\btlga\b': 'talaga',
    r'\btlaga\b': 'talaga',
    r'\btalga\b': 'talaga',
    r'\bsge\b': 'sige',
    r'\bsigi\b': 'sige',
    r'\bsigey\b': 'sige',
    r'\bgsto\b': 'gusto',
    r'\bgsto\b': 'gusto',
    r'\bkyo\b': 'kayo',
    r'\bkau\b': 'kayo',
    r'\bka\b': 'ikaw',  # context-dependent
    r'\bpra\b': 'para',
    r'\bpr\b': 'para',
    r'\bsn\b': 'sa',
    r'\bsna\b': 'sana',
    r'\bbkt\b': 'bakit',
    r'\bbkit\b': 'bakit',
    r'\bna\b': 'na',
    r'\blng\b': 'lang',
    r'\bdpt\b': 'dapat',
    r'\bdpat\b': 'dapat',
    r'\bynm\b': 'yung',
    r'\byn\b': 'yun',
    r'\btpos\b': 'tapos',
    r'\btps\b': 'tapos',
}


def apply_phonetic_correction(text: str) -> str:
    """
    Apply phonetic corrections for common Taglish text speak and misspellings.
    
    Args:
        text: Input text with potential misspellings
    
    Returns:
        Text with phonetic corrections applied
    """
    corrected = text.lower()
    for pattern, replacement in PHONETIC_PATTERNS.items():
        corrected = re.sub(pattern, replacement, corrected, flags=re.IGNORECASE)
    return corrected


def detect_language_segments(text: str) -> List[Tuple[str, str]]:
    """
    Perform language-aware tokenization to identify Tagalog vs English segments.
    
    Args:
        text: Input Taglish text
    
    Returns:
        List of tuples (segment, language) where language is 'tl' or 'en'
    """
    words = text.split()
    segments = []
    
    for word in words:
        # Remove punctuation for checking
        word_clean = re.sub(r'[^\w\s]', '', word.lower())
        
        # Check if word is in Tagalog dictionary
        if word_clean in TAGLISH_DICTIONARY:
            segments.append((word, 'tl'))
        # Check for Tagalog affixes/patterns
        elif any(word_clean.startswith(prefix) for prefix in ['mag', 'nag', 'pag', 'um', 'in', 'ka', 'ma']):
            if len(word_clean) > 3:
                segments.append((word, 'tl'))
            else:
                segments.append((word, 'en'))
        # Check for Tagalog suffixes
        elif any(word_clean.endswith(suffix) for suffix in ['an', 'in', 'han', 'hin']):
            segments.append((word, 'tl'))
        else:
            segments.append((word, 'en'))
    
    return segments


def calculate_context_score(text: str) -> Dict[str, any]:
    """
    Calculate context scores for the Taglish text to understand code-switching patterns.
    
    Args:
        text: Input Taglish text
    
    Returns:
        Dictionary with context metrics
    """
    segments = detect_language_segments(text)
    total_words = len(segments)
    
    if total_words == 0:
        return {
            "tagalog_ratio": 0.0,
            "english_ratio": 0.0,
            "switch_count": 0,
            "complexity": "simple",
            "dominant_language": "unknown"
        }
    
    tagalog_count = sum(1 for _, lang in segments if lang == 'tl')
    english_count = total_words - tagalog_count
    
    # Count language switches
    switch_count = 0
    for i in range(1, len(segments)):
        if segments[i][1] != segments[i-1][1]:
            switch_count += 1
    
    tagalog_ratio = tagalog_count / total_words
    english_ratio = english_count / total_words
    
    # Determine complexity based on switch frequency
    switch_ratio = switch_count / total_words if total_words > 1 else 0
    if switch_ratio > 0.3:
        complexity = "highly_mixed"
    elif switch_ratio > 0.15:
        complexity = "mixed"
    else:
        complexity = "simple"
    
    # Determine dominant language
    if tagalog_ratio > 0.6:
        dominant_language = "tagalog"
    elif english_ratio > 0.6:
        dominant_language = "english"
    else:
        dominant_language = "balanced"
    
    return {
        "tagalog_ratio": round(tagalog_ratio, 2),
        "english_ratio": round(english_ratio, 2),
        "switch_count": switch_count,
        "complexity": complexity,
        "dominant_language": dominant_language,
        "total_words": total_words
    }


def preprocess_taglish_text(text: str) -> Dict[str, any]:
    """
    Comprehensive preprocessing pipeline for Taglish text.
    Applies dictionary lookup, phonetic correction, language-aware tokenization,
    and context scoring.
    
    Args:
        text: Raw Taglish input text
    
    Returns:
        Dictionary with preprocessed text and metadata
    """
    # Step 1: Apply phonetic correction
    corrected_text = apply_phonetic_correction(text)
    
    # Step 2: Detect language segments
    segments = detect_language_segments(corrected_text)
    
    # Step 3: Apply dictionary translations for known terms
    enriched_tokens = []
    for word, lang in segments:
        word_clean = re.sub(r'[^\w\s]', '', word.lower())
        if lang == 'tl' and word_clean in TAGLISH_DICTIONARY:
            translation = TAGLISH_DICTIONARY[word_clean]
            enriched_tokens.append(f"{word}[{translation}]")
        else:
            enriched_tokens.append(word)
    
    # Step 4: Calculate context scores
    context_score = calculate_context_score(corrected_text)
    
    # Step 5: Create annotated text for better translation
    annotated_text = " ".join(enriched_tokens)
    
    return {
        "original_text": text,
        "corrected_text": corrected_text,
        "annotated_text": annotated_text,
        "segments": segments,
        "context_score": context_score
    }
