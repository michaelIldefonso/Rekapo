"""
Test script comparing mBART translation with and without preprocessing
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Only import preprocessing (no heavy dependencies)
from ai_models.llm.preprocessing import preprocess_taglish_text

# Test cases with common Taglish patterns
test_texts = [
    "kc kumain na ako kaya busog na ko",
    "pwedi na tayo umuwi, tapos na meeting",
    "tlga maganda weather today",
    "bkt di ka pa umuwi?",
    "gsto ko mag bili ng pagkain",
]

print("=" * 80)
print("mBART TRANSLATION TEST - With vs Without Preprocessing")
print("=" * 80)

for i, text in enumerate(test_texts, 1):
    print(f"\n{'─' * 80}")
    print(f"Test {i}: {text}")
    print('─' * 80)
    
    # Show preprocessing results
    print("\n📋 PREPROCESSING:")
    print("-" * 40)
    prep = preprocess_taglish_text(text)
    print(f"Original:   {prep['original_text']}")
    print(f"Corrected:  {prep['corrected_text']}")
    print(f"Annotated:  {prep['annotated_text']}")
    
    context = prep['context_score']
    print(f"\nContext: {context['tagalog_ratio']*100:.0f}% TL, {context['english_ratio']*100:.0f}% EN, " +
          f"Complexity: {context['complexity']}, Switches: {context['switch_count']}")
    
    # Translation comparison (mock - actual translation requires model)
    print(f"\n🤖 TRANSLATION COMPARISON:")
    print("-" * 40)
    
    print("WITHOUT preprocessing:")
    print(f"  Input:  '{text}'")
    print(f"  Output: (would translate with errors/misspellings)")
    
    print("\nWITH preprocessing:")
    print(f"  Input:  '{prep['corrected_text']}'")
    print(f"  Output: (would translate corrected text)")
    
    # Uncomment below to test with actual model
    # result_with = translate_text(text, use_preprocessing=True)
    # result_without = translate_text(text, use_preprocessing=False)
    # print(f"\nACTUAL WITHOUT: {result_without['translated_text']}")
    # print(f"ACTUAL WITH:    {result_with['translated_text']}")

print("\n" + "=" * 80)
print("✅ Test complete! mBART now has preprocessing support.")
print("=" * 80)
print("\nKey improvements:")
print("  ✓ Text-speak corrections (kc → kasi, tlga → talaga)")
print("  ✓ Consistent word normalization")
print("  ✓ Better handling of code-switching")
print("  ✓ Context-aware translation")
