"""
Test if hallucination filtering is helping or hurting with the fine-tuned model.
Tests audio with silence/noise to see if "You" and similar issues appear.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_models.whisper.inference import transcribe_audio_file

def test_with_and_without_hallucination_filter(audio_files: list):
    """
    Compare results with hallucination filtering enabled vs disabled
    """
    print("\n" + "="*70)
    print("TESTING HALLUCINATION FILTERING")
    print("="*70)
    
    for audio_path in audio_files[:3]:  # Test first 3 files
        print(f"\n{'─'*70}")
        print(f"Audio: {Path(audio_path).name}")
        print(f"{'─'*70}")
        
        # Transcribe normally (with filtering)
        result = transcribe_audio_file(
            audio_path=audio_path,
            language="tl",
            device="cuda",
            vad_filter=True,
            initial_prompt=None
        )
        
        print(f"\n✅ WITH hallucination filtering:")
        print(f"   Text: {result['text']}")
        print(f"   Segments: {len(result['segments'])}")
        
        # Show what was filtered (if any)
        if result['segments']:
            for seg in result['segments']:
                no_speech = seg.get('no_speech_prob', 0)
                if no_speech > 0.5:
                    print(f"   ⚠️  High no_speech_prob: {no_speech:.2f} - '{seg['text']}'")
        
        # Check if text is empty (everything was filtered)
        if not result['text'].strip():
            print(f"   ⚠️  All segments were filtered as hallucinations!")

if __name__ == "__main__":
    audio_dir = Path(__file__).parent.parent / "audiios"
    
    audio_files = list(audio_dir.glob("*.wav")) + list(audio_dir.glob("*.mp3")) + list(audio_dir.glob("*.webm"))
    
    if audio_files:
        print(f"Found {len(audio_files)} audio files")
        test_with_and_without_hallucination_filter([str(f) for f in sorted(audio_files)])
    else:
        print("❌ No audio files found in audiios/")
