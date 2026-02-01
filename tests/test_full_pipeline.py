"""
Full Pipeline Integration Test
Tests the complete flow: Audio -> Whisper -> Preprocessing -> Translation -> Summarization

This test simulates the WebSocket endpoint flow without requiring WebSocket/Auth:
1. Audio file -> Whisper transcription (with hallucination filtering)
2. Preprocessing (Taglish detection, character cleaning)
3. Translation to English (NLLB or Qwen)
4. Summarization every 10 segments
5. Output comprehensive results
"""
import sys
from pathlib import Path
import json

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_models.whisper.inference import transcribe_audio_file
from ai_models.translator.inference import translate_text
from ai_models.llm.llm import translate_taglish_to_english
from ai_models.summarizer.inference import summarize_transcriptions
from config.config import TRANSLATION_MODEL, ENABLE_TAGLISH_PREPROCESSING

# ANSI color codes for nice output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    """Print formatted section header"""
    print(f"\n{Colors.HEADER}{'=' * 70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.HEADER}{'=' * 70}{Colors.ENDC}")

def print_step(step_num, text):
    """Print step indicator"""
    print(f"\n{Colors.CYAN}{Colors.BOLD}[STEP {step_num}] {text}{Colors.ENDC}")

def print_success(text):
    """Print success message"""
    print(f"{Colors.GREEN}✅ {text}{Colors.ENDC}")

def print_warning(text):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.ENDC}")

def print_error(text):
    """Print error message"""
    print(f"{Colors.RED}❌ {text}{Colors.ENDC}")

def print_info(label, value, indent=2):
    """Print labeled information"""
    spaces = " " * indent
    print(f"{spaces}{Colors.BOLD}{label}:{Colors.ENDC} {value}")

def translate_to_english(text: str, detected_lang: str = "tl") -> str:
    """
    Unified translation function matching whisper.py routing logic.
    Routes to NLLB or Qwen based on config.
    """
    if TRANSLATION_MODEL == "qwen":
        result = translate_taglish_to_english(
            text=text,
            device="cuda",
            max_new_tokens=512
        )
        return result["translated_text"]
    elif TRANSLATION_MODEL == "nllb":
        # Map language codes
        lang_map = {
            "tl": "tgl_Latn",
            "en": "eng_Latn",
            "fil": "tgl_Latn"
        }
        source_lang = lang_map.get(detected_lang, "tgl_Latn")
        
        result = translate_text(
            text=text,
            source_lang=source_lang,
            target_lang="eng_Latn",
            device="cuda"
        )
        return result["translated_text"]
    else:
        return text

def is_valid_taglish_text(text: str) -> bool:
    """
    Check if text contains valid Taglish (Tagalog/English) characters only.
    Returns False if text contains non-Latin characters.
    """
    if not text:
        return False
    
    # Allow Latin alphabet, numbers, punctuation, and spaces
    import re
    valid_pattern = r'^[A-Za-z0-9\s\.,!?\;:\'\"\(\)\-–—/\n\r]+$'
    return bool(re.match(valid_pattern, text))

def test_single_audio_file(audio_path: str, language: str = None):
    """
    Test the full pipeline on a single audio file.
    """
    print_header("🎯 FULL PIPELINE TEST - SINGLE AUDIO FILE")
    
    print_info("Audio File", audio_path, indent=0)
    print_info("Translation Model", TRANSLATION_MODEL.upper(), indent=0)
    print_info("Taglish Preprocessing", "ENABLED" if ENABLE_TAGLISH_PREPROCESSING else "DISABLED", indent=0)
    
    # STEP 1: Whisper Transcription
    print_step(1, "Whisper Transcription (with hallucination filtering)")
    
    try:
        result = transcribe_audio_file(
            audio_path=audio_path,
            language=language,
            device="cuda",
            vad_filter=False,  # VAD handled on frontend
            temperature=0.2,
            repetition_penalty=1.1,
            no_repeat_ngram_size=3
        )
        
        print_success("Transcription completed")
        print_info("Original Text", result["text"][:100] + "..." if len(result["text"]) > 100 else result["text"])
        print_info("Language", f"{result['language']} (confidence: {result['language_probability']:.2%})")
        print_info("Duration", f"{result['duration']:.2f}s")
        print_info("Segments", len(result["segments"]))
        
        # Check for hallucinations in segments
        if result["segments"]:
            hallucination_count = sum(1 for seg in result["segments"] if seg.get("no_speech_prob", 0) > 0.6)
            if hallucination_count > 0:
                print_warning(f"Note: {hallucination_count} segments were filtered as hallucinations")
        
    except Exception as e:
        print_error(f"Transcription failed: {e}")
        return None
    
    # Check if transcription is empty
    if not result["text"] or not result["text"].strip():
        print_warning("Transcription is empty - skipping")
        return None
    
    # STEP 2: Preprocessing - Validate Taglish
    print_step(2, "Preprocessing - Taglish Validation")
    
    if not is_valid_taglish_text(result["text"]):
        print_warning("Text contains non-Taglish characters - would be skipped in production")
        print_info("Invalid chars detected in", result["text"][:50])
    else:
        print_success("Text validated as Taglish")
    
    # Force detected language to be either Tagalog or English
    if result["language"] not in ["tl", "en"]:
        print_warning(f"Language '{result['language']}' detected, forcing to 'tl' (Tagalog)")
        result["language"] = "tl"
    
    # STEP 3: Translation to English
    print_step(3, f"Translation to English ({TRANSLATION_MODEL.upper()})")
    
    try:
        english_translation = translate_to_english(
            result["text"],
            result["language"]
        )
        
        print_success("Translation completed")
        print_info("English", english_translation[:100] + "..." if len(english_translation) > 100 else english_translation)
        
    except Exception as e:
        print_error(f"Translation failed: {e}")
        english_translation = result["text"]
    
    return {
        "segment_number": 1,
        "transcription": result["text"],
        "english_translation": english_translation,
        "language": result["language"],
        "duration": result["duration"],
        "segments": result["segments"]
    }

def test_multiple_segments_with_summarization(audio_files: list, language: str = None):
    """
    Test the full pipeline with multiple audio segments.
    Generates summaries every 10 segments.
    """
    print_header("🎯 FULL PIPELINE TEST - MULTIPLE SEGMENTS + SUMMARIZATION")
    
    print_info("Number of Audio Files", len(audio_files), indent=0)
    print_info("Translation Model", TRANSLATION_MODEL.upper(), indent=0)
    print_info("Summarization", "Every 10 segments", indent=0)
    
    all_transcriptions = []
    summaries = []
    
    for idx, audio_path in enumerate(audio_files, 1):
        print(f"\n{Colors.BLUE}{'─' * 70}{Colors.ENDC}")
        print(f"{Colors.BLUE}Processing Segment {idx}/{len(audio_files)}: {Path(audio_path).name}{Colors.ENDC}")
        print(f"{Colors.BLUE}{'─' * 70}{Colors.ENDC}")
        
        # Process single audio file through full pipeline
        result = test_single_audio_file(audio_path, language)
        
        if result:
            result["segment_number"] = idx
            all_transcriptions.append(result)
            
            # Check if we should generate a summary (every 10 chunks)
            if idx % 10 == 0 and len(all_transcriptions) >= 10:
                print_step(4, f"Generating Summary (Segments {idx-9} to {idx})")
                
                try:
                    # Get last 10 transcriptions
                    recent_transcriptions = all_transcriptions[-10:]
                    
                    # Generate summary
                    summary_result = summarize_transcriptions(
                        transcriptions=recent_transcriptions,
                        device="cuda",
                        max_length=200,
                        min_length=50
                    )
                    
                    print_success("Summary generated")
                    print_info("Summary", summary_result["summary"])
                    print_info("Chunks", summary_result["chunk_count"])
                    print_info("Compression", f"{len(summary_result['summary'].split())}/{summary_result['original_length']} words")
                    
                    summaries.append({
                        "range": f"{idx-9}-{idx}",
                        "summary": summary_result["summary"],
                        "chunk_count": summary_result["chunk_count"]
                    })
                    
                except Exception as e:
                    print_error(f"Summarization failed: {e}")
    
    # Final Summary
    print_header("📊 PIPELINE TEST RESULTS")
    
    print_info("Total Segments Processed", len(all_transcriptions), indent=0)
    print_info("Summaries Generated", len(summaries), indent=0)
    
    if all_transcriptions:
        print(f"\n{Colors.BOLD}All Transcriptions:{Colors.ENDC}")
        for trans in all_transcriptions:
            print(f"\n  {Colors.CYAN}Segment #{trans['segment_number']}:{Colors.ENDC}")
            print(f"    Original: {trans['transcription'][:60]}...")
            print(f"    English:  {trans['english_translation'][:60]}...")
    
    if summaries:
        print(f"\n{Colors.BOLD}Generated Summaries:{Colors.ENDC}")
        for summary in summaries:
            print(f"\n  {Colors.CYAN}Chunks {summary['range']}:{Colors.ENDC}")
            print(f"    {summary['summary']}")
    
    return {
        "transcriptions": all_transcriptions,
        "summaries": summaries
    }

def test_with_sample_audio():
    """
    Test with sample audio files from the audiios directory.
    """
    print_header("🔍 SEARCHING FOR SAMPLE AUDIO FILES")
    
    # Look for audio files in audiios directory
    audio_dir = Path(__file__).parent.parent / "audiios"
    
    if not audio_dir.exists():
        print_error("audiios directory not found")
        print_info("Expected location", str(audio_dir))
        return
    
    # Find session directories with audio files
    session_dirs = [d for d in audio_dir.iterdir() if d.is_dir() and d.name.startswith("session_")]
    
    if not session_dirs:
        print_error("No session directories found in audiios/")
        return
    
    # Use the first session directory
    session_dir = session_dirs[0]
    print_info("Using session", session_dir.name, indent=0)
    
    # Find audio files (wav, mp3, webm)
    audio_files = []
    for ext in ["*.wav", "*.mp3", "*.webm"]:
        audio_files.extend(list(session_dir.glob(ext)))
    
    if not audio_files:
        print_error(f"No audio files found in {session_dir}")
        return
    
    # Sort by name and take first few
    audio_files = sorted(audio_files)[:15]  # Test with up to 15 segments
    
    print_success(f"Found {len(audio_files)} audio files")
    for f in audio_files[:5]:
        print_info("  -", f.name)
    if len(audio_files) > 5:
        print_info("  -", f"... and {len(audio_files) - 5} more")
    
    # Run the full pipeline test
    test_multiple_segments_with_summarization([str(f) for f in audio_files], language=None)

def run_manual_test():
    """
    Run test with manually specified audio file paths.
    """
    print_header("⚙️  MANUAL AUDIO FILE TEST")
    
    print("Enter audio file paths (one per line, empty line to finish):")
    print("Example: C:/path/to/audio.wav")
    
    audio_files = []
    while True:
        path = input(f"{Colors.CYAN}Audio file {len(audio_files) + 1}:{Colors.ENDC} ").strip()
        if not path:
            break
        
        if not Path(path).exists():
            print_error(f"File not found: {path}")
            continue
        
        audio_files.append(path)
        print_success(f"Added: {Path(path).name}")
    
    if not audio_files:
        print_warning("No audio files provided")
        return
    
    # Run the test
    test_multiple_segments_with_summarization(audio_files, language=None)

if __name__ == "__main__":
    print("\n")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}🧪 FULL PIPELINE INTEGRATION TEST{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 70}{Colors.ENDC}")
    print(f"{Colors.HEADER}Audio → Whisper → Preprocessing → Translation → Summarization{Colors.ENDC}")
    print(f"{Colors.HEADER}{'=' * 70}{Colors.ENDC}\n")
    
    print("Select test mode:")
    print("  1. Auto-detect sample audio from audiios/")
    print("  2. Manual audio file paths")
    
    choice = input(f"\n{Colors.CYAN}Choice (1 or 2):{Colors.ENDC} ").strip()
    
                elif idx % 10 == 0:
                    print_warning(f"Summary not generated: only {len(all_transcriptions)} segments so far (need 10)")
    if choice == "1":
        test_with_sample_audio()
    elif choice == "2":
        run_manual_test()
    else:
        print_error("Invalid choice")
        sys.exit(1)
    
    print(f"\n{Colors.GREEN}{Colors.BOLD}✅ Pipeline test completed!{Colors.ENDC}\n")
