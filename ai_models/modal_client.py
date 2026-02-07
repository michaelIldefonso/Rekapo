"""
Modal client for calling deployed AI models
Provides same interface as local inference files but calls Modal serverless functions
"""
from typing import Optional, List, Dict, Any
import modal

# Lazy-load Modal functions (connect only when needed)
_transcribe_fn = None
_translate_fn = None
_summarize_fn = None

def _get_modal_functions():
    """Connect to Modal functions on first use"""
    global _transcribe_fn, _translate_fn, _summarize_fn
    
    if _transcribe_fn is None:
        print("🔗 Connecting to Modal deployed functions...")
        try:
            # Look up the deployed app
            app = modal.App.lookup("rekapo-ai")
            
            # Get function handles from the app
            _transcribe_fn = modal.Function.from_name("rekapo-ai", "transcribe_audio")
            _translate_fn = modal.Function.from_name("rekapo-ai", "translate_text")
            _summarize_fn = modal.Function.from_name("rekapo-ai", "summarize_text")
            
            print("✅ Modal functions connected successfully!")
        except Exception as e:
            print(f"⚠️  Modal connection failed: {e}")
            print("   Make sure Modal token is set and app is deployed")
            raise
    
    return _transcribe_fn, _translate_fn, _summarize_fn


def transcribe_audio_file(
    audio_path: str,
    model_name_or_path: Optional[str] = None,
    language: Optional[str] = "tl",
    device: str = "cuda",
    vad_filter: bool = True,
    beam_size: int = 5,
    temperature: float = 0.2,
    repetition_penalty: float = 1.05,
    no_repeat_ngram_size: int = 3,
    initial_prompt: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Transcribe audio using Modal-deployed Whisper model
    
    Args:
        audio_path: Path to audio file
        language: Language code (default: 'tl' for Tagalog)
        Other args match local inference but are handled by Modal
    
    Returns:
        dict with transcription results
    """
    # Get Modal functions (lazy load)
    transcribe_fn, _, _ = _get_modal_functions()
    
    # Read audio file
    with open(audio_path, "rb") as f:
        audio_bytes = f.read()
    
    # Call Modal function
    result = transcribe_fn.remote(audio_bytes, language=language)
    
    # Format to match local inference return structure
    return {
        "text": result["segments"][0]["text"] if result["segments"] else "",
        "language": result["language"],
        "language_probability": 0.95,  # Modal doesn't return this, use default
        "duration": result["duration"],
        "segments": result["segments"]
    }


def translate_text(
    text: str,
    source_lang: str = "tgl_Latn",
    target_lang: str = "eng_Latn",
    device: str = "auto",
    use_preprocessing: bool = False,
    **kwargs
) -> Dict[str, str]:
    """
    Translate text using Modal-deployed NLLB model
    
    Args:
        text: Text to translate
        source_lang: Source language code (NLLB format)
        target_lang: Target language code (NLLB format)
    
    Returns:
        dict with translated text
    """
    # Get Modal functions (lazy load)
    _, translate_fn, _ = _get_modal_functions()
    
    # Call Modal function
    result = translate_fn.remote(text, source_lang=source_lang, target_lang=target_lang)
    
    return {
        "translated_text": result["translated_text"]
    }


def summarize_transcriptions(
    transcriptions: List[Dict[str, Any]],
    device: str = "cuda",
    max_length: int = 300,
    min_length: int = 75,
    **kwargs
) -> Dict[str, Any]:
    """
    Summarize transcriptions using Modal-deployed Qwen model
    
    Args:
        transcriptions: List of transcription dicts with 'english_translation' field
        max_length: Maximum summary length
        min_length: Minimum summary length
    
    Returns:
        dict with summary and chunk count
    """
    # Get Modal functions (lazy load)
    _, _, summarize_fn = _get_modal_functions()
    
    # Combine all English translations
    combined_text = " ".join([
        t.get("english_translation", "") for t in transcriptions
    ])
    
    # Call Modal function
    result = summarize_fn.remote(
        combined_text,
        max_length=max_length,
        min_length=min_length
    )
    
    return {
        "summary": result["summary"],
        "chunk_count": len(transcriptions)
    }


def clear_summarizer_cache():
    """
    No-op for Modal (GPU memory managed automatically)
    Kept for compatibility with local inference interface
    """
    pass  # Modal handles GPU memory automatically
