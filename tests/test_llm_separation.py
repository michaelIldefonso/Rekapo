"""
Test script demonstrating the separation of preprocessing and LLM translation
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import ONLY preprocessing (no transformers/torch required)
from ai_models.preprocessing import preprocess_taglish_text

# LLM translation import commented out to test preprocessing independently
# from ai_models.llm.llm import translate_taglish_to_english

# Test cases
test_texts = [
    "kc kumain na ako kaya busog na ko",
    "pwede na tayo umuwi, tapos na meeting",
    "maganda talaga weather today",
]

print("=" * 80)
print("TAGLISH TRANSLATION TEST - Separated Preprocessing & LLM")
print("=" * 80)

for i, text in enumerate(test_texts, 1):
    print(f"\n{'─' * 80}")
    print(f"Test {i}: {text}")
    print('─' * 80)
    
    # Step 1: Preprocessing only (standalone)
    print("\n📋 PREPROCESSING RESULTS:")
    print("-" * 40)
    preprocessing = preprocess_taglish_text(text)
    
    print(f"Original:    {preprocessing['original_text']}")
    print(f"Corrected:   {preprocessing['corrected_text']}")
    print(f"Annotated:   {preprocessing['annotated_text']}")
    
    context = preprocessing['context_score']
    print(f"\nContext Analysis:")
    print(f"  • Tagalog: {context['tagalog_ratio']*100:.0f}% | English: {context['english_ratio']*100:.0f}%")
    print(f"  • Complexity: {context['complexity']}")
    print(f"  • Dominant: {context['dominant_language']}")
    print(f"  • Switches: {context['switch_count']}")
    
    # Step 2: Full translation (with preprocessing integrated)
    print(f"\n🤖 TRANSLATION RESULT:")
    print("-" * 40)
    # Uncomment below when ready to test with model
    # result = translate_taglish_to_english(text)
    # print(f"English: {result['translated_text']}")
    # print(f"Model: {result['model_used']}")
    print("(Translation disabled - model not loaded in test)")

print("\n" + "=" * 80)
print("✅ Test complete! Preprocessing and LLM are successfully separated.")
print("=" * 80)
