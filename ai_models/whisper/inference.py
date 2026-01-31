from faster_whisper import WhisperModel
import os
import re
from pathlib import Path
from config.config import WHISPER_MODEL_PATH

# Global model instance for reuse
_model_cache = {}

def is_hallucination(text: str, no_speech_prob: float = 0.0) -> bool:
    """
    Detect if a transcription is likely a hallucination.
    
    Whisper commonly hallucinates phrases when there's no speech:
    - "You", "Thank you", "Thanks for watching"
    - Short meaningless phrases
    - High no_speech_prob indicates silence
    
    Args:
        text: Transcribed text
        no_speech_prob: Probability of no speech (0.0-1.0)
    
    Returns:
        True if likely hallucination, False otherwise
    """
    if not text or not text.strip():
        return True
    
    text_lower = text.strip().lower()
    
    # High no_speech probability = likely hallucination
    if no_speech_prob > 0.6:
        return True
    
    # Common Whisper hallucinations
    hallucination_phrases = [
        "you",
        "thank you",
        "thanks",
        "thank you for watching",
        "thanks for watching",
        "bye",
        "goodbye",
        "...",
        ".",
        "?",
        "!"
    ]
    
    # Check if text exactly matches common hallucinations
    if text_lower in hallucination_phrases:
        return True
    
    # Very short text (1-2 chars) is likely noise
    if len(text_lower) <= 2:
        return True
    
    return False

def clean_transcription_text(text: str) -> str:
    """
    Clean transcription text to only include valid characters.
    Removes phonetic symbols, random Unicode characters, and other noise.
    
    Keeps:
    - English/Tagalog alphabet (A-Z, a-z)
    - Numbers (0-9)
    - Common punctuation (.,!?;:'"()-—)
    - Apostrophes and hyphens
    - Spaces and newlines
    
    Args:
        text: Raw transcription text
    
    Returns:
        Cleaned text with only valid characters
    """
    if not text:
        return text
    
    # Define allowed characters (Latin alphabet + common punctuation)
    # This covers both English and Tagalog (which uses Latin script)
    allowed_pattern = r'[A-Za-z0-9\s\.,!?\;:\'\"\(\)\-–—/\n\r]'
    
    # Keep only allowed characters
    cleaned = ''.join(char if re.match(allowed_pattern, char) else ' ' for char in text)
    
    # Clean up multiple spaces
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    # Remove leading/trailing whitespace
    cleaned = cleaned.strip()
    
    return cleaned

def get_transcriber(model_name_or_path: str = None, device: str = "auto", compute_type: str = "auto"):
    """
    Loads the faster-whisper model.
    Uses caching to avoid reloading the same model.
    
    Args:
        model_name_or_path: Model size (tiny, base, small, medium, large-v2, large-v3), URL, or path
        device: "cpu", "cuda", or "auto" (auto-detects)
        compute_type: "int8", "float16", "float32", or "auto"
    """
    # Use configured model if no path specified
    if model_name_or_path is None:
        model_name_or_path = WHISPER_MODEL_PATH
    
    cache_key = f"{model_name_or_path}_{device}_{compute_type}"
    
    if cache_key not in _model_cache:
        try:
            # Auto-detect device if not specified
            if device == "auto":
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"
            
            # Auto-select compute type based on device
            if compute_type == "auto":
                compute_type = "float16" if device == "cuda" else "int8"
            
            _model_cache[cache_key] = WhisperModel(
                model_name_or_path,
                device=device,
                compute_type=compute_type
            )
        except Exception as e:
            raise RuntimeError(f"Failed to load model '{model_name_or_path}': {e}")
    
    return _model_cache[cache_key]

def transcribe_audio_file(
    audio_path: str,
    model_name_or_path: str = None,
    language: str = None,
    device: str = "auto",
    compute_type: str = "auto",
    beam_size: int = 5,
    vad_filter: bool = True,
    temperature: float = 0.2,
    repetition_penalty: float = 1.1,
    no_repeat_ngram_size: int = 3,
    compression_ratio_threshold: float = 2.4,
    condition_on_previous_text: bool = True,
    initial_prompt: str = None
) -> dict:
    """
    Transcribes an audio file using faster-whisper.
    Returns dict with 'text' and optional 'segments' for detailed info.
    
    Args:
        audio_path: Path to audio file
        model_name_or_path: Model size, URL, or local path (defaults to WHISPER_MODEL_PATH from .env)
        language: Language code (e.g., 'en', 'es', 'tl') or None for auto-detection
        device: "cpu", "cuda", or "auto"
        compute_type: "int8", "float16", "float32", or "auto"
        beam_size: Beam size for decoding (higher = more accurate but slower)
        vad_filter: Enable Voice Activity Detection to filter out non-speech
        temperature: Sampling temperature (lower = more deterministic, default 0.2)
        repetition_penalty: Penalty for repeated tokens (default 1.1)
            Note: Set lower (1.0-1.05) for Tagalog to preserve reduplication patterns
        no_repeat_ngram_size: Prevent repeating n-grams of this size (default 3)
            Note: Safe for Tagalog - only blocks 3+ word repetitions, preserves "bili-bili"
        compression_ratio_threshold: Threshold for detecting low-quality outputs (default 2.4)
        condition_on_previous_text: Use previous text as context (default True)
        initial_prompt: Optional text to guide Whisper's transcription style and improve accuracy
    """
    if not audio_path:
        raise ValueError("audio_path must be provided and non-empty.")
    
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    # Load the model
    try:
        model = get_transcriber(model_name_or_path, device, compute_type)
    except Exception as e:
        raise RuntimeError(f"Error initializing model: {e}")
    
    # Adjust repetition penalty for Tagalog to preserve legitimate reduplication
    if language == "tl" and repetition_penalty > 1.05:
        print(f"Note: Reducing repetition_penalty from {repetition_penalty} to 1.05 for Tagalog (preserves reduplication)")
        repetition_penalty = 1.05

    # Transcribe with improved generation parameters
    try:
        # Build transcribe kwargs
        transcribe_kwargs = {
            "language": language,
            "beam_size": beam_size,
            "vad_filter": vad_filter,
            "temperature": temperature,
            "repetition_penalty": repetition_penalty,
            "no_repeat_ngram_size": no_repeat_ngram_size,
            "compression_ratio_threshold": compression_ratio_threshold,
            "condition_on_previous_text": condition_on_previous_text
        }
        
        # Add initial_prompt if provided (guides Whisper for better accuracy)
        if initial_prompt:
            transcribe_kwargs["initial_prompt"] = initial_prompt
        
        segments, info = model.transcribe(audio_path, **transcribe_kwargs)
        
        # Collect all segments and filter hallucinations
        all_segments = list(segments)
        
        # Filter out hallucinations using no_speech_prob
        valid_segments = []
        for seg in all_segments:
            # Get no_speech_prob (defaults to 0.0 if not available)
            no_speech_prob = getattr(seg, 'no_speech_prob', 0.0)
            
            # Skip if detected as hallucination
            if is_hallucination(seg.text, no_speech_prob):
                print(f"⚠️  Filtered hallucination: '{seg.text}' (no_speech_prob: {no_speech_prob:.2f})")
                continue
            
            valid_segments.append(seg)
        
        # Join text from valid segments only
        full_text = " ".join([segment.text for segment in valid_segments])
        
        # Clean transcription to remove phonetic symbols and unwanted characters
        full_text_cleaned = clean_transcription_text(full_text)
        cleaned_segments = [
            {
                "start": seg.start,
                "end": seg.end,
                "text": clean_transcription_text(seg.text),
                "no_speech_prob": getattr(seg, 'no_speech_prob', 0.0)
            }
            for seg in valid_segments
        ]
        
        return {
            "text": full_text_cleaned,
            "language": info.language,
            "language_probability": info.language_probability,
            "duration": info.duration,
            "segments": cleaned_segments
        }
    except Exception as e:
        raise RuntimeError(f"Transcription failed: {e}")
