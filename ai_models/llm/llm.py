from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

# Global model cache
_llm_cache = {}

def get_llm(model_name: str = "Qwen/Qwen2.5-1.5B-Instruct", device: str = "auto"):
    """
    Loads a small LLM for Taglish translation.
    Uses caching to avoid reloading the same model.
    
    Args:
        model_name: Model name (default: Qwen2.5-1.5B for fast inference, no auth required)
        device: "cpu", "cuda", or "auto"
    
    Returns:
        tuple: (model, tokenizer, device)
    """
    cache_key = f"{model_name}_{device}"
    
    if cache_key not in _llm_cache:
        try:
            # Auto-detect device if not specified
            if device == "auto":
                device = "cuda" if torch.cuda.is_available() else "cpu"
            
            # Load tokenizer and model
            tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
            model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float16 if device == "cuda" else torch.float32,
                trust_remote_code=True
            )
            model = model.to(device)
            model.eval()
            
            _llm_cache[cache_key] = (model, tokenizer, device)
        except Exception as e:
            raise RuntimeError(f"Failed to load LLM '{model_name}': {e}")
    
    return _llm_cache[cache_key]

def translate_taglish_to_english(
    text: str,
    model_name: str = "Qwen/Qwen2.5-1.5B-Instruct",
    device: str = "auto",
    max_new_tokens: int = 256
) -> dict:
    """
    Translates Taglish (mixed Tagalog-English) text to pure English using LLM.
    Better for code-switched speech than mBART.
    
    Args:
        text: Taglish text to translate
        model_name: Model name or path
        device: "cpu", "cuda", or "auto"
        max_new_tokens: Maximum tokens to generate
    
    Returns:
        dict with 'translated_text', 'model_used'
    """
    if not text or not text.strip():
        return {
            "translated_text": "",
            "model_used": model_name
        }
    
    try:
        # Load model and tokenizer
        model, tokenizer, device_used = get_llm(model_name, device)
        
        # Create prompt for Taglish translation (Qwen2.5 format)
        prompt = f"""<|im_start|>system
You are a translator specializing in Taglish (mixed Tagalog and English). Translate the following text to pure English. Keep the meaning accurate and natural.<|im_end|>
<|im_start|>user
Translate this to English: {text}<|im_end|>
<|im_start|>assistant
"""
        
        # Tokenize input
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
        inputs = {k: v.to(device_used) for k, v in inputs.items()}
        
        # Generate translation
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,  # Deterministic for consistency
                pad_token_id=tokenizer.eos_token_id
            )
        
        # Decode translation
        full_output = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Extract only the assistant's response
        if "<|im_start|>assistant" in full_output:
            translated_text = full_output.split("<|im_start|>assistant")[-1].strip()
            translated_text = translated_text.split("<|im_end|>")[0].strip()
        else:
            translated_text = full_output.strip()
        
        return {
            "translated_text": translated_text,
            "model_used": model_name
        }
    
    except Exception as e:
        raise RuntimeError(f"LLM translation failed: {e}")

def translate_taglish_batch(
    texts: list,
    model_name: str = "Qwen/Qwen2.5-1.5B-Instruct",
    device: str = "auto",
    max_new_tokens: int = 256
) -> list:
    """
    Translates multiple Taglish texts to English.
    
    Args:
        texts: List of Taglish texts
        model_name: Model name or path
        device: "cpu", "cuda", or "auto"
        max_new_tokens: Maximum tokens per translation
    
    Returns:
        list of translated texts
    """
    if not texts:
        return []
    
    results = []
    for text in texts:
        result = translate_taglish_to_english(
            text=text,
            model_name=model_name,
            device=device,
            max_new_tokens=max_new_tokens
        )
        results.append(result["translated_text"])
    
    return results
