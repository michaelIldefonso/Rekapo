"""
Taglish Text Preprocessing Module

Provides advanced preprocessing for Taglish (Tagalog-English code-switched) text:
- Dictionary lookup for 47,695+ Tagalog words with English translations
- Tagalog morphology (affix stripping, reduplication detection)
- Multi-word phrase detection (50+ common expressions)
- Phonetic correction for text-speak (60+ patterns)
- Proper noun preservation
- Language-aware tokenization
- Context scoring for code-switching analysis

This module is used by the translation pipeline (NLLB) to improve
Taglish-to-English translation quality.
"""

import re
import json
import os
from typing import List, Dict, Tuple
from collections import Counter


def load_tagalog_dictionary() -> Dict[str, str]:
    """
    Load Tagalog-English dictionary from JSON file.
    Falls back to a minimal curated dictionary if file not found.
    
    Returns:
        Dictionary mapping Tagalog words to English translations
    """
    # Try to load from JSON file
    dict_path = os.path.join(os.path.dirname(__file__), 'tagalog_dictionary.json')
    
    try:
        with open(dict_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Filter out metadata fields starting with underscore
            dictionary = {k: v for k, v in data.items() if not k.startswith('_')}
            print(f"Loaded {len(dictionary)} Tagalog words from dictionary file")
            return dictionary
    except FileNotFoundError:
        print(f"Dictionary file not found at {dict_path}, using minimal fallback")
        return _get_fallback_dictionary()
    except json.JSONDecodeError as e:
        print(f"Error parsing dictionary JSON: {e}, using minimal fallback")
        return _get_fallback_dictionary()


def _get_fallback_dictionary() -> Dict[str, str]:
    """
    Minimal curated dictionary as fallback.
    Contains most common Taglish words for basic functionality.
    """
    return {
        # Essential words
        "ako": "I/me", "ko": "my/me",
        "ikaw": "you", "mo": "your/you",
        "siya": "he/she", "niya": "his/her",
        "tayo": "we", "kami": "we",
        "kayo": "you (plural)", "sila": "they",
        "oo": "yes", "hindi": "no/not", "di": "no/not",
        "ano": "what", "sino": "who", "saan": "where",
        "kailan": "when", "paano": "how", "bakit": "why",
        "kain": "eat", "inom": "drink", "tulog": "sleep",
        "gusto": "want/like", "ayaw": "don't want",
        "pwede": "can/possible", "puwede": "can/possible",
        "salamat": "thank you", "sorry": "sorry",
        "naman": "also/too", "lang": "just/only", "pa": "still/yet",
        "na": "already/now", "kasi": "because", "pero": "but",
        "sige": "okay", "tara": "let's go", "talaga": "really",
    }


# Load the dictionary at module initialization
TAGLISH_DICTIONARY = load_tagalog_dictionary()

# Tagalog morphology: affixes for root word extraction
TAGALOG_AFFIXES = {
    'prefixes': ['nag', 'mag', 'naka', 'maka', 'mapag', 'pag', 'pa', 'um', 'in', 'ma', 'ka', 'nang', 'napag', 'ipag', 'ipinag'],
    'suffixes': ['an', 'in', 'han', 'hin', 'ng'],
    'circumfixes': [('nag', 'an'), ('mag', 'an'), ('ka', 'an'), ('pag', 'an'), ('pinag', 'an'), ('pina', 'an')]
}

# Common multi-word Tagalog phrases (check these before word-by-word translation)
COMMON_PHRASES = {
    "hindi ko alam": "I don't know",
    "ewan ko": "I don't know",
    "bahala na": "come what may",
    "ano ba": "what the heck",
    "sige na": "come on / alright",
    "grabe naman": "that's too much",
    "wala akong pake": "I don't care",
    "pakiusap lang": "please",
    "ang ganda": "how beautiful",
    "ang sarap": "so delicious",
    "kumusta ka": "how are you",
    "kumusta na": "how have you been",
    "ingat ka": "take care",
    "sana all": "I wish everyone had that",
    "syempre naman": "of course",
    "oo nga": "yeah right / exactly",
    "talaga naman": "really now",
    "wala na": "it's gone / nothing left",
    "meron ba": "is there",
    "ayaw ko na": "I don't want anymore",
    "tama na": "that's enough",
    "sabi ko": "I said",
    "sabi niya": "he/she said",
    "alam mo": "you know",
    "hindi naman": "not really",
    "di ba": "right?",
    "ganun ba": "is that so",
    "parang ganun": "something like that",
    "ano ba yan": "what is that",
    "hay nako": "oh my",
    "naku po": "oh my goodness",
    "grabe ka": "you're too much",
    "sayang naman": "what a waste",
    "sige lang": "it's okay / go ahead",
    "pwede na": "that works / good enough",
    "okay lang": "it's fine",
    "walang problema": "no problem",
    "salamat po": "thank you (respectful)",
    "pasensya na": "sorry / excuse me",
    "sandali lang": "just a moment",
    "tara na": "let's go",
    "halika dito": "come here",
    "umuwi ka na": "go home now",
    "kain na": "let's eat / time to eat",
    "busog na ako": "I'm full",
    "gutom na ako": "I'm hungry",
    "antok na ako": "I'm sleepy",
    "pagod na ako": "I'm tired",
}

# Expanded phonetic correction patterns for common Taglish misspellings and text-speak
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
    # Modern Filipino internet slang
    r'\bnkklk\b': 'nakakaloka',  # crazy/overwhelming
    r'\bcnxa\b': 'sensya',  # sorry
    r'\bcnsya\b': 'sensya',
    r'\bawit\b': 'awit',  # disappointment expression
    r'\bpota\b': 'puta',  # explicit (clean up if needed)
    r'\bpre\b': 'pare',  # friend/buddy
    r'\bbesh\b': 'best friend',
    r'\bbes\b': 'best friend',
    r'\bmamsir\b': 'maam or sir',
    r'\bnaks\b': 'nice',  # expression of admiration
    r'\bchz\b': 'cheese',  # just kidding
    r'\bchar\b': 'charot',  # just kidding
    r'\bcharot\b': 'just kidding',
    r'\bchour\b': 'just kidding',
    r'\bluh\b': 'lo',  # expression of disbelief
    r'\bnaks\b': 'wow nice',
    r'\bkeri\b': 'carry on / can handle',
    r'\bwildt\b': 'wild',  # crazy/intense
    r'\bgg\b': 'good game',
    r'\bomg\b': 'oh my god',
    r'\bomfg\b': 'oh my god',
    r'\bwfh\b': 'work from home',
    r'\bftw\b': 'for the win',
    r'\basf\b': 'as fuck',  # intensity marker
    r'\basfff\b': 'as fuck',
    r'\bjowa\b': 'partner / boyfriend / girlfriend',
    r'\btorpe\b': 'shy / unable to express feelings',
    r'\btampo\b': 'sulking',
    r'\bgipit\b': 'desperate / in need',
    r'\blupet\b': 'loophole / shortcut',
}


def strip_tagalog_affixes(word: str) -> tuple[str, list[str]]:
    """
    Strip Tagalog affixes to find root word for better dictionary lookup.
    Returns root word and list of removed affixes.
    
    Args:
        word: Tagalog word potentially with affixes
    
    Returns:
        Tuple of (root_word, list_of_removed_affixes)
    
    Examples:
        'kumakain' -> ('kain', ['um', 'reduplication'])
        'naglalaro' -> ('laro', ['nag', 'reduplication'])
        'pagkain' -> ('kain', ['pag'])
    """
    word_lower = word.lower()
    removed_affixes = []
    
    # Check for circumfixes first (prefix + suffix combo)
    for prefix, suffix in TAGALOG_AFFIXES['circumfixes']:
        if word_lower.startswith(prefix) and word_lower.endswith(suffix):
            root = word_lower[len(prefix):-len(suffix)]
            if len(root) >= 2:  # Valid root
                removed_affixes.extend([prefix, suffix])
                return root, removed_affixes
    
    # Check for prefixes
    for prefix in sorted(TAGALOG_AFFIXES['prefixes'], key=len, reverse=True):
        if word_lower.startswith(prefix) and len(word_lower) > len(prefix) + 1:
            root = word_lower[len(prefix):]
            removed_affixes.append(prefix)
            word_lower = root
            break
    
    # Check for suffixes
    for suffix in TAGALOG_AFFIXES['suffixes']:
        if word_lower.endswith(suffix) and len(word_lower) > len(suffix) + 1:
            root = word_lower[:-len(suffix)]
            removed_affixes.append(suffix)
            word_lower = root
            break
    
    return word_lower, removed_affixes


def detect_reduplication(word: str) -> tuple[str, bool]:
    """
    Detect and handle Tagalog reduplication patterns.
    Reduplication is used for intensity, frequency, or plurality.
    
    Args:
        word: Potentially reduplicated word
    
    Returns:
        Tuple of (base_word, is_reduplicated)
    
    Examples:
        'bili-bili' -> ('bili', True)
        'kain-kain' -> ('kain', True)
        'takbo' -> ('takbo', False)
        'tatakbo' -> ('takbo', True)  # CV-reduplication
    """
    word_lower = word.lower()
    
    # Full reduplication with hyphen: 'kain-kain' -> 'kain'
    if '-' in word_lower:
        parts = word_lower.split('-')
        if len(parts) == 2 and parts[0] == parts[1]:
            return parts[0], True
    
    # Partial CV-reduplication (consonant-vowel): 'tatakbo' -> 'takbo'
    # Common pattern: first syllable repeats
    if len(word_lower) >= 4:
        # Check if first 2 chars repeat: tatakbo (ta-takbo)
        if word_lower[:2] == word_lower[2:4]:
            return word_lower[2:], True
    
    return word_lower, False


def detect_phrases(text: str) -> list[tuple[str, str, int, int]]:
    """
    Detect common multi-word phrases in text.
    Returns list of (phrase, translation, start_pos, end_pos).
    
    Args:
        text: Input text
    
    Returns:
        List of detected phrases with positions
    """
    text_lower = text.lower()
    detected = []
    
    # Sort phrases by length (longest first) to match longer phrases first
    sorted_phrases = sorted(COMMON_PHRASES.items(), key=lambda x: len(x[0]), reverse=True)
    
    for phrase, translation in sorted_phrases:
        start = 0
        while True:
            pos = text_lower.find(phrase, start)
            if pos == -1:
                break
            # Check word boundaries
            if (pos == 0 or not text_lower[pos-1].isalnum()) and \
               (pos + len(phrase) >= len(text_lower) or not text_lower[pos + len(phrase)].isalnum()):
                detected.append((phrase, translation, pos, pos + len(phrase)))
            start = pos + 1
    
    # Remove overlapping phrases (keep first/longest match)
    detected.sort(key=lambda x: x[2])  # Sort by start position
    filtered = []
    last_end = -1
    for item in detected:
        if item[2] >= last_end:  # No overlap
            filtered.append(item)
            last_end = item[3]
    
    return filtered


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


def is_likely_proper_noun(word: str, context_words: list[str]) -> bool:
    """
    Heuristic to detect proper nouns (names, places, brands).
    Preserves these to avoid mistranslation.
    
    Args:
        word: Word to check
        context_words: Surrounding words for context
    
    Returns:
        True if likely a proper noun
    """
    # Check if word starts with capital letter (and not at sentence start)
    if not word or not word[0].isupper():
        return False
    
    # Common Filipino name prefixes/patterns
    name_indicators = ['si', 'ni', 'kay', 'kina']
    if any(indicator in [w.lower() for w in context_words[-2:]] for indicator in name_indicators):
        return True
    
    # Check if all caps (likely acronym or brand)
    if word.isupper() and len(word) > 1:
        return True
    
    # Common place name suffixes in Philippines
    place_suffixes = ['City', 'Province', 'Street', 'Avenue', 'Road']
    if any(word.endswith(suffix) for suffix in place_suffixes):
        return True
    
    return False


def detect_language_segments(text: str) -> List[Tuple[str, str]]:
    """
    Perform language-aware tokenization to identify Tagalog vs English segments.
    Now includes: affix stripping, reduplication detection, phrase detection,
    and proper noun preservation.
    
    Args:
        text: Input Taglish text
    
    Returns:
        List of tuples (segment, language) where language is 'tl', 'en', or 'proper'
    """
    words = text.split()
    segments = []
    
    # First pass: detect phrases
    phrases = detect_phrases(text)
    phrase_positions = set()
    for phrase, translation, start, end in phrases:
        phrase_positions.update(range(start, end))
    
    char_pos = 0
    prev_words = []
    
    for word in words:
        # Skip if part of a detected phrase
        word_start = text.find(word, char_pos)
        word_end = word_start + len(word)
        if any(pos in phrase_positions for pos in range(word_start, word_end)):
            char_pos = word_end
            continue
        
        # Remove punctuation for checking
        word_clean = re.sub(r'[^\w\s]', '', word.lower())
        
        if not word_clean:
            segments.append((word, 'en'))
            char_pos = word_end
            continue
        
        # Check if proper noun
        if is_likely_proper_noun(word, prev_words):
            segments.append((word, 'proper'))
            prev_words.append(word)
            char_pos = word_end
            continue
        
        # Check for reduplication
        base_word, is_reduplicated = detect_reduplication(word_clean)
        if is_reduplicated:
            word_clean = base_word
        
        # Try direct dictionary lookup
        if word_clean in TAGLISH_DICTIONARY:
            segments.append((word, 'tl'))
        else:
            # Try stripping affixes and lookup root
            root, affixes = strip_tagalog_affixes(word_clean)
            if root in TAGLISH_DICTIONARY and affixes:
                segments.append((word, 'tl'))
            # Check for Tagalog affixes/patterns
            elif any(word_clean.startswith(prefix) for prefix in TAGALOG_AFFIXES['prefixes'][:8]):
                if len(word_clean) > 3:
                    segments.append((word, 'tl'))
                else:
                    segments.append((word, 'en'))
            # Check for Tagalog suffixes
            elif any(word_clean.endswith(suffix) for suffix in TAGALOG_AFFIXES['suffixes']):
                segments.append((word, 'tl'))
            else:
                segments.append((word, 'en'))
        
        prev_words.append(word)
        char_pos = word_end
    
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
    
    # Step 3: Process detected phrases
    phrases = detect_phrases(corrected_text)
    phrase_map = {phrase: translation for phrase, translation, _, _ in phrases}
    
    # Step 4: Apply dictionary translations for known terms
    enriched_tokens = []
    for word, lang in segments:
        word_clean = re.sub(r'[^\w\s]', '', word.lower())
        
        # Preserve proper nouns
        if lang == 'proper':
            enriched_tokens.append(word)
        # Check if part of a common phrase
        elif any(word_clean in phrase for phrase in phrase_map.keys()):
            # Will be handled by phrase replacement
            enriched_tokens.append(word)
        # Tagalog word - try dictionary lookup with affix stripping
        elif lang == 'tl':
            # Try direct lookup first
            if word_clean in TAGLISH_DICTIONARY:
                translation = TAGLISH_DICTIONARY[word_clean]
                enriched_tokens.append(f"{word}[{translation}]")
            else:
                # Try with reduplication handling
                base_word, is_reduplicated = detect_reduplication(word_clean)
                if is_reduplicated and base_word in TAGLISH_DICTIONARY:
                    translation = TAGLISH_DICTIONARY[base_word]
                    enriched_tokens.append(f"{word}[repeated:{translation}]")
                else:
                    # Try affix stripping
                    root, affixes = strip_tagalog_affixes(word_clean)
                    if root in TAGLISH_DICTIONARY:
                        translation = TAGLISH_DICTIONARY[root]
                        affix_str = '+'.join(affixes)
                        enriched_tokens.append(f"{word}[{affix_str}+{translation}]")
                    else:
                        enriched_tokens.append(word)
        else:
            enriched_tokens.append(word)
    
    # Step 5: Replace detected phrases with translations
    annotated_text = " ".join(enriched_tokens)
    for phrase, translation in phrase_map.items():
        # Replace phrase with translation notation
        annotated_text = re.sub(
            r'\b' + re.escape(phrase) + r'\b',
            f"[PHRASE:{translation}]",
            annotated_text,
            flags=re.IGNORECASE
        )
    
    # Step 6: Calculate context scores
    context_score = calculate_context_score(corrected_text)
    
    return {
        "original_text": text,
        "corrected_text": corrected_text,
        "annotated_text": annotated_text,
        "segments": segments,
        "detected_phrases": list(phrase_map.items()),
        "context_score": context_score
    }
