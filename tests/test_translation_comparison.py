"""
Translation Comparison Test: NLLB vs Qwen

Compares translation quality between:
1. NLLB-200 (current) - Fast, specialized translation model
2. Qwen 2.5-1.5B (new) - LLM with Taglish normalization

Tests with real Taglish samples to evaluate:
- Translation accuracy
- Taglish handling
- Context preservation
- Speed comparison
"""
import sys
from pathlib import Path
import time
from typing import Dict, List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_models.translator.inference import translate_text as nllb_translate
from ai_models.preprocessing.taglish import preprocess_taglish_text


def qwen_translate(
    text: str,
    normalize_taglish: bool = True,
    device: str = "auto"
) -> Dict[str, any]:
    """
    Translate using Qwen 2.5-1.5B with enhanced Taglish normalization.
    
    Args:
        text: Text to translate
        normalize_taglish: Apply preprocessing normalization
        device: Device to use
    
    Returns:
        Dictionary with translation and metadata
    """
    from ai_models.summarizer.inference import get_summarizer
    from transformers import AutoTokenizer
    import torch
    
    # Apply Taglish preprocessing
    preprocessing_result = None
    input_text = text
    
    if normalize_taglish:
        try:
            preprocessing_result = preprocess_taglish_text(text)
            # Use enriched annotation for better translation
            input_text = preprocessing_result["annotated_text"]
            print(f"   📝 Preprocessed: {input_text[:100]}...")
        except Exception as e:
            print(f"   ⚠️  Preprocessing failed: {e}")
    
    # Load Qwen model (shared with summarizer)
    model, tokenizer, device_used = get_summarizer(device=device)
    
    # Build translation prompt
    messages = [
        {
            "role": "system", 
            "content": "You are a professional Filipino-English translator. Translate Taglish (mixed Tagalog-English) text to natural, fluent English. Preserve proper nouns and brand names. If annotations like [word:meaning] appear, use them as hints for accurate translation."
        },
        {
            "role": "user", 
            "content": f"Translate this Taglish text to English. Keep it natural and conversational:\n\n{input_text}\n\nEnglish translation:"
        }
    ]
    
    # Apply chat template
    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )
    
    # Tokenize
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    
    # Generate translation
    start_time = time.time()
    with torch.no_grad():
        with torch.inference_mode():
            outputs = model.generate(
                **inputs,
                max_new_tokens=200,
                min_new_tokens=10,
                do_sample=True,
                temperature=0.3,  # Lower temperature for more consistent translation
                top_p=0.9,
                top_k=40,
                repetition_penalty=1.2,
                eos_token_id=tokenizer.eos_token_id,
                pad_token_id=tokenizer.pad_token_id if tokenizer.pad_token_id else tokenizer.eos_token_id,
                use_cache=True
            )
    
    translation_time = time.time() - start_time
    
    # Decode
    generated_ids = outputs[0][inputs.input_ids.shape[1]:]
    translated_text = tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
    
    # Clean up common unwanted patterns
    unwanted_patterns = [
        "English translation:", "Translation:", "Here's the translation:",
        "The translation is:", "In English:", "English:"
    ]
    for pattern in unwanted_patterns:
        if translated_text.lower().startswith(pattern.lower()):
            translated_text = translated_text[len(pattern):].strip()
            if translated_text and translated_text[0] in [':', '-']:
                translated_text = translated_text[1:].strip()
    
    return {
        "translated_text": translated_text,
        "preprocessing_used": preprocessing_result is not None,
        "preprocessing_info": preprocessing_result,
        "translation_time": translation_time,
        "model": "Qwen 2.5-1.5B"
    }


# Test samples - Real Taglish scenarios
TEST_SAMPLES = [
    {
        "name": "Simple Taglish",
        "text": "Kumain na ako ng breakfast tapos nag-work from home",
        "expected": "I already ate breakfast then worked from home"
    },
    {
        "name": "Code-switching",
        "text": "Yung client meeting natin bukas, need ba mag-prepare ng presentation?",
        "expected": "Our client meeting tomorrow, do we need to prepare a presentation?"
    },
    {
        "name": "Text speak",
        "text": "Pde ba ako mag-late today? Traffic kasi grabe sa EDSA",
        "expected": "Can I be late today? The traffic on EDSA is really bad"
    },
    {
        "name": "Reduplication",
        "text": "Bili-bili lang yan sa tindahan, mura-mura pa",
        "expected": "You can just buy that at the store, it's quite cheap"
    },
    {
        "name": "Complex mixing",
        "text": "Grabe yung meeting kanina, sobrang haba tapos walang agenda. Hindi ko na gets bakit andun pa ako.",
        "expected": "That meeting earlier was intense, it was super long and had no agenda. I don't understand why I was even there."
    },
    {
        "name": "Colloquialisms",
        "text": "Sana all may work from home setup. Ako naman kailangan pa mag-commute every day.",
        "expected": "I wish everyone had a work from home setup. I still have to commute every day."
    },
    {
        "name": "Business context",
        "text": "Okay lang yung proposal nila pero yung timeline medyo tight. Kaya ba natin yan by next week?",
        "expected": "Their proposal is okay but the timeline is quite tight. Can we do that by next week?"
    },
    {
        "name": "Casual conversation",
        "text": "Tara na lunch! Gutom na ako eh. San tayo kakain?",
        "expected": "Let's go have lunch! I'm already hungry. Where shall we eat?"
    }
]


def print_comparison_header():
    """Print formatted test header"""
    print("\n" + "═" * 100)
    print("🔄 TRANSLATION COMPARISON: NLLB-200 vs Qwen 2.5-1.5B")
    print("═" * 100)
    print("\nTesting with real Taglish samples to compare:")
    print("  📘 NLLB-200: Specialized translation model (current)")
    print("  🤖 Qwen 2.5-1.5B: LLM with Taglish normalization (new)")
    print("═" * 100)


def print_sample_header(sample: Dict, index: int):
    """Print formatted sample header"""
    print(f"\n{'─' * 100}")
    print(f"🧪 Test {index}: {sample['name']}")
    print(f"{'─' * 100}")
    print(f"📝 Original: {sample['text']}")
    print(f"🎯 Expected: {sample['expected']}")
    print()


def print_translation_result(method: str, result: Dict, emoji: str):
    """Print formatted translation result"""
    print(f"\n{emoji} {method}:")
    print(f"   Translation: {result['translated_text']}")
    print(f"   Time: {result.get('translation_time', 0):.3f}s")
    
    if result.get('preprocessing_info'):
        prep = result['preprocessing_info']
        ctx = prep['context_score']
        print(f"   Preprocessing:")
        print(f"     - Corrected: {prep['corrected_text'][:60]}...")
        print(f"     - Tagalog ratio: {ctx['tagalog_ratio']*100:.0f}%")
        print(f"     - Complexity: {ctx['complexity']}")
        if prep['detected_phrases']:
            print(f"     - Phrases: {len(prep['detected_phrases'])} detected")


def compare_translations(sample: Dict, index: int) -> Dict:
    """Compare NLLB and Qwen translations for a sample"""
    print_sample_header(sample, index)
    
    # Test 1: NLLB translation
    print("⏳ Testing NLLB-200...")
    try:
        start_time = time.time()
        nllb_result = nllb_translate(
            text=sample['text'],
            source_lang="tgl_Latn",
            target_lang="eng_Latn",
            device="cuda",
            use_preprocessing=True  # Use existing preprocessing
        )
        nllb_result['translation_time'] = time.time() - start_time
        nllb_result['model'] = "NLLB-200"
        
        print_translation_result("NLLB-200", nllb_result, "📘")
    except Exception as e:
        print(f"❌ NLLB failed: {e}")
        nllb_result = None
    
    # Test 2: Qwen translation
    print("\n⏳ Testing Qwen 2.5-1.5B...")
    try:
        qwen_result = qwen_translate(
            text=sample['text'],
            normalize_taglish=True,
            device="cuda"
        )
        
        print_translation_result("Qwen 2.5-1.5B", qwen_result, "🤖")
    except Exception as e:
        print(f"❌ Qwen failed: {e}")
        qwen_result = None
    
    return {
        "sample": sample,
        "nllb": nllb_result,
        "qwen": qwen_result
    }


def print_summary(results: List[Dict]):
    """Print comparison summary"""
    print(f"\n{'═' * 100}")
    print("📊 COMPARISON SUMMARY")
    print(f"{'═' * 100}\n")
    
    nllb_times = [r['nllb']['translation_time'] for r in results if r['nllb']]
    qwen_times = [r['qwen']['translation_time'] for r in results if r['qwen']]
    
    print(f"⏱️  Average Translation Time:")
    print(f"   NLLB-200: {sum(nllb_times)/len(nllb_times):.3f}s")
    print(f"   Qwen 2.5-1.5B: {sum(qwen_times)/len(qwen_times):.3f}s")
    print(f"   Speed difference: {(sum(qwen_times)/len(qwen_times)) / (sum(nllb_times)/len(nllb_times)):.1f}x slower")
    
    print(f"\n📈 Successful Translations:")
    print(f"   NLLB-200: {len([r for r in results if r['nllb']])}/{len(results)}")
    print(f"   Qwen 2.5-1.5B: {len([r for r in results if r['qwen']])}/{len(results)}")
    
    print(f"\n{'─' * 100}")
    print("💡 Quality Assessment (Manual Review Recommended):")
    print("   - Check naturalness and fluency")
    print("   - Verify Taglish handling (code-switching)")
    print("   - Compare context preservation")
    print("   - Evaluate proper noun handling")
    print(f"{'═' * 100}\n")


def run_comparison_tests():
    """Run all comparison tests"""
    print_comparison_header()
    
    results = []
    
    for i, sample in enumerate(TEST_SAMPLES, 1):
        try:
            result = compare_translations(sample, i)
            results.append(result)
            
            # Brief pause between tests
            time.sleep(0.5)
        except Exception as e:
            print(f"\n❌ Test {i} failed: {e}")
            import traceback
            traceback.print_exc()
    
    print_summary(results)
    
    return results


if __name__ == "__main__":
    print("\n🚀 Starting Translation Comparison Tests...")
    print("⚠️  This will test both NLLB and Qwen models")
    print("⏱️  Estimated time: 2-3 minutes\n")
    
    results = run_comparison_tests()
    
    print("✅ Comparison tests completed!")
    print(f"📁 Results: {len(results)} samples tested")
    print("\n💭 Next steps:")
    print("   1. Review translation quality manually")
    print("   2. Compare naturalness and accuracy")
    print("   3. Decide which model to use for production")
    print("   4. Consider hybrid approach (NLLB for speed, Qwen for quality)")
