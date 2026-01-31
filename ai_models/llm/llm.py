"""
Taglish to English Translation Module using Qwen LLM

Provides translation functionality with advanced preprocessing pipeline.
"""

from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
from typing import Optional

# Import preprocessing functions from preprocessing module
from ai_models.preprocessing import preprocess_taglish_text

# Global model and tokenizer cache
_model = None
_tokenizer = None




def get_qwen_model(model_name: str = "Qwen/Qwen2.5-7B-Instruct", device: str = "cuda"):
    """
    Gets or creates a Qwen model and tokenizer.
    
    Args:
        model_name: Hugging Face model name
        device: Device to run on ('cuda' or 'cpu')
    
    Returns:
        tuple of (model, tokenizer)
    """
    global _model, _tokenizer
    
    if _model is None or _tokenizer is None:
        print(f"Loading Qwen model: {model_name}...")
        _tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        _model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16 if device == "cuda" else torch.float32,
            device_map="auto" if device == "cuda" else None,
            trust_remote_code=True,
            load_in_4bit=True  # Use 4-bit quantization for ~7B model
        )
        if device == "cpu":
            _model = _model.to(device)
        print(f"Model loaded successfully on {device}")
    
    return _model, _tokenizer

def translate_taglish_to_english(
    text: str,
    model_name: Optional[str] = "Qwen/Qwen2.5-7B-Instruct",
    device: Optional[str] = "cuda",
    max_new_tokens: Optional[int] = 512,
    max_retries: int = 2
) -> dict:
    """
    Translates Taglish (mixed Tagalog-English) text to pure English using Qwen.
    Uses advanced preprocessing: dictionary lookup, phonetic correction,
    language-aware tokenization, and context scoring.
    
    Args:
        text: Taglish text to translate
        model_name: Hugging Face model name (default: Qwen2.5-7B-Instruct)
        device: Device to run on ('cuda' or 'cpu')
        max_new_tokens: Maximum tokens to generate
        max_retries: Number of retry attempts on failure
    
    Returns:
        dict with 'translated_text', 'model_used', 'preprocessing_info'
    """
    if not text or not text.strip():
        return {
            "translated_text": "",
            "model_used": model_name,
            "preprocessing_info": None
        }
    
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    
    if max_new_tokens is None:
        max_new_tokens = 512
    
    # Step 1: Preprocess the text with advanced pipeline
    preprocessing_result = preprocess_taglish_text(text)
    context_info = preprocessing_result["context_score"]
    
    last_error = None
    for attempt in range(max_retries):
        try:
            # Get Qwen model
            model, tokenizer = get_qwen_model(model_name, device)
            
            # Create enhanced prompt with preprocessing information
            system_prompt = """You are an expert Taglish-to-English translator with deep understanding of Filipino and English code-switching patterns. 
You will receive preprocessed text with:
- Phonetically corrected spellings
- Dictionary annotations showing Tagalog word meanings
- Context analysis of language mixing patterns

Your task is to produce natural, fluent English translations."""

            user_prompt = f"""Translate the following Taglish text to English.

Original text: {preprocessing_result['original_text']}

Preprocessed text with annotations: {preprocessing_result['annotated_text']}

Context Analysis:
- Language mix: {context_info['tagalog_ratio']*100:.0f}% Tagalog, {context_info['english_ratio']*100:.0f}% English
- Complexity: {context_info['complexity']}
- Dominant language: {context_info['dominant_language']}
- Code-switching points: {context_info['switch_count']}

Instructions:
1. Use the dictionary annotations [word] to understand Tagalog terms
2. Maintain the original meaning and tone
3. Fix any remaining spelling or grammar errors
4. Produce natural, fluent English
5. Return ONLY the English translation - no explanations, no notes

Translation:"""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # Format prompt using chat template
            prompt = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )
            
            # Tokenize and generate
            inputs = tokenizer(prompt, return_tensors="pt").to(device)
            
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    temperature=0.7,
                    top_p=0.9,
                    do_sample=True,
                    pad_token_id=tokenizer.eos_token_id
                )
            
            # Decode only the generated part
            generated_tokens = outputs[0][inputs.input_ids.shape[1]:]
            translated_text = tokenizer.decode(generated_tokens, skip_special_tokens=True).strip()
            
            # Remove common unwanted prefixes/suffixes that might slip through
            unwanted_patterns = [
                "Translation:", "English translation:", "Here is the translation:",
                "The translation is:", "Translated text:", "English:",
                "Note:", "Explanation:", "Context:"
            ]
            
            for pattern in unwanted_patterns:
                if translated_text.lower().startswith(pattern.lower()):
                    translated_text = translated_text[len(pattern):].strip()
                    # Remove leading colon or dash if present
                    if translated_text and translated_text[0] in [':', '-']:
                        translated_text = translated_text[1:].strip()
            
            # Remove quotes if the entire response is wrapped in them
            if translated_text.startswith('"') and translated_text.endswith('"'):
                translated_text = translated_text[1:-1].strip()
            elif translated_text.startswith("'") and translated_text.endswith("'"):
                translated_text = translated_text[1:-1].strip()
            
            return {
                "translated_text": translated_text,
                "model_used": model_name,
                "preprocessing_info": {
                    "corrected_text": preprocessing_result["corrected_text"],
                    "context_score": context_info
                }
            }
        
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                continue
    
    # Fallback to original text if all retries failed
    print(f"Qwen translation failed after {max_retries} attempts: {last_error}")
    return {
        "translated_text": text,
        "model_used": f"{model_name} (failed, returned original)",
        "preprocessing_info": {
            "corrected_text": preprocessing_result.get("corrected_text", text),
            "context_score": context_info
        }
    }

def translate_taglish_batch(
    texts: list,
    model_name: Optional[str] = "Qwen/Qwen2.5-7B-Instruct",
    device: Optional[str] = "cuda",
    max_new_tokens: Optional[int] = 512
) -> list:
    """
    Translates multiple Taglish texts to English using Qwen with advanced preprocessing.
    
    Args:
        texts: List of Taglish texts
        model_name: Hugging Face model name (default: Qwen2.5-7B-Instruct)
        device: Device to run on ('cuda' or 'cpu')
        max_new_tokens: Maximum tokens to generate
    
    Returns:
        list of dicts with translation results and preprocessing info
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
        results.append(result)
    
    return results
