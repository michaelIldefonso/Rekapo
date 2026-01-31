"""
Test to verify initial_prompt is working in Whisper transcription.
Compares transcription with and without prompt to see the difference.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_models.whisper.inference import transcribe_audio_file

def test_prompt_effect(audio_path: str):
    """
    Test the same audio with and without initial_prompt to see the difference.
    """
    print("\n" + "="*70)
    print("TESTING INITIAL_PROMPT EFFECT")
    print("="*70)
    
    print(f"\nAudio file: {audio_path}")
    
    # Test 1: Without prompt
    print("\n[TEST 1] Transcription WITHOUT initial_prompt:")
    print("-" * 70)
    
    result1 = transcribe_audio_file(
        audio_path=audio_path,
        language="tl",
        device="cuda",
        vad_filter=True,
        initial_prompt=None  # No prompt
    )
    
    print(f"Text: {result1['text']}")
    print(f"Language: {result1['language']} ({result1['language_probability']:.2%})")
    print(f"Segments: {len(result1['segments'])}")
    
    # Test 2: With Tagalog/English context prompt
    print("\n[TEST 2] Transcription WITH initial_prompt (Taglish context):")
    print("-" * 70)
    
    result2 = transcribe_audio_file(
        audio_path=audio_path,
        language="tl",
        device="cuda",
        vad_filter=True,
        initial_prompt="Ito ay isang meeting o pag-uusap sa Tagalog at English. Walang background music."
    )
    
    print(f"Text: {result2['text']}")
    print(f"Language: {result2['language']} ({result2['language_probability']:.2%})")
    print(f"Segments: {len(result2['segments'])}")
    
    # Test 3: With "no music" prompt
    print("\n[TEST 3] Transcription WITH initial_prompt (anti-hallucination):")
    print("-" * 70)
    
    result3 = transcribe_audio_file(
        audio_path=audio_path,
        language="tl",
        device="cuda",
        vad_filter=True,
        initial_prompt="No background music. No sound effects. Only clear speech."
    )
    
    print(f"Text: {result3['text']}")
    print(f"Language: {result3['language']} ({result3['language_probability']:.2%})")
    print(f"Segments: {len(result3['segments'])}")
    
    # Compare
    print("\n" + "="*70)
    print("COMPARISON")
    print("="*70)
    
    print(f"\nWithout prompt ({len(result1['text'].split())} words):")
    print(f"  {result1['text'][:100]}...")
    
    print(f"\nWith Taglish context ({len(result2['text'].split())} words):")
    print(f"  {result2['text'][:100]}...")
    
    print(f"\nWith anti-hallucination ({len(result3['text'].split())} words):")
    print(f"  {result3['text'][:100]}...")
    
    if result1['text'] != result2['text']:
        print("\n✅ initial_prompt IS affecting transcription!")
    else:
        print("\n⚠️  initial_prompt might not be having much effect on this audio")
    
    print("\n" + "="*70)

if __name__ == "__main__":
    # Find a sample audio file
    audio_dir = Path(__file__).parent.parent / "audiios"
    
    if audio_dir.exists():
        # First try to find audio files in session directories
        session_dirs = [d for d in audio_dir.iterdir() if d.is_dir() and d.name.startswith("session_")]
        
        audio_files = []
        if session_dirs:
            audio_files = list(session_dirs[0].glob("*.wav")) + list(session_dirs[0].glob("*.mp3")) + list(session_dirs[0].glob("*.webm"))
        
        # If no session dirs, look for audio files directly in audiios/
        if not audio_files:
            audio_files = list(audio_dir.glob("*.wav")) + list(audio_dir.glob("*.mp3")) + list(audio_dir.glob("*.webm"))
        
        if audio_files:
            print(f"Found {len(audio_files)} audio files, using: {audio_files[0].name}")
            test_prompt_effect(str(audio_files[0]))
        else:
            print("❌ No audio files found in audiios/")
    else:
        print("❌ audiios directory not found")
        print("\nUsage: Provide path to audio file:")
        print("python test_initial_prompt.py")
        print("\nOr run with custom path in code.")
