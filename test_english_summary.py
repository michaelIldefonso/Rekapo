"""
Quick test for English text summarization with Qwen 2.5-3B CT2
"""
from ai_models.summarizer.inference import summarize_text, summarize_transcriptions

print("=" * 70)
print("🧪 Testing Qwen 2.5-3B CT2 Summarization with English Text")
print("=" * 70)

# Test 1: Simple English paragraph
print("\n📝 Test 1: Basic English Paragraph")
print("-" * 70)

english_text = """
The development team met today to discuss the progress of the mobile app project. 
The backend API integration is now complete, and the team has successfully implemented 
the real-time transcription feature using faster-whisper. The frontend team reported 
that the UI is 80% complete and they expect to finish by next week. We also discussed 
deploying the application to production, and decided to use Cloudflare R2 for file 
storage. The QA team will begin testing next Monday. Everyone agreed that the project 
is on track for the end-of-month deadline.
"""

print(f"Original text: {len(english_text.split())} words")
print(f"Preview: {english_text[:150]}...\n")

try:
    result = summarize_text(
        text=english_text,
        device="cuda",  # Use GPU
        max_length=150,
        min_length=30
    )
    
    print("✅ Summary generated!")
    print(f"\n📄 Summary ({len(result['summary'].split())} words):")
    print(result['summary'])
    print(f"\n📊 Compression: {len(result['summary'].split())}/{result['original_length']} words ({(1 - len(result['summary'].split()) / result['original_length']) * 100:.1f}% reduction)")
    
except Exception as e:
    print(f"❌ Error: {e}")

# Test 2: Multiple meeting segments (like your real use case)
print("\n" + "=" * 70)
print("📝 Test 2: Multiple Meeting Segments (10 chunks)")
print("-" * 70)

meeting_chunks = [
    {"english_translation": "Good morning everyone. Let's start today's standup meeting."},
    {"english_translation": "The backend team has completed the API endpoints for user authentication."},
    {"english_translation": "We integrated JWT tokens and refresh token functionality."},
    {"english_translation": "The mobile team is working on the voice recording feature with VAD."},
    {"english_translation": "We're using silero VAD to detect speech and filter out silence."},
    {"english_translation": "The transcription service with faster-whisper is now live."},
    {"english_translation": "We achieved 95% accuracy on Tagalog and English mixed speech."},
    {"english_translation": "Next week we'll deploy to staging for QA testing."},
    {"english_translation": "The design team shared new mockups for the session history screen."},
    {"english_translation": "Everyone agreed the new design looks great. Meeting adjourned."},
]

print(f"Number of segments: {len(meeting_chunks)}")
print("Segments preview:")
for i, chunk in enumerate(meeting_chunks[:3], 1):
    print(f"  {i}. {chunk['english_translation'][:60]}...")

try:
    result = summarize_transcriptions(
        transcriptions=meeting_chunks,
        device="cuda",
        max_length=200,
        min_length=50
    )
    
    print("\n✅ Summary generated!")
    print(f"\n📄 Summary:")
    print(result['summary'])
    print(f"\n📊 Stats:")
    print(f"  - Chunks: {result['chunk_count']}")
    print(f"  - Original: {result['original_length']} words")
    print(f"  - Summary: {len(result['summary'].split())} words")
    print(f"  - Compression: {(1 - len(result['summary'].split()) / result['original_length']) * 100:.1f}% reduction")
    
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 70)
print("✅ Testing Complete!")
print("=" * 70)
