"""
Full Pipeline Comparison Test: Whisper + NLLB vs Whisper + Qwen

Tests the complete transcription and translation pipeline:
1. Whisper transcription (Tagalog audio → Tagalog text)
2. Translation comparison:
   - NLLB-200 (current)
   - Qwen 2.5-1.5B (new)
3. Compare against reference translations

Tests with 50 real audio samples from Excel reference file.
"""
import sys
from pathlib import Path
import time
import pandas as pd
from typing import Dict, List, Tuple
import difflib

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_models.whisper.inference import transcribe_audio_file
from ai_models.translator.inference import translate_text as nllb_translate
from ai_models.preprocessing.taglish import preprocess_taglish_text


def qwen_translate(text: str, normalize_taglish: bool = True, device: str = "auto") -> Dict[str, any]:
    """
    Translate using Qwen 2.5-1.5B with Taglish normalization.
    Uses the same function from translation comparison test.
    """
    from ai_models.summarizer.inference import get_summarizer
    import torch
    
    # Apply Taglish preprocessing
    preprocessing_result = None
    input_text = text
    
    if normalize_taglish:
        try:
            preprocessing_result = preprocess_taglish_text(text)
            input_text = preprocessing_result["annotated_text"]
        except Exception as e:
            print(f"      ⚠️  Preprocessing failed: {e}")
    
    # Load Qwen model
    model, tokenizer, device_used = get_summarizer(device=device)
    
    # Build translation prompt - direct instruction format to prevent meta-commentary
    messages = [
        {
            "role": "system", 
            "content": "Translate Filipino/Taglish to English. Output ONLY the English translation, nothing else. No explanations, no annotations, no meta-commentary."
        },
        {
            "role": "user", 
            "content": f"{input_text}"
        }
    ]
    
    # Apply chat template
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    
    # Tokenize
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    
    # Generate with strict settings to minimize meta-commentary
    start_time = time.time()
    with torch.no_grad():
        with torch.inference_mode():
            outputs = model.generate(
                **inputs,
                max_new_tokens=150,
                min_new_tokens=5,
                do_sample=True,
                temperature=0.1,  # Lower = more deterministic, less creative
                top_p=0.85,
                top_k=30,
                repetition_penalty=1.15,
                eos_token_id=tokenizer.eos_token_id,
                pad_token_id=tokenizer.pad_token_id if tokenizer.pad_token_id else tokenizer.eos_token_id,
                use_cache=True
            )
    
    translation_time = time.time() - start_time
    
    # Decode
    generated_ids = outputs[0][inputs.input_ids.shape[1]:]
    translated_text = tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
    
    # Aggressive cleanup to remove meta-commentary and annotations
    import re
    
    # Remove annotation patterns like [intj], [word:meaning], etc.
    translated_text = re.sub(r'\[[\w:]+\]', '', translated_text)
    
    # Remove meta-commentary patterns (case-insensitive)
    unwanted_patterns = [
        r"^Here'?s?\s+(an?\s+)?(appropriate\s+)?translation[:\s]*",
        r"^The translation is[:\s]*",
        r"^In English[:\s]*",
        r"^English translation[:\s]*",
        r"^Translation[:\s]*",
        r"^English[:\s]*",
        r"^I('ll| will) translate[^:]*[:\s]*",
        r"^This (means|translates|says)[:\s]*",
        r"^Let me translate[^:]*[:\s]*"
    ]
    
    for pattern in unwanted_patterns:
        translated_text = re.sub(pattern, '', translated_text, flags=re.IGNORECASE | re.MULTILINE)
    
    # Clean up any leading/trailing punctuation from cleanup
    translated_text = translated_text.strip()
    if translated_text and translated_text[0] in [':', '-', '—']:
        translated_text = translated_text[1:].strip()
    
    # Normalize whitespace
    translated_text = ' '.join(translated_text.split())
    
    return {
        "translated_text": translated_text,
        "preprocessing_used": preprocessing_result is not None,
        "translation_time": translation_time,
        "model": "Qwen"
    }


def calculate_similarity(text1: str, text2: str) -> float:
    """Calculate similarity ratio between two texts (0-100%)"""
    return difflib.SequenceMatcher(None, text1.lower(), text2.lower()).ratio() * 100


def calculate_word_error_rate(reference: str, hypothesis: str) -> float:
    """
    Calculate Word Error Rate (WER) between reference and hypothesis.
    WER = (S + D + I) / N where:
    S = substitutions, D = deletions, I = insertions, N = words in reference
    """
    ref_words = reference.lower().split()
    hyp_words = hypothesis.lower().split()
    
    # Use difflib to find operations
    matcher = difflib.SequenceMatcher(None, ref_words, hyp_words)
    
    substitutions = 0
    deletions = 0
    insertions = 0
    
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'replace':
            substitutions += max(i2 - i1, j2 - j1)
        elif tag == 'delete':
            deletions += (i2 - i1)
        elif tag == 'insert':
            insertions += (j2 - j1)
    
    if len(ref_words) == 0:
        return 0.0 if len(hyp_words) == 0 else 100.0
    
    wer = (substitutions + deletions + insertions) / len(ref_words) * 100
    return min(wer, 100.0)


def load_test_data(excel_path: str) -> pd.DataFrame:
    """Load test data from Excel file"""
    try:
        df = pd.read_excel(excel_path)
        print(f"✅ Loaded {len(df)} test samples from Excel")
        print(f"   Columns: {df.columns.tolist()}")
        return df
    except Exception as e:
        print(f"❌ Failed to load Excel file: {e}")
        raise


def test_single_audio(
    audio_path: str,
    reference_text: str,
    sample_number: int,
    audio_dir: Path,
    device: str = "cuda"
) -> Dict:
    """Test a single audio file through full pipeline"""
    print(f"\n{'─' * 100}")
    print(f"🎵 Sample {sample_number}: {audio_path}")
    print(f"{'─' * 100}")
    print(f"📝 Reference: {reference_text[:80]}...")
    
    full_audio_path = audio_dir / audio_path
    
    if not full_audio_path.exists():
        print(f"❌ Audio file not found: {full_audio_path}")
        return {
            "sample": sample_number,
            "audio_path": audio_path,
            "error": "Audio file not found"
        }
    
    result = {
        "sample": sample_number,
        "audio_path": audio_path,
        "reference": reference_text
    }
    
    # Step 1: Whisper Transcription
    print("\n🎤 Step 1: Whisper Transcription")
    try:
        transcribe_start = time.time()
        transcription_result = transcribe_audio_file(
            audio_path=str(full_audio_path),
            device=device,
            language="tl"  # Tagalog
        )
        transcription_time = time.time() - transcribe_start
        
        transcribed_text = transcription_result.get("text", "")
        detected_lang = transcription_result.get("language", "unknown")
        
        print(f"   ✅ Transcribed ({transcription_time:.2f}s, lang: {detected_lang})")
        print(f"   📝 Result: {transcribed_text[:80]}...")
        
        result["transcription"] = transcribed_text
        result["transcription_time"] = transcription_time
        result["detected_language"] = detected_lang
        
    except Exception as e:
        print(f"   ❌ Transcription failed: {e}")
        result["transcription_error"] = str(e)
        return result
    
    # Step 2: NLLB Translation
    print("\n📘 Step 2: NLLB Translation")
    try:
        nllb_result = nllb_translate(
            text=transcribed_text,
            source_lang="tgl_Latn",
            target_lang="eng_Latn",
            device=device,
            use_preprocessing=True
        )
        
        nllb_translation = nllb_result["translated_text"]
        print(f"   ✅ Translated ({nllb_result.get('translation_time', 0):.2f}s)")
        print(f"   📝 Result: {nllb_translation[:80]}...")
        
        # Calculate metrics
        nllb_similarity = calculate_similarity(reference_text, nllb_translation)
        nllb_wer = calculate_word_error_rate(reference_text, nllb_translation)
        
        print(f"   📊 Similarity: {nllb_similarity:.1f}% | WER: {nllb_wer:.1f}%")
        
        result["nllb_translation"] = nllb_translation
        result["nllb_similarity"] = nllb_similarity
        result["nllb_wer"] = nllb_wer
        
    except Exception as e:
        print(f"   ❌ NLLB translation failed: {e}")
        result["nllb_error"] = str(e)
    
    # Clear GPU memory before loading Qwen to prevent OOM
    if device == "cuda":
        import torch
        import gc
        
        # Clear NLLB model from cache
        from ai_models.translator import inference as translator_module
        if hasattr(translator_module, '_translator_cache'):
            translator_module._translator_cache.clear()
            print("\n🧹 Cleared NLLB model from cache")
        
        print("🧹 Clearing GPU memory...")
        gc.collect()
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
        print(f"   💾 GPU Memory: {torch.cuda.memory_allocated() / 1024**2:.0f}MB allocated, {torch.cuda.memory_reserved() / 1024**2:.0f}MB reserved")
    
    # Step 3: Qwen Translation
    print("\n🤖 Step 3: Qwen Translation")
    try:
        qwen_result = qwen_translate(
            text=transcribed_text,
            normalize_taglish=True,
            device=device
        )
        
        qwen_translation = qwen_result["translated_text"]
        print(f"   ✅ Translated ({qwen_result['translation_time']:.2f}s)")
        print(f"   📝 Result: {qwen_translation[:80]}...")
        
        # Calculate metrics
        qwen_similarity = calculate_similarity(reference_text, qwen_translation)
        qwen_wer = calculate_word_error_rate(reference_text, qwen_translation)
        
        print(f"   📊 Similarity: {qwen_similarity:.1f}% | WER: {qwen_wer:.1f}%")
        
        result["qwen_translation"] = qwen_translation
        result["qwen_similarity"] = qwen_similarity
        result["qwen_wer"] = qwen_wer
        
    except RuntimeError as e:
        if "out of memory" in str(e).lower() or "oom" in str(e).lower():
            print(f"   ❌ Qwen translation failed: OUT OF MEMORY")
            print(f"      💡 Try: Reduce max_new_tokens or use CPU")
            result["qwen_error"] = "OOM - GPU out of memory"
        else:
            print(f"   ❌ Qwen translation failed: {e}")
            result["qwen_error"] = str(e)
    except Exception as e:
        print(f"   ❌ Qwen translation failed: {e}")
        result["qwen_error"] = str(e)
    
    # Final cleanup after sample
    if device == "cuda":
        import torch
        import gc
        from ai_models.summarizer import inference as summarizer_module
        
        # Clear Qwen model cache to free memory for next sample
        if hasattr(summarizer_module, '_model_cache'):
            summarizer_module._model_cache.clear()
        
        gc.collect()
        torch.cuda.empty_cache()
    
    return result


def print_summary(results: List[Dict]):
    """Print comprehensive summary of all tests"""
    print(f"\n{'═' * 100}")
    print("📊 COMPREHENSIVE TEST SUMMARY")
    print(f"{'═' * 100}\n")
    
    # Filter successful results
    successful = [r for r in results if "transcription" in r and not r.get("transcription_error")]
    nllb_success = [r for r in successful if "nllb_translation" in r]
    qwen_success = [r for r in successful if "qwen_translation" in r]
    
    print(f"✅ Successful Transcriptions: {len(successful)}/{len(results)}")
    print(f"✅ Successful NLLB Translations: {len(nllb_success)}/{len(successful)}")
    print(f"✅ Successful Qwen Translations: {len(qwen_success)}/{len(successful)}")
    
    if successful:
        avg_transcription_time = sum(r["transcription_time"] for r in successful) / len(successful)
        print(f"\n⏱️  Average Transcription Time: {avg_transcription_time:.2f}s")
    
    if nllb_success:
        print(f"\n📘 NLLB-200 Performance:")
        avg_similarity = sum(r["nllb_similarity"] for r in nllb_success) / len(nllb_success)
        avg_wer = sum(r["nllb_wer"] for r in nllb_success) / len(nllb_success)
        print(f"   Average Similarity: {avg_similarity:.1f}%")
        print(f"   Average WER: {avg_wer:.1f}%")
    
    if qwen_success:
        print(f"\n🤖 Qwen 2.5-1.5B Performance:")
        avg_similarity = sum(r["qwen_similarity"] for r in qwen_success) / len(qwen_success)
        avg_wer = sum(r["qwen_wer"] for r in qwen_success) / len(qwen_success)
        print(f"   Average Similarity: {avg_similarity:.1f}%")
        print(f"   Average WER: {avg_wer:.1f}%")
    
    # Comparison
    if nllb_success and qwen_success:
        nllb_avg_sim = sum(r["nllb_similarity"] for r in nllb_success) / len(nllb_success)
        qwen_avg_sim = sum(r["qwen_similarity"] for r in qwen_success) / len(qwen_success)
        
        print(f"\n🔄 Comparison:")
        if qwen_avg_sim > nllb_avg_sim:
            diff = qwen_avg_sim - nllb_avg_sim
            print(f"   🏆 Qwen wins by {diff:.1f}% similarity")
        elif nllb_avg_sim > qwen_avg_sim:
            diff = nllb_avg_sim - qwen_avg_sim
            print(f"   🏆 NLLB wins by {diff:.1f}% similarity")
        else:
            print(f"   🤝 Tied performance")
    
    # Best and worst samples
    if nllb_success:
        best_nllb = max(nllb_success, key=lambda x: x["nllb_similarity"])
        worst_nllb = min(nllb_success, key=lambda x: x["nllb_similarity"])
        print(f"\n📈 NLLB Best: {best_nllb['audio_path']} ({best_nllb['nllb_similarity']:.1f}%)")
        print(f"📉 NLLB Worst: {worst_nllb['audio_path']} ({worst_nllb['nllb_similarity']:.1f}%)")
    
    if qwen_success:
        best_qwen = max(qwen_success, key=lambda x: x["qwen_similarity"])
        worst_qwen = min(qwen_success, key=lambda x: x["qwen_similarity"])
        print(f"\n📈 Qwen Best: {best_qwen['audio_path']} ({best_qwen['qwen_similarity']:.1f}%)")
        print(f"📉 Qwen Worst: {worst_qwen['audio_path']} ({worst_qwen['qwen_similarity']:.1f}%)")
    
    print(f"\n{'═' * 100}\n")


def run_full_pipeline_tests(
    excel_path: str = "tests/For testing.xlsx",
    audio_dir: str = "tests/audio_files",
    max_samples: int = None,
    device: str = "cuda"
):
    """Run full pipeline tests on all audio samples"""
    
    print("\n" + "═" * 100)
    print("🎬 FULL PIPELINE COMPARISON TEST")
    print("═" * 100)
    print("\nPipeline:")
    print("  1. 🎤 Whisper: Audio → Tagalog text")
    print("  2. 📘 NLLB-200: Tagalog → English (with preprocessing)")
    print("  3. 🤖 Qwen 2.5-1.5B: Tagalog → English (with Taglish normalization)")
    print("  4. 📊 Compare against reference")
    print("═" * 100)
    
    # Load test data
    try:
        df = load_test_data(excel_path)
    except Exception as e:
        print(f"❌ Cannot proceed without test data: {e}")
        return []
    
    audio_path = Path(audio_dir)
    if not audio_path.exists():
        print(f"❌ Audio directory not found: {audio_path}")
        return []
    
    # Limit samples if specified
    if max_samples:
        df = df.head(max_samples)
        print(f"\n⚠️  Testing limited to first {max_samples} samples")
    
    print(f"\n🎯 Testing {len(df)} audio samples...")
    
    results = []
    
    for idx, row in df.iterrows():
        audio_file = row['Audio Path']
        reference = row['Audio Text']
        
        try:
            result = test_single_audio(
                audio_path=audio_file,
                reference_text=reference,
                sample_number=idx + 1,
                audio_dir=audio_path,
                device=device
            )
            results.append(result)
            
            # Brief pause between samples
            time.sleep(0.5)
            
        except Exception as e:
            print(f"\n❌ Sample {idx + 1} ({audio_file}) failed: {e}")
            results.append({
                "sample": idx + 1,
                "audio_path": audio_file,
                "error": str(e)
            })
    
    print_summary(results)
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Full pipeline comparison test")
    parser.add_argument("--max-samples", type=int, default=5, help="Maximum samples to test (default: 5)")
    parser.add_argument("--device", type=str, default="cuda", choices=["cuda", "cpu"], help="Device to use")
    parser.add_argument("--all", action="store_true", help="Test all 50 samples")
    
    args = parser.parse_args()
    
    max_samples = None if args.all else args.max_samples
    
    print("\n🚀 Starting Full Pipeline Comparison Tests...")
    if max_samples:
        print(f"⚠️  Testing first {max_samples} samples (use --all for all 50)")
    else:
        print(f"⚠️  Testing ALL 50 samples (this will take time)")
    print(f"🖥️  Device: {args.device.upper()}")
    print("⏱️  Estimated time per sample: 5-10 seconds\n")
    
    results = run_full_pipeline_tests(
        max_samples=max_samples,
        device=args.device
    )
    
    print("✅ Full pipeline tests completed!")
    print(f"📁 Results: {len(results)} samples tested")
    print("\n💭 Recommendations:")
    print("   - Review samples with low similarity scores")
    print("   - Compare NLLB vs Qwen on complex Taglish")
    print("   - Check if Whisper transcription errors affect translation")
    print("   - Consider hybrid approach based on content type")
