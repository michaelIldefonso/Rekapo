from faster_whisper import WhisperModel
import os
from pathlib import Path
from config.config import WHISPER_MODEL_PATH

# Global model instance for reuse
_model_cache = {}

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
    vad_filter: bool = True
) -> dict:
    """
    Transcribes an audio file using faster-whisper.
    Returns dict with 'text' and optional 'segments' for detailed info.
    
    Args:
        audio_path: Path to audio file
        model_name_or_path: Model size, URL, or local path (defaults to WHISPER_MODEL_PATH from .env)
        language: Language code (e.g., 'en', 'es') or None for auto-detection
        device: "cpu", "cuda", or "auto"
        compute_type: "int8", "float16", "float32", or "auto"
        beam_size: Beam size for decoding (higher = more accurate but slower)
        vad_filter: Enable Voice Activity Detection to filter out non-speech
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

    # Transcribe
    try:
        segments, info = model.transcribe(
            audio_path,
            language=language,
            beam_size=beam_size,
            vad_filter=vad_filter
        )
        
        # Collect all segments
        all_segments = list(segments)
        full_text = " ".join([segment.text for segment in all_segments])
        
        return {
            "text": full_text.strip(),
            "language": info.language,
            "language_probability": info.language_probability,
            "duration": info.duration,
            "segments": [
                {
                    "start": seg.start,
                    "end": seg.end,
                    "text": seg.text
                }
                for seg in all_segments
            ]
        }
    except Exception as e:
        raise RuntimeError(f"Transcription failed: {e}")
