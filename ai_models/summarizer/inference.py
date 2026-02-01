from transformers import AutoTokenizer
import ctranslate2
import sys
from pathlib import Path

# Add parent directory to path for config imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config.config import SUMMARIZER_MODEL_PATH

# Global summarizer cache
_summarizer_cache = {}

def get_summarizer(model_name: str = None, device: str = "auto"):
    """
    Loads the CTranslate2 summarization model.
    Uses caching to avoid reloading the same model.
    
    Args:
        model_name: Model name or path (default: BART CT2 for summarization)
        device: "cpu", "cuda", or "auto" (auto-detects)
    
    Returns:
        tuple: (translator, tokenizer, device)
    """
    # Use configured model if no path specified
    if model_name is None:
        model_name = SUMMARIZER_MODEL_PATH
    
    cache_key = f"{model_name}_{device}"
    
    if cache_key not in _summarizer_cache:
        print(f"📦 Loading CTranslate2 summarization model: {model_name}")
        try:
            # Auto-detect device if not specified
            if device == "auto":
                device = "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
            
            device_name = "GPU" if device == "cuda" else "CPU"
            print(f"🖥️  Using device: {device_name}")
            
            # Load tokenizer (from the CT2 model directory)
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            
            # Load CTranslate2 model
            translator = ctranslate2.Translator(model_name, device=device)
            
            _summarizer_cache[cache_key] = (translator, tokenizer, device)
            print(f"✅ CTranslate2 summarization model loaded and cached")
        except Exception as e:
            print(f"❌ Failed to load summarization model: {e}")
            raise RuntimeError(f"Failed to load summarization model '{model_name}': {e}")
    else:
        print(f"♻️  Using cached summarization model: {model_name}")
    
    return _summarizer_cache[cache_key]

def summarize_text(
    text: str,
    model_name: str = None,
    device: str = "auto",
    max_length: int = 150,
    min_length: int = 50,
    beam_size: int = 4
) -> dict:
    """
    Summarizes text using BART CTranslate2 model.
    
    Args:
        text: Text to summarize
        model_name: Model name or path
        device: "cpu", "cuda", or "auto"
        max_length: Maximum length of summary
        min_length: Minimum length of summary
        beam_size: Number of beams for beam search
    
    Returns:
        dict with 'summary' and 'original_length'
    """
    if not text or not text.strip():
        print("⚠️  summarize_text: Empty text provided")
        return {
            "summary": "",
            "original_length": 0
        }
    
    try:
        print(f"🔧 Loading/getting summarizer model: {model_name}")
        # Load summarizer (CT2 translator and tokenizer)
        translator, tokenizer, device_used = get_summarizer(model_name, device)
        
        word_count = len(text.split())
        print(f"📝 Summarizing {word_count} words (max={max_length}, min={min_length})...")
        
        # Tokenize input text
        tokens = tokenizer.convert_ids_to_tokens(tokenizer.encode(text))
        
        # Generate summary using CTranslate2
        results = translator.translate_batch(
            [tokens],
            beam_size=beam_size,
            max_decoding_length=max_length,
            min_decoding_length=min_length
        )
        
        # Decode the summary
        summary_tokens = results[0].hypotheses[0]
        summary = tokenizer.decode(
            tokenizer.convert_tokens_to_ids(summary_tokens),
            skip_special_tokens=True
        )
        
        print(f"✅ summarize_text completed: {len(summary)} characters")
        
        return {
            "summary": summary.strip(),
            "original_length": word_count
        }
    
    except Exception as e:
        print(f"❌ Summarization failed in summarize_text: {e}")
        raise RuntimeError(f"Summarization failed: {e}")

def summarize_transcriptions(
    transcriptions: list,
    model_name: str = None,
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
    print(f"📝 summarize_transcriptions called with {len(transcriptions)} transcriptions")
    
    if not transcriptions:
        print("⚠️  No transcriptions to summarize (empty list)")
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
        
        print(f"📊 Combined text length: {len(combined_text)} characters, {len(combined_text.split())} words")
        
        if not combined_text.strip():
            print("⚠️  Combined text is empty after joining transcriptions")
            return {
                "summary": "",
                "chunk_count": len(transcriptions),
                "original_length": 0
            }
        
        print(f"🤖 Calling BART summarizer (max_length={max_length}, min_length={min_length})...")
        
        # Summarize the combined text
        result = summarize_text(
            text=combined_text,
            model_name=model_name,
            device=device,
            max_length=max_length,
            min_length=min_length
        )
        
        print(f"✅ Summary generated: {len(result['summary'])} characters")
        print(f"   Summary preview: {result['summary'][:150]}...")
        
        return {
            "summary": result["summary"],
            "chunk_count": len(transcriptions),
            "original_length": result["original_length"]
        }
    
    except Exception as e:
        print(f"❌ Transcription summarization failed: {e}")
        raise RuntimeError(f"Transcription summarization failed: {e}")

def summarize_meeting_segments(
    segments: list,
    model_name: str = None,
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
