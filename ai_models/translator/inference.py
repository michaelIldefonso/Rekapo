from transformers import MBartForConditionalGeneration, MBart50TokenizerFast
import torch

# Global model cache for reuse
_translator_cache = {}

def get_translator(model_name: str = "facebook/mbart-large-50-many-to-many-mmt", device: str = "auto"):
    """
    Loads the mBART translation model.
    Uses caching to avoid reloading the same model.
    
    Args:
        model_name: Model name or path (default: mBART-50 many-to-many)
        device: "cpu", "cuda", or "auto" (auto-detects)
    
    Returns:
        tuple: (model, tokenizer)
    """
    cache_key = f"{model_name}_{device}"
    
    if cache_key not in _translator_cache:
        try:
            # Auto-detect device if not specified
            if device == "auto":
                device = "cuda" if torch.cuda.is_available() else "cpu"
            
            # Load tokenizer and model
            tokenizer = MBart50TokenizerFast.from_pretrained(model_name)
            model = MBartForConditionalGeneration.from_pretrained(model_name)
            model = model.to(device)
            
            _translator_cache[cache_key] = (model, tokenizer, device)
        except Exception as e:
            raise RuntimeError(f"Failed to load translation model '{model_name}': {e}")
    
    return _translator_cache[cache_key]

def translate_text(
    text: str,
    source_lang: str = "tl_XX",  # Tagalog
    target_lang: str = "en_XX",  # English
    model_name: str = "facebook/mbart-large-50-many-to-many-mmt",
    device: str = "auto",
    max_length: int = 512,
    num_beams: int = 5
) -> dict:
    """
    Translates text from source language to target language using mBART.
    
    Args:
        text: Text to translate
        source_lang: Source language code (e.g., 'tl_XX' for Tagalog, 'en_XX' for English)
        target_lang: Target language code (e.g., 'en_XX' for English, 'tl_XX' for Tagalog)
        model_name: Model name or path
        device: "cpu", "cuda", or "auto"
        max_length: Maximum length of generated translation
        num_beams: Number of beams for beam search (higher = better quality but slower)
    
    Returns:
        dict with 'translated_text', 'source_lang', 'target_lang'
    
    Supported language codes:
        - English: en_XX
        - Tagalog: tl_XX (Filipino)
        - Spanish: es_XX
        - Chinese: zh_CN
        - Japanese: ja_XX
        - Korean: ko_KR
        And many more...
    """
    if not text or not text.strip():
        return {
            "translated_text": "",
            "source_lang": source_lang,
            "target_lang": target_lang
        }
    
    try:
        # Load model and tokenizer
        model, tokenizer, device_used = get_translator(model_name, device)
        
        # Set source language
        tokenizer.src_lang = source_lang
        
        # Tokenize input text
        encoded = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=max_length)
        encoded = {k: v.to(device_used) for k, v in encoded.items()}
        
        # Generate translation
        generated_tokens = model.generate(
            **encoded,
            forced_bos_token_id=tokenizer.lang_code_to_id[target_lang],
            max_length=max_length,
            num_beams=num_beams,
            early_stopping=True
        )
        
        # Decode translation
        translated_text = tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)[0]
        
        return {
            "translated_text": translated_text.strip(),
            "source_lang": source_lang,
            "target_lang": target_lang
        }
    
    except Exception as e:
        raise RuntimeError(f"Translation failed: {e}")

def translate_segments(
    segments: list,
    source_lang: str = "tl_XX",
    target_lang: str = "en_XX",
    model_name: str = "facebook/mbart-large-50-many-to-many-mmt",
    device: str = "auto",
    max_length: int = 512,
    num_beams: int = 5
) -> list:
    """
    Translates multiple text segments while preserving timestamps.
    
    Args:
        segments: List of dicts with 'start', 'end', 'text' keys
        source_lang: Source language code
        target_lang: Target language code
        model_name: Model name or path
        device: "cpu", "cuda", or "auto"
        max_length: Maximum length of generated translation
        num_beams: Number of beams for beam search
    
    Returns:
        list of dicts with 'start', 'end', 'text', 'translated_text'
    """
    if not segments:
        return []
    
    try:
        # Load model once for all segments
        model, tokenizer, device_used = get_translator(model_name, device)
        tokenizer.src_lang = source_lang
        
        translated_segments = []
        
        for segment in segments:
            if not segment.get("text") or not segment["text"].strip():
                translated_segments.append({
                    **segment,
                    "translated_text": ""
                })
                continue
            
            # Tokenize and translate
            encoded = tokenizer(
                segment["text"], 
                return_tensors="pt", 
                padding=True, 
                truncation=True, 
                max_length=max_length
            )
            encoded = {k: v.to(device_used) for k, v in encoded.items()}
            
            generated_tokens = model.generate(
                **encoded,
                forced_bos_token_id=tokenizer.lang_code_to_id[target_lang],
                max_length=max_length,
                num_beams=num_beams,
                early_stopping=True
            )
            
            translated_text = tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)[0]
            
            translated_segments.append({
                **segment,
                "translated_text": translated_text.strip()
            })
        
        return translated_segments
    
    except Exception as e:
        raise RuntimeError(f"Segment translation failed: {e}")

def auto_detect_and_translate(
    text: str,
    detected_lang: str,
    model_name: str = "facebook/mbart-large-50-many-to-many-mmt",
    device: str = "auto",
    max_length: int = 512,
    num_beams: int = 5
) -> dict:
    """
    Automatically translates text to English if not already in English.
    Maps Whisper language codes to mBART language codes.
    
    Args:
        text: Text to translate
        detected_lang: Language code from Whisper (e.g., 'tl', 'en', 'es')
        model_name: Model name or path
        device: "cpu", "cuda", or "auto"
        max_length: Maximum length of generated translation
        num_beams: Number of beams for beam search
    
    Returns:
        dict with 'translated_text', 'source_lang', 'target_lang', 'is_english'
    """
    # Map Whisper language codes to mBART language codes
    # Restricted to Tagalog and English only for Taglish support
    lang_map = {
        'tl': 'tl_XX',  # Tagalog/Filipino
        'en': 'en_XX',  # English
    }
    
    # Check if already in English
    if detected_lang == 'en':
        return {
            "translated_text": text,
            "source_lang": "en_XX",
            "target_lang": "en_XX",
            "is_english": True
        }
    
    # Get mBART language code
    source_lang = lang_map.get(detected_lang, 'tl_XX')  # Default to Tagalog if unknown
    
    # Translate to English
    result = translate_text(
        text=text,
        source_lang=source_lang,
        target_lang="en_XX",
        model_name=model_name,
        device=device,
        max_length=max_length,
        num_beams=num_beams
    )
    
    result["is_english"] = False
    return result
