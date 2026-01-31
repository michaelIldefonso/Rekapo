from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
import torch
import sys
import re
from pathlib import Path

# Add parent directory to path for preprocessing imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import preprocessing pipeline
try:
    from ai_models.preprocessing import preprocess_taglish_text
    PREPROCESSING_AVAILABLE = True
except ImportError:
    PREPROCESSING_AVAILABLE = False
    print("Warning: Taglish preprocessing not available. Install required dependencies.")

# Global model cache for reuse
_translator_cache = {}

def post_process_translation(translated: str, original: str) -> str:
    """
    Post-process NLLB translation output for better quality.
    Cleans up common issues: redundancy, capitalization, hallucinations.
    
    Args:
        translated: NLLB output translation
        original: Original input text
    
    Returns:
        Cleaned translation
    """
    if not translated or not translated.strip():
        return translated
    
    # Remove common prefixes that NLLB might add
    unwanted_prefixes = [
        "Translation:", "English translation:", "Translation is:",
        "[Translation]", "English:", "Output:", "Result:"
    ]
    for prefix in unwanted_prefixes:
        if translated.lower().startswith(prefix.lower()):
            translated = translated[len(prefix):].strip()
            if translated and translated[0] in [':', '-']:
                translated = translated[1:].strip()
    
    # Remove quotes wrapping entire translation
    if (translated.startswith('"') and translated.endswith('"')) or \
       (translated.startswith("'") and translated.endswith("'")):
        translated = translated[1:-1].strip()
    
    # Fix common NLLB over-correction issues
    # NLLB sometimes repeats words or adds filler
    words = translated.split()
    if len(words) > 2:
        # Remove immediate consecutive duplicates
        cleaned_words = [words[0]]
        for i in range(1, len(words)):
            if words[i].lower() != words[i-1].lower():
                cleaned_words.append(words[i])
        translated = " ".join(cleaned_words)
    
    # Preserve capitalization of proper nouns from original
    original_words = original.split()
    translated_words = translated.split()
    
    # Simple heuristic: if original word was capitalized (not at start), keep it
    for orig_word in original_words:
        if orig_word and orig_word[0].isupper():
            # Find similar word in translation and capitalize
            orig_clean = re.sub(r'[^\w]', '', orig_word.lower())
            for i, trans_word in enumerate(translated_words):
                trans_clean = re.sub(r'[^\w]', '', trans_word.lower())
                if orig_clean == trans_clean or orig_word == trans_word:
                    # Preserve original capitalization
                    translated_words[i] = orig_word
                    break
    
    translated = " ".join(translated_words)
    
    # Remove trailing/leading whitespace and normalize spaces
    translated = re.sub(r'\s+', ' ', translated).strip()
    
    # Ensure first letter is capitalized
    if translated and translated[0].islower():
        translated = translated[0].upper() + translated[1:]
    
    # Check if translation is actually in English (basic heuristic)
    # If it looks like it wasn't translated, return original
    if len(translated) > 0:
        # Count Latin alphabet characters
        latin_chars = sum(1 for c in translated if c.isalpha() and ord(c) < 128)
        total_chars = sum(1 for c in translated if c.isalpha())
        
        if total_chars > 0 and latin_chars / total_chars < 0.8:
            # Likely not properly translated (too many non-Latin chars)
            # Return original as fallback
            return original
    
    return translated

def get_translator(model_name: str = "facebook/nllb-200-1.3B", device: str = "auto"):
    """
    Loads the NLLB-200 translation model.
    Uses caching to avoid reloading the same model.
    
    Args:
        model_name: Model name or path (default: NLLB-200-1.3B)
        device: "cpu", "cuda", or "auto" (auto-detects)
    
    Returns:
        tuple: (model, tokenizer, device)
    """
    cache_key = f"{model_name}_{device}"
    
    if cache_key not in _translator_cache:
        try:
            # Auto-detect device if not specified
            if device == "auto":
                device = "cuda" if torch.cuda.is_available() else "cpu"
            
            # Load tokenizer and model
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
            model = model.to(device)
            
            _translator_cache[cache_key] = (model, tokenizer, device)
            print(f"✅ Loaded NLLB-200-1.3B translation model on {device}")
        except Exception as e:
            raise RuntimeError(f"Failed to load translation model '{model_name}': {e}")
    
    return _translator_cache[cache_key]

def translate_text(
    text: str,
    source_lang: str = "tgl_Latn",  # Tagalog
    target_lang: str = "eng_Latn",  # English
    model_name: str = "facebook/nllb-200-1.3B",
    device: str = "auto",
    max_length: int = 512,
    num_beams: int = 5,
    use_preprocessing: bool = True
) -> dict:
    """
    Translates text from source language to target language using NLLB-200.
    Applies advanced preprocessing for Taglish to English translation.
    
    Args:
        text: Text to translate
        source_lang: Source language code (e.g., 'tgl_Latn' for Tagalog, 'eng_Latn' for English)
        target_lang: Target language code (e.g., 'eng_Latn' for English, 'tgl_Latn' for Tagalog)
        model_name: Model name or path
        device: "cpu", "cuda", or "auto"
        max_length: Maximum length of generated translation
        num_beams: Number of beams for beam search (higher = better quality but slower)
        use_preprocessing: Apply phonetic correction and dictionary lookup (for Taglish only)
    
    Returns:
        dict with 'translated_text', 'source_lang', 'target_lang', 'preprocessing_info' (optional)
    
    Supported language codes (NLLB-200 format):
        - English: eng_Latn
        - Tagalog: tgl_Latn (Filipino)
        - Spanish: spa_Latn
        - Chinese: zho_Hans
        - Japanese: jpn_Jpan
        - Korean: kor_Hang
        And 194 more languages...
    """
    if not text or not text.strip():
        return {
            "translated_text": "",
            "source_lang": source_lang,
            "target_lang": target_lang,
            "preprocessing_info": None
        }
    
    # Apply preprocessing for Taglish to English translation
    preprocessing_result = None
    input_text = text
    
    if (use_preprocessing and PREPROCESSING_AVAILABLE and 
        source_lang == "tgl_Latn" and target_lang == "eng_Latn"):
        try:
            preprocessing_result = preprocess_taglish_text(text)
            # Use corrected text for translation
            input_text = preprocessing_result["corrected_text"]
        except Exception as e:
            print(f"Preprocessing failed, using original text: {e}")
            input_text = text
    
    try:
        # Load model and tokenizer
        model, tokenizer, device_used = get_translator(model_name, device)
        
        # Set source and target languages for NLLB
        tokenizer.src_lang = source_lang
        
        # Tokenize input text
        encoded = tokenizer(input_text, return_tensors="pt", padding=True, truncation=True, max_length=max_length)
        encoded = {k: v.to(device_used) for k, v in encoded.items()}
        
        # Get target language token ID
        forced_bos_token_id = tokenizer.convert_tokens_to_ids(target_lang)
        
        # Generate translation
        generated_tokens = model.generate(
            **encoded,
            forced_bos_token_id=forced_bos_token_id,
            max_length=max_length,
            num_beams=num_beams,
            early_stopping=True
        )
        
        # Decode translation
        translated_text = tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)[0]
        
        # Post-process translation for better quality
        translated_text = post_process_translation(translated_text.strip(), text)
        
        result = {
            "translated_text": translated_text,
            "source_lang": source_lang,
            "target_lang": target_lang
        }
        
        # Add preprocessing info if available
        if preprocessing_result:
            result["preprocessing_info"] = {
                "original_text": preprocessing_result["original_text"],
                "corrected_text": preprocessing_result["corrected_text"],
                "context_score": preprocessing_result["context_score"]
            }
        
        return result
    
    except Exception as e:
        raise RuntimeError(f"Translation failed: {e}")

def translate_segments(
    segments: list,
    source_lang: str = "tgl_Latn",
    target_lang: str = "eng_Latn",
    model_name: str = "facebook/nllb-200-1.3B",
    device: str = "auto",
    max_length: int = 512,
    num_beams: int = 5,
    use_preprocessing: bool = True
) -> list:
    """
    Translates multiple text segments while preserving timestamps.
    Applies preprocessing for Taglish to English translation.
    
    Args:
        segments: List of dicts with 'start', 'end', 'text' keys
        source_lang: Source language code (NLLB format, e.g., 'tgl_Latn')
        target_lang: Target language code (NLLB format, e.g., 'eng_Latn')
        model_name: Model name or path
        device: "cpu", "cuda", or "auto"
        max_length: Maximum length of generated translation
        num_beams: Number of beams for beam search
        use_preprocessing: Apply phonetic correction and dictionary lookup (for Taglish only)
    
    Returns:
        list of dicts with 'start', 'end', 'text', 'translated_text', 'preprocessing_info' (optional)
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
                    "translated_text": "",
                    "preprocessing_info": None
                })
                continue
            
            # Apply preprocessing for Taglish to English
            preprocessing_result = None
            input_text = segment["text"]
            
            if (use_preprocessing and PREPROCESSING_AVAILABLE and 
                source_lang == "tgl_Latn" and target_lang == "eng_Latn"):
                try:
                    preprocessing_result = preprocess_taglish_text(segment["text"])
                    input_text = preprocessing_result["corrected_text"]
                except Exception as e:
                    print(f"Preprocessing failed for segment, using original: {e}")
                    input_text = segment["text"]
            
            # Tokenize and translate
            encoded = tokenizer(
                input_text, 
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
            
            # Post-process translation
            translated_text = post_process_translation(translated_text.strip(), segment["text"])
            
            result = {
                **segment,
                "translated_text": translated_text
            }
            
            # Add preprocessing info if available
            if preprocessing_result:
                result["preprocessing_info"] = {
                    "corrected_text": preprocessing_result["corrected_text"],
                    "context_score": preprocessing_result["context_score"]
                }
            
            translated_segments.append(result)
        
        return translated_segments
    
    except Exception as e:
        raise RuntimeError(f"Segment translation failed: {e}")

def auto_detect_and_translate(
    text: str,
    detected_lang: str,
    model_name: str = "facebook/nllb-200-1.3B",
    device: str = "auto",
    max_length: int = 512,
    num_beams: int = 5,
    use_preprocessing: bool = True
) -> dict:
    """
    Automatically translates text to English if not already in English.
    Maps Whisper language codes to NLLB-200 language codes.
    Applies preprocessing for Taglish text.
    
    Args:
        text: Text to translate
        detected_lang: Language code from Whisper (e.g., 'tl', 'en', 'es')
        model_name: Model name or path
        device: "cpu", "cuda", or "auto"
        max_length: Maximum length of generated translation
        num_beams: Number of beams for beam search
        use_preprocessing: Apply phonetic correction and dictionary lookup (for Taglish only)
    
    Returns:
        dict with 'translated_text', 'source_lang', 'target_lang', 'is_english', 'preprocessing_info' (optional)
    """
    # Map Whisper language codes to NLLB-200 language codes
    # Restricted to Tagalog and English only for Taglish support
    lang_map = {
        'tl': 'tgl_Latn',  # Tagalog/Filipino
        'en': 'eng_Latn',  # English
    }
    
    # Check if already in English
    if detected_lang == 'en':
        return {
            "translated_text": text,
            "source_lang": "eng_Latn",
            "target_lang": "eng_Latn",
            "is_english": True,
            "preprocessing_info": None
        }
    
    # Get NLLB-200 language code
    source_lang = lang_map.get(detected_lang, 'tgl_Latn')  # Default to Tagalog if unknown
    
    # Translate to English
    result = translate_text(
        text=text,
        source_lang=source_lang,
        target_lang="eng_Latn",
        model_name=model_name,
        device=device,
        max_length=max_length,
        num_beams=num_beams,
        use_preprocessing=use_preprocessing
    )
    
    result["is_english"] = False
    return result
