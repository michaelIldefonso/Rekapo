from transformers import pipeline
import torch

# Global summarizer cache
_summarizer_cache = {}

def get_summarizer(model_name: str = "facebook/bart-large-cnn", device: str = "auto"):
    """
    Loads the summarization model.
    Uses caching to avoid reloading the same model.
    
    Args:
        model_name: Model name or path (default: BART for summarization)
        device: "cpu", "cuda", or "auto" (auto-detects)
    
    Returns:
        summarization pipeline
    """
    cache_key = f"{model_name}_{device}"
    
    if cache_key not in _summarizer_cache:
        try:
            # Auto-detect device if not specified
            if device == "auto":
                device = 0 if torch.cuda.is_available() else -1  # 0 for GPU, -1 for CPU
            elif device == "cuda":
                device = 0
            else:
                device = -1
            
            # Load summarization pipeline
            summarizer = pipeline(
                "summarization",
                model=model_name,
                device=device
            )
            
            _summarizer_cache[cache_key] = summarizer
        except Exception as e:
            raise RuntimeError(f"Failed to load summarization model '{model_name}': {e}")
    
    return _summarizer_cache[cache_key]

def summarize_text(
    text: str,
    model_name: str = "facebook/bart-large-cnn",
    device: str = "auto",
    max_length: int = 150,
    min_length: int = 50,
    do_sample: bool = False
) -> dict:
    """
    Summarizes text using BART or other summarization models.
    
    Args:
        text: Text to summarize
        model_name: Model name or path
        device: "cpu", "cuda", or "auto"
        max_length: Maximum length of summary
        min_length: Minimum length of summary
        do_sample: Whether to use sampling (False = deterministic)
    
    Returns:
        dict with 'summary' and 'original_length'
    """
    if not text or not text.strip():
        return {
            "summary": "",
            "original_length": 0
        }
    
    try:
        # Load summarizer
        summarizer = get_summarizer(model_name, device)
        
        # Summarize
        result = summarizer(
            text,
            max_length=max_length,
            min_length=min_length,
            do_sample=do_sample,
            truncation=True
        )
        
        summary = result[0]["summary_text"]
        
        return {
            "summary": summary.strip(),
            "original_length": len(text.split())
        }
    
    except Exception as e:
        raise RuntimeError(f"Summarization failed: {e}")

def summarize_transcriptions(
    transcriptions: list,
    model_name: str = "facebook/bart-large-cnn",
    device: str = "auto",
    max_length: int = 200,
    min_length: int = 50
) -> dict:
    """
    Summarizes multiple transcription chunks into a coherent summary.
    
    Args:
        transcriptions: List of dicts with 'transcription' and 'english_translation'
        model_name: Model name or path
        device: "cpu", "cuda", or "auto"
        max_length: Maximum length of summary
        min_length: Minimum length of summary
    
    Returns:
        dict with 'summary', 'chunk_count', 'original_length'
    """
    if not transcriptions:
        return {
            "summary": "",
            "chunk_count": 0,
            "original_length": 0
        }
    
    try:
        # Combine all English translations
        combined_text = " ".join([
            t.get("english_translation", t.get("transcription", ""))
            for t in transcriptions
            if t.get("english_translation") or t.get("transcription")
        ])
        
        if not combined_text.strip():
            return {
                "summary": "",
                "chunk_count": len(transcriptions),
                "original_length": 0
            }
        
        # Summarize the combined text
        result = summarize_text(
            text=combined_text,
            model_name=model_name,
            device=device,
            max_length=max_length,
            min_length=min_length
        )
        
        return {
            "summary": result["summary"],
            "chunk_count": len(transcriptions),
            "original_length": result["original_length"]
        }
    
    except Exception as e:
        raise RuntimeError(f"Transcription summarization failed: {e}")

def summarize_meeting_segments(
    segments: list,
    model_name: str = "facebook/bart-large-cnn",
    device: str = "auto",
    max_length: int = 200,
    min_length: int = 50
) -> dict:
    """
    Summarizes meeting segments with timestamps and speaker information.
    
    Args:
        segments: List of segment dicts with timing and text info
        model_name: Model name or path
        device: "cpu", "cuda", or "auto"
        max_length: Maximum length of summary
        min_length: Minimum length of summary
    
    Returns:
        dict with 'summary', 'total_duration', 'segment_count'
    """
    if not segments:
        return {
            "summary": "",
            "total_duration": 0,
            "segment_count": 0
        }
    
    try:
        # Extract all text from segments
        texts = []
        total_duration = 0
        
        for segment in segments:
            if "english_translation" in segment and segment["english_translation"]:
                texts.append(segment["english_translation"])
            elif "transcription" in segment and segment["transcription"]:
                texts.append(segment["transcription"])
            
            if "duration" in segment:
                total_duration += segment["duration"]
        
        combined_text = " ".join(texts)
        
        if not combined_text.strip():
            return {
                "summary": "",
                "total_duration": total_duration,
                "segment_count": len(segments)
            }
        
        # Summarize
        result = summarize_text(
            text=combined_text,
            model_name=model_name,
            device=device,
            max_length=max_length,
            min_length=min_length
        )
        
        return {
            "summary": result["summary"],
            "total_duration": total_duration,
            "segment_count": len(segments)
        }
    
    except Exception as e:
        raise RuntimeError(f"Meeting segment summarization failed: {e}")
