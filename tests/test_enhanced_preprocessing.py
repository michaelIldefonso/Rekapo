"""
Test Enhanced Preprocessing Pipeline
Tests all new improvements: affix handling, reduplication, phrases, text-speak, etc.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_models.preprocessing import (
    preprocess_taglish_text,
    strip_tagalog_affixes,
    detect_reduplication,
    detect_phrases,
    apply_phonetic_correction
)

def test_affix_stripping():
    """Test Tagalog morphology - affix removal"""
    print("\n=== Testing Affix Stripping ===")
    
    test_words = [
        "kumakain",  # um + reduplication + kain
        "naglalaro",  # nag + reduplication + laro
        "maganda",    # ma + ganda
        "pagkain",    # pag + kain
        "kaibigan",   # ka + ibigan
        "nagtrabaho", # nag + trabaho
    ]
    
    for word in test_words:
        root, affixes = strip_tagalog_affixes(word)
        print(f"{word:15} -> root: '{root}', affixes: {affixes}")

def test_reduplication():
    """Test reduplication detection"""
    print("\n=== Testing Reduplication Detection ===")
    
    test_words = [
        "bili-bili",
        "kain-kain",
        "takbo-takbo",
        "tatakbo",
        "lalaro",
        "kakain",
    ]
    
    for word in test_words:
        base, is_redup = detect_reduplication(word)
        status = "✓ REDUPLICATED" if is_redup else "✗ not reduplicated"
        print(f"{word:15} -> '{base}' {status}")

def test_phrase_detection():
    """Test multi-word phrase detection"""
    print("\n=== Testing Phrase Detection ===")
    
    test_texts = [
        "hindi ko alam kung pwede ako pumunta",
        "sige na please, gusto ko talaga yan",
        "grabe naman, ang sarap ng pagkain",
        "kumusta ka na? ingat ka",
    ]
    
    for text in test_texts:
        phrases = detect_phrases(text)
        print(f"\nText: '{text}'")
        if phrases:
            for phrase, translation, start, end in phrases:
                print(f"  Found: '{phrase}' → '{translation}'")
        else:
            print("  No phrases detected")

def test_phonetic_correction():
    """Test text-speak correction"""
    print("\n=== Testing Text-Speak Correction ===")
    
    test_texts = [
        "kc gutom na ako eh",
        "d2 na ako, cnxa late",
        "tlga naman, awit",
        "sge na pls char lang",
        "nkklk grabe ka besh",
    ]
    
    for text in test_texts:
        corrected = apply_phonetic_correction(text)
        if text != corrected:
            print(f"'{text}' → '{corrected}'")
        else:
            print(f"'{text}' (no changes)")

def test_full_pipeline():
    """Test complete preprocessing pipeline"""
    print("\n=== Testing Full Preprocessing Pipeline ===")
    
    test_texts = [
        "Kumakain na ako kanina, busog pa ko",
        "hindi ko alam kung pwede ako pumunta kc busy",
        "grabe naman tlga si Juan, nkklk",
        "sge na pls, gusto ko talaga yan char",
        "naglalaro-laro lang sila sa bahay",
    ]
    
    for text in test_texts:
        print(f"\n{'='*60}")
        print(f"Original: {text}")
        print(f"{'='*60}")
        
        result = preprocess_taglish_text(text)
        
        print(f"Corrected: {result['corrected_text']}")
        print(f"Annotated: {result['annotated_text']}")
        
        if result.get('detected_phrases'):
            print(f"Phrases: {result['detected_phrases']}")
        
        context = result['context_score']
        print(f"Context: {context['tagalog_ratio']*100:.0f}% Tagalog, "
              f"{context['english_ratio']*100:.0f}% English, "
              f"Complexity: {context['complexity']}")

def test_improvements():
    """Demonstrate improvements with before/after examples"""
    print("\n" + "="*70)
    print("DEMONSTRATION: Enhanced Translation Pipeline")
    print("="*70)
    
    examples = [
        {
            "text": "kumakain na ako kanina pa",
            "what_improved": "Affix + Reduplication: 'kumakain' → 'um'+'ka'+'kain'"
        },
        {
            "text": "hindi ko alam kung pwede",
            "what_improved": "Phrase detection: 'hindi ko alam' → single phrase"
        },
        {
            "text": "grabe naman tlga si Maria",
            "what_improved": "Text-speak: 'tlga'→'talaga', Proper noun: 'Maria' preserved"
        },
        {
            "text": "kc gutom na ako, cnxa late",
            "what_improved": "Multiple text-speak: 'kc'→'kasi', 'cnxa'→'sensya'"
        },
        {
            "text": "naglalaro-laro lang sila",
            "what_improved": "Reduplication with hyphen: 'laro-laro'→'laro'"
        },
    ]
    
    for ex in examples:
        print(f"\n{'-'*70}")
        print(f"Input: {ex['text']}")
        print(f"Improvement: {ex['what_improved']}")
        
        result = preprocess_taglish_text(ex['text'])
        print(f"Output: {result['annotated_text']}")

if __name__ == "__main__":
    print("\n" + "="*70)
    print("TESTING ENHANCED PREPROCESSING PIPELINE")
    print("="*70)
    
    test_affix_stripping()
    test_reduplication()
    test_phrase_detection()
    test_phonetic_correction()
    test_full_pipeline()
    test_improvements()
    
    print("\n" + "="*70)
    print("ALL TESTS COMPLETED")
    print("="*70)
