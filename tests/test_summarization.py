"""
Test script for summarization functionality.
Tests BART-based summarization for meeting transcriptions.
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_models.summarizer.inference import (
    summarize_text,
    summarize_transcriptions,
    summarize_meeting_segments,
    get_summarizer
)

def print_test_header(test_name):
    """Print formatted test header"""
    print("\n" + "=" * 70)
    print(f"🧪 {test_name}")
    print("=" * 70)

def print_result(label, value, max_width=60):
    """Print formatted result"""
    if isinstance(value, str) and len(value) > max_width:
        value = value[:max_width-3] + "..."
    print(f"  {label}: {value}")

def test_basic_summarization():
    """Test basic text summarization"""
    print_test_header("Test 1: Basic Text Summarization")
    
    sample_text = """
    In today's meeting, we discussed the implementation of the new feature for real-time 
    transcription. The team decided to use faster-whisper for improved performance. 
    We also talked about integrating Cloudflare R2 for storage instead of local storage. 
    The mobile app will receive transcriptions via WebSocket and display them in real-time. 
    We agreed to implement summarization every 10 chunks to help users keep track of long meetings. 
    The project deadline is set for the end of the month, and we need to complete testing by next week.
    """
    
    print("📝 Original Text:")
    print(sample_text.strip())
    print(f"\n📊 Original Length: {len(sample_text.split())} words")
    
    try:
        result = summarize_text(
            text=sample_text,
            device="cuda",  # Use GPU
            max_length=300,
            min_length=75
        )
        
        print(f"\n✅ Summarization Successful!")
        print_result("Summary", result["summary"])
        print_result("Original Word Count", result["original_length"])
        print_result("Compression Ratio", f"{(1 - len(result['summary'].split()) / result['original_length']) * 100:.1f}%")
        
        return True
    except Exception as e:
        print(f"\n❌ Summarization Failed: {e}")
        return False

def test_empty_text():
    """Test summarization with empty text"""
    print_test_header("Test 2: Empty Text Handling")
    
    try:
        result = summarize_text(text="", device="cuda")
        
        if result["summary"] == "" and result["original_length"] == 0:
            print("✅ Empty text handled correctly")
            print_result("Summary", result["summary"] or "(empty)")
            print_result("Original Length", result["original_length"])
            return True
        else:
            print("❌ Empty text not handled correctly")
            return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_transcription_summarization():
    """Test summarization of transcription chunks"""
    print_test_header("Test 3: Transcription Chunks Summarization")
    
    transcription_chunks = [
        {
            "transcription": "Magandang umaga po sa inyong lahat",
            "english_translation": "Good morning to everyone",
            "segment_number": 1
        },
        {
            "transcription": "Ngayon ay pag-uusapan natin ang bagong feature",
            "english_translation": "Today we will discuss the new feature",
            "segment_number": 2
        },
        {
            "transcription": "Ang real-time transcription ay mahalaga para sa meeting",
            "english_translation": "Real-time transcription is important for meetings",
            "segment_number": 3
        },
        {
            "transcription": "Gagamitin natin ang faster-whisper technology",
            "english_translation": "We will use faster-whisper technology",
            "segment_number": 4
        },
        {
            "transcription": "Kailangan natin ng R2 storage para sa files",
            "english_translation": "We need R2 storage for files",
            "segment_number": 5
        }
    ]
    
    print(f"📝 Number of Chunks: {len(transcription_chunks)}")
    print("\n📋 Transcription Chunks:")
    for chunk in transcription_chunks:
        print(f"  Segment {chunk['segment_number']}: {chunk['transcription']}")
        print(f"    → {chunk['english_translation']}")
    
    try:
        result = summarize_transcriptions(
            transcriptions=transcription_chunks,
            device="cuda",
            max_length=300,
            min_length=75
        )
        
        print(f"\n✅ Transcription Summarization Successful!")
        print_result("Summary", result["summary"])
        print_result("Chunk Count", result["chunk_count"])
        print_result("Original Word Count", result["original_length"])
        
        return True
    except Exception as e:
        print(f"\n❌ Transcription Summarization Failed: {e}")
        return False

def test_meeting_segments_summarization():
    """Test summarization of meeting segments with timing"""
    print_test_header("Test 4: Meeting Segments with Timing")
    
    meeting_segments = [
        {
            "transcription": "Magsisimula na tayo ng meeting",
            "english_translation": "We will now start the meeting",
            "duration": 3.5,
            "timestamp": "00:00:00"
        },
        {
            "transcription": "Ang agenda para ngayon ay project updates",
            "english_translation": "The agenda for today is project updates",
            "duration": 4.2,
            "timestamp": "00:00:03"
        },
        {
            "transcription": "First topic is about the mobile application",
            "english_translation": "First topic is about the mobile application",
            "duration": 3.8,
            "timestamp": "00:00:07"
        },
        {
            "transcription": "Tapos na ang development ng voice recording feature",
            "english_translation": "The development of voice recording feature is complete",
            "duration": 4.5,
            "timestamp": "00:00:11"
        },
        {
            "transcription": "Susunod natin ay testing at deployment",
            "english_translation": "Next we will do testing and deployment",
            "duration": 3.9,
            "timestamp": "00:00:15"
        }
    ]
    
    print(f"📝 Number of Segments: {len(meeting_segments)}")
    print("\n📋 Meeting Segments:")
    for seg in meeting_segments:
        print(f"  [{seg['timestamp']}] ({seg['duration']}s) {seg['transcription']}")
        print(f"    → {seg['english_translation']}")
    
    try:
        result = summarize_meeting_segments(
            segments=meeting_segments,
            device="cuda",
            max_length=300,
            min_length=75
        )
        
        print(f"\n✅ Meeting Segment Summarization Successful!")
        print_result("Summary", result["summary"])
        print_result("Segment Count", result["segment_count"])
        print_result("Total Duration", f"{result['total_duration']:.1f}s")
        
        return True
    except Exception as e:
        print(f"\n❌ Meeting Segment Summarization Failed: {e}")
        return False

def test_long_text_summarization():
    """Test summarization of longer text (like real meeting notes)"""
    print_test_header("Test 5: Long Text Summarization (Real Meeting Scenario)")
    
    long_text = """
    The meeting started with introductions from all team members. We have five developers, 
    two designers, and one project manager present. The main topic of discussion was the 
    implementation of the new real-time transcription feature for our meeting application.
    
    First, we discussed the technical architecture. The team decided to use faster-whisper 
    for speech recognition because it offers better performance compared to the standard 
    Whisper model. We also talked about using NLLB-200 for translation to support multiple 
    languages, particularly focusing on Tagalog and English which are commonly used in our 
    target market.
    
    Storage was another important topic. We evaluated several options and decided to use 
    Cloudflare R2 for storing audio files and profile photos. R2 is cost-effective and 
    provides good performance with S3-compatible API. We need to ensure proper error 
    handling and logging for all R2 operations.
    
    The mobile application will use WebSocket for real-time communication with the server. 
    Audio chunks will be sent continuously, and the server will respond with transcriptions 
    and translations immediately. We also agreed to implement automatic summarization every 
    10 chunks so users don't miss important points during long meetings.
    
    Testing requirements were outlined. We need comprehensive unit tests for all components, 
    integration tests for the WebSocket communication, and end-to-end tests with real audio 
    samples. The QA team will prepare test cases for both Tagalog and English audio.
    
    Finally, we set the project timeline. Development should be completed by the end of this 
    month. Testing phase will take one week, followed by a week for bug fixes and optimization. 
    The production deployment is scheduled for the first week of next month. Everyone agreed 
    to the timeline and committed to their respective tasks.
    """
    
    word_count = len(long_text.split())
    print(f"📊 Original Length: {word_count} words")
    print(f"📝 Preview: {long_text[:200]}...")
    
    try:
        result = summarize_text(
            text=long_text,
            device="cuda",
            max_length=400,
            min_length=100
        )
        
        print(f"\n✅ Long Text Summarization Successful!")
        print_result("Summary", result["summary"], max_width=200)
        print_result("Original Word Count", result["original_length"])
        print_result("Summary Word Count", len(result["summary"].split()))
        print_result("Compression Ratio", f"{(1 - len(result['summary'].split()) / result['original_length']) * 100:.1f}%")
        
        return True
    except Exception as e:
        print(f"\n❌ Long Text Summarization Failed: {e}")
        return False

def test_model_loading():
    """Test model loading and caching"""
    print_test_header("Test 6: Model Loading and Caching")
    
    try:
        print("🔄 Loading summarizer model (first time)...")
        generator1, tokenizer1, device1 = get_summarizer(device="cuda")
        print("✅ Model loaded successfully")
        
        print("\n🔄 Loading summarizer model again (should use cache)...")
        generator2, tokenizer2, device2 = get_summarizer(device="cuda")
        print("✅ Model retrieved from cache")
        
        # Check if the same generator object is returned (indicating caching works)
        if generator1 is generator2:
            print("\n✅ Caching works correctly (same generator object)")
            return True
        else:
            print("\n⚠️  Warning: Different generator objects (caching might not be working)")
            return False
    except Exception as e:
        print(f"\n❌ Model Loading Failed: {e}")
        return False

def run_all_tests():
    """Run all summarization tests"""
    from config.config import SUMMARIZER_MODEL_PATH
    
    print("\n")
    print("=" * 70)
    print("🧪 SUMMARIZATION TEST SUITE")
    print("=" * 70)
    print(f"Testing Qwen 2.5-1.5B Instruct for meeting transcription summarization")
    print(f"Model: {SUMMARIZER_MODEL_PATH}")
    print("Device: GPU (CUDA)")
    print("=" * 70)
    
    tests = [
        ("Model Loading", test_model_loading),
        ("Basic Summarization", test_basic_summarization),
        ("Empty Text", test_empty_text),
        ("Transcription Chunks", test_transcription_summarization),
        ("Meeting Segments", test_meeting_segments_summarization),
        ("Long Text", test_long_text_summarization),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"\n❌ Test crashed: {e}")
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {test_name}")
    
    print("\n" + "-" * 70)
    print(f"  Total: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print("=" * 70)
    
    return passed == total

if __name__ == "__main__":
    print("\n🚀 Starting Summarization Tests...")
    print("⚠️  Note: This will download Qwen 2.5-1.5B (~3GB) if not already cached")
    print("⏱️  First run may take several minutes...\n")
    
    success = run_all_tests()
    
    if success:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)
