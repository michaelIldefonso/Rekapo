"""
Module: ai_models/summarizer/inference.py.

This module contains AI inference pipeline components.
"""

from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import sys
from pathlib import Path

# Add parent directory to path for config imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config.config import SUMMARIZER_MODEL_PATH

# Global summarizer cache.
# Caching avoids repeated warm-up latency (tokenizer/model load) across requests.
_summarizer_cache = {}

def clear_summarizer_cache():
    """
    Clears the summarizer cache and frees GPU memory.
    Call this after summarization to free memory for other models.
    """
    global _summarizer_cache
    if _summarizer_cache:
        print("🧹 Clearing summarizer cache...")
        _summarizer_cache.clear()
        
        if torch.cuda.is_available():
            import gc
            gc.collect()
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            print(f"   ✅ GPU memory freed")

def get_summarizer(model_name: str = None, device: str = "auto"):
    """
    Loads the summarization model from HuggingFace.
    Uses caching to avoid reloading the same model.
    
    Args:
        model_name: Model name or path (default from config: Qwen/Qwen2.5-1.5B-Instruct)
        device: "cpu", "cuda", or "auto" (auto-detects)
    
    Returns:
        tuple: (model, tokenizer, device)
    """
    # Use configured model if no path specified
    if model_name is None:
        model_name = SUMMARIZER_MODEL_PATH
    
    cache_key = f"{model_name}_{device}"
    
    if cache_key not in _summarizer_cache:
        print(f"📦 Loading summarization model: {model_name}")
        try:
            # Auto-detect device if not specified
            if device == "auto":
                device = "cuda" if torch.cuda.is_available() else "cpu"
            
            device_name = "GPU" if device == "cuda" else "CPU"
            print(f"🖥️  Using device: {device_name}")
            
            # Clear GPU memory before loading to reduce OOM risk on constrained GPUs.
            if device == "cuda":
                import gc
                print(f"🧹 Clearing GPU memory before loading model...")
                gc.collect()
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
                mem_allocated = torch.cuda.memory_allocated() / 1024**2
                mem_reserved = torch.cuda.memory_reserved() / 1024**2
                print(f"   💾 GPU Memory: {mem_allocated:.0f}MB allocated, {mem_reserved:.0f}MB reserved")
            
            # Load tokenizer
            tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
            
            # Load model with optimizations
            print(f"📥 Loading model with optimizations...")
            
            if device == "cuda":
                # GPU path prefers 4-bit quantization to keep inference viable on
                # consumer GPUs while preserving acceptable summary quality.
                try:
                    from transformers import BitsAndBytesConfig
                    
                    quantization_config = BitsAndBytesConfig(
                        load_in_4bit=True,
                        bnb_4bit_compute_dtype=torch.float16,
                        bnb_4bit_use_double_quant=True,
                        bnb_4bit_quant_type="nf4"
                    )
                    
                    model = AutoModelForCausalLM.from_pretrained(
                        model_name,
                        trust_remote_code=True,
                        device_map="auto",
                        quantization_config=quantization_config,
                        torch_dtype=torch.float16,
                        low_cpu_mem_usage=True
                    )
                    print(f"✨ Using 4-bit quantization (saves ~75% VRAM)")
                except Exception as e:
                    print(f"⚠️  4-bit quantization unavailable: {e}")
                    print(f"   Loading in float16 instead...")
                    model = AutoModelForCausalLM.from_pretrained(
                        model_name,
                        trust_remote_code=True,
                        device_map="auto",
                        torch_dtype=torch.float16,
                        low_cpu_mem_usage=True
                    )
            else:
                # CPU path uses float32 for numerical stability and compatibility.
                model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    trust_remote_code=True,
                    device_map=device,
                    torch_dtype=torch.float32,
                    low_cpu_mem_usage=True
                )
            
            model.eval()  # Set to evaluation mode
            
            # Keep checkpointing enabled for additional memory headroom.
            # Even in eval mode this can help large models on limited VRAM.
            if hasattr(model, 'gradient_checkpointing_enable'):
                model.gradient_checkpointing_enable()
            
            _summarizer_cache[cache_key] = (model, tokenizer, device)
            print(f"✅ Summarization model loaded and cached")
        except Exception as e:
            print(f"❌ Failed to load summarization model: {e}")
            raise RuntimeError(f"Failed to load summarization model '{model_name}': {e}")
    else:
        model, tokenizer, device = _summarizer_cache[cache_key]
        print(f"♻️  Using cached summarization model: {model_name}")
    
    return _summarizer_cache[cache_key]

def summarize_text(
    text: str,
    model_name: str = None,
    device: str = "auto",
    max_length: int = 300,
    min_length: int = 50,
    beam_size: int = 1
) -> dict:
    """
    Summarizes text using an instruction-tuned LLM (default: Qwen2.5-1.5B).
    
    Args:
        text: Text to summarize
        model_name: Model name or path (default from config)
        device: "cpu", "cuda", or "auto"
        max_length: Maximum length of summary
        min_length: Minimum length of summary
        beam_size: Number of beams (1 = sampling mode)
    
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
        # Load summarizer (model and tokenizer)
        model, tokenizer, device_used = get_summarizer(model_name, device)
        
        word_count = len(text.split())
        print(f"📝 Summarizing {word_count} words (max_tokens={max_length})...")
        
        # Build instruction prompt for Qwen using chat template
        messages = [
            {"role": "system", "content": "You are a helpful assistant that summarizes meeting transcripts concisely."},
            {"role": "user", "content": f"Summarize the following meeting transcript in a clear and concise way:\n\n{text}"}
        ]
        
        # Apply chat template
        prompt = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        # Tokenize input
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        
        # Generate summary with optimized settings
        with torch.no_grad():
            # Use torch.inference_mode for better performance
            with torch.inference_mode():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=max_length,
                    min_new_tokens=min_length,
                    do_sample=True,
                    temperature=0.7,
                    top_p=0.9,
                    top_k=40,
                    repetition_penalty=1.1,
                    eos_token_id=tokenizer.eos_token_id,
                    pad_token_id=tokenizer.pad_token_id if tokenizer.pad_token_id else tokenizer.eos_token_id,
                    use_cache=True  # Enable KV cache for faster generation
                )
        
        # Decode only the generated part (skip the input prompt)
        generated_ids = outputs[0][inputs.input_ids.shape[1]:]
        summary = tokenizer.decode(generated_ids, skip_special_tokens=True)
        
        # Clean up
        summary = summary.strip()
        
        # Remove common unwanted patterns
        unwanted_patterns = [
            "Summary:", "Here is the summary:", "The summary is:",
            "Transcript summary:", "Meeting summary:"
        ]
        for pattern in unwanted_patterns:
            if summary.lower().startswith(pattern.lower()):
                summary = summary[len(pattern):].strip()
        
        print(f"✅ summarize_text completed: {len(summary)} characters")
        
        return {
            "summary": summary.strip(),
            "original_length": word_count
        }
    
    except Exception as e:
        print(f"❌ Summarization failed in summarize_text: {e}")
        import traceback
        traceback.print_exc()
        raise RuntimeError(f"Summarization failed: {e}")

def summarize_transcriptions(
    transcriptions: list,
    model_name: str = None,
    device: str = "auto",
    max_length: int = 300,
    min_length: int = 75
) -> dict:
    """
    Summarizes multiple transcription chunks into a coherent summary.
    
    Args:
        transcriptions: List of dicts with 'transcription' and 'english_translation'
        model_name: Model name or path (default from config)
        device: "cpu", "cuda", or "auto"
        max_length: Maximum length of summary (tokens)
        min_length: Minimum length of summary (ignored with sampling)
    
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
        
        print(f"🤖 Calling summarizer model (max_length={max_length}, min_length={min_length})...")
        
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
    max_length: int = 300,
    min_length: int = 75
) -> dict:
    """
    Summarizes meeting segments with timestamps and speaker information.
    
    Args:
        segments: List of segment dicts with timing and text info
        model_name: Model name or path (default from config)
        device: "cpu", "cuda", or "auto"
        max_length: Maximum length of summary (tokens)
        min_length: Minimum length of summary (ignored with sampling)
    
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

