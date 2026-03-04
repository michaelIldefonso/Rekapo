"""
Modal deployment for Rekapo AI models
Deploys Whisper, NLLB, and Qwen models as serverless GPU functions
"""
import modal

# Create Modal app
app = modal.App("rekapo-ai")

# Define base image with CUDA and cuDNN support
base_image = (
    modal.Image.from_registry(
        "nvidia/cuda:12.1.0-cudnn8-devel-ubuntu22.04",  # devel has build tools
        add_python="3.11"
    )
    .run_commands(
        "apt-get update",
        "apt-get install -y clang",  # Explicitly install clang first
    )
    .apt_install(
        "ffmpeg",
        "pkg-config",
        "libavcodec-dev",
        "libavformat-dev",
        "libavutil-dev",
        "libavdevice-dev",
        "libavfilter-dev",
        "libswscale-dev",
        "libswresample-dev",
    )
    .pip_install(
        "numpy<2",
        "torch==2.1.0",
        "transformers>=4.37.0",
        "ctranslate2==4.0.0",
        "faster-whisper==1.0.0",
        "bitsandbytes==0.41.3",
        "accelerate==0.25.0",
        "sentencepiece==0.1.99",
        "protobuf==4.25.1",
        "scipy",  # Required by bitsandbytes
    )
)

# Create volumes for model caching
whisper_volume = modal.Volume.from_name("whisper-models", create_if_missing=True)
nllb_volume = modal.Volume.from_name("nllb-models", create_if_missing=True)
qwen_volume = modal.Volume.from_name("qwen-models", create_if_missing=True)

# ============================================================================
# WHISPER INFERENCE
# ============================================================================

@app.function(
    image=base_image,
    gpu="T4",  # Works perfectly on T4
    volumes={"/models/whisper": whisper_volume},
    secrets=[modal.Secret.from_name("huggingface")],  # Add HF token
    timeout=600,  # 10 minutes max
)
def transcribe_audio(
    audio_bytes: bytes,
    language: str = "tl",  # Tagalog
) -> dict:
    """
    Transcribe audio using fine-tuned Whisper model
    
    Args:
        audio_bytes: Audio file bytes
        language: Language code (default: 'tl' for Tagalog)
    
    Returns:
        dict with transcription segments
    """
    import tempfile
    from faster_whisper import WhisperModel
    from huggingface_hub import login
    import os
    
    # Login to HuggingFace with token from secrets
    hf_token = os.environ.get("HUGGINGFACE_TOKEN")
    if hf_token:
        login(token=hf_token)
    
    # Model path from HuggingFace (will be downloaded to volume on first run)
    model_path = "michaelildefonso/whisper-small-taglish-fine-tuned-ct2"
    
    # Load model (cached in volume) - matches local inference.py
    print(f"Loading Whisper model from {model_path}...")
    model = WhisperModel(
        model_path,
        device="cuda",
        compute_type="float16",
    )
    
    # Save audio bytes to temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
        tmp_file.write(audio_bytes)
        tmp_path = tmp_file.name
    
    try:
        # Transcribe with parameters matching local inference.py
        segments, info = model.transcribe(
            tmp_path,
            language=language,
            beam_size=5,
            vad_filter=True,
            temperature=0.2,
            repetition_penalty=1.05,  # Reduced for Tagalog to preserve reduplication
            no_repeat_ngram_size=3,
            compression_ratio_threshold=2.4,
            condition_on_previous_text=True,
        )
        
        # Convert segments to list
        results = []
        for segment in segments:
            results.append({
                "start": segment.start,
                "end": segment.end,
                "text": segment.text,
            })
        
        return {
            "segments": results,
            "language": info.language,
            "duration": info.duration,
        }
    finally:
        # Clean up temp file
        os.unlink(tmp_path)


# ============================================================================
# NLLB TRANSLATION
# ============================================================================

@app.function(
    image=base_image,
    gpu="T4",  # float16 CT2 on T4
    volumes={"/models/nllb": nllb_volume},
    secrets=[modal.Secret.from_name("huggingface")],  # Add HF token for model download
    timeout=300,  # 5 minutes max
)
def translate_text(
    text: str,
    source_lang: str = "tgl_Latn",  # Tagalog
    target_lang: str = "eng_Latn",  # English
) -> dict:
    """
    Translate text using CTranslate2 NLLB model (4-8x faster, lower cost!)
    Matches local inference.py implementation
    
    Args:
        text: Text to translate
        source_lang: Source language code (NLLB format)
        target_lang: Target language code (NLLB format)
    
    Returns:
        dict with translated text
    """
    import ctranslate2
    from transformers import AutoTokenizer
    from huggingface_hub import snapshot_download
    import os
    
    # Your uploaded CT2 model
    model_name = "michaelildefonso/nllb-1.3b-ct2"
    
    # Download model to volume (cached after first run)
    print(f"Loading CT2 NLLB translator: {model_name}...")
    model_path = snapshot_download(
        repo_id=model_name,
        cache_dir="/models/nllb",
    )
    
    # Load translator with float16 compute type for better accuracy
    translator = ctranslate2.Translator(model_path, device="cuda", compute_type="float16")
    
    # Load tokenizer from HuggingFace
    tokenizer = AutoTokenizer.from_pretrained("facebook/nllb-200-1.3B")
    
    # Set source language for tokenizer
    tokenizer.src_lang = source_lang
    
    # Tokenize input text (CTranslate2 expects list of tokens)
    encoded = tokenizer.convert_ids_to_tokens(tokenizer.encode(text))
    
    # Translate using CTranslate2
    results = translator.translate_batch(
        [encoded],
        target_prefix=[[target_lang]],
        max_batch_size=2048,
        beam_size=5,
        max_decoding_length=512
    )
    
    # Decode translation (CTranslate2 returns tokens)
    translated_tokens = results[0].hypotheses[0]
    translated_text = tokenizer.decode(
        tokenizer.convert_tokens_to_ids(translated_tokens),
        skip_special_tokens=True
    )
    
    return {
        "translated_text": translated_text.strip(),
        "source_lang": source_lang,
        "target_lang": target_lang,
    }


# ============================================================================
# QWEN SUMMARIZATION
# ============================================================================

@app.function(
    image=base_image,
    gpu="T4",  # Testing with bfloat16
    volumes={"/models/qwen": qwen_volume},
    secrets=[modal.Secret.from_name("huggingface")],  # Add HF token
    timeout=600,  # 10 minutes max
)
def summarize_text(
    text: str,
    max_length: int = 300,
    min_length: int = 50,
) -> dict:
    """
    Summarize text using Qwen2.5-1.5B-Instruct
    
    Args:
        text: Text to summarize
        max_length: Maximum summary tokens
        min_length: Minimum summary tokens
    
    Returns:
        dict with summary
    """
    from transformers import AutoTokenizer, AutoModelForCausalLM
    import torch
    
    model_name = "Qwen/Qwen2.5-1.5B-Instruct"
    
    print(f"Loading Qwen model: {model_name}...")
    
    # Load model in bfloat16 for better numerical stability
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        trust_remote_code=True,
        device_map="auto",
        torch_dtype=torch.bfloat16,  # Better stability than float16
        low_cpu_mem_usage=True,
    )
    
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    model.eval()
    
    # Build prompt
    messages = [
        {"role": "system", "content": "You are a helpful assistant that summarizes meeting transcripts concisely."},
        {"role": "user", "content": f"Summarize the following meeting transcript in a clear and concise way:\n\n{text}"}
    ]
    
    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )
    
    # Tokenize and generate
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    
    with torch.inference_mode():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_length,
            min_new_tokens=min_length,
            do_sample=True,  # A10G handles sampling well
            temperature=0.7,
            top_p=0.9,
            top_k=40,
            repetition_penalty=1.1,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
            use_cache=True,
        )
    
    # Decode only generated part
    generated_ids = outputs[0][inputs.input_ids.shape[1]:]
    summary = tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
    
    # Clean up common prefixes
    unwanted_patterns = [
        "Summary:", "Here is the summary:", "The summary is:",
        "Transcript summary:", "Meeting summary:"
    ]
    for pattern in unwanted_patterns:
        if summary.lower().startswith(pattern.lower()):
            summary = summary[len(pattern):].strip()
    
    return {
        "summary": summary,
        "original_length": len(text.split()),
    }


# ============================================================================
# LOCAL TESTING FUNCTIONS
# ============================================================================

@app.local_entrypoint()
def test_local():
    """
    Test all models locally before deploying
    """
    print("🧪 Testing Modal deployment locally...")
    
    # Test Whisper
    print("\n1️⃣ Testing Whisper Transcription...")
    try:
        with open("tests/audio_files/t1.mp3", "rb") as f:
            audio_bytes = f.read()
        result = transcribe_audio.remote(audio_bytes)
        print(f"✅ Transcription successful!")
        print(f"   Language: {result['language']}")
        print(f"   Duration: {result['duration']:.2f}s")
        print(f"   Segments: {len(result['segments'])}")
        if result['segments']:
            print(f"   First segment: {result['segments'][0]['text'][:100]}...")
    except Exception as e:
        print(f"❌ Whisper test failed: {e}")
    
    # Test Translation
    print("\n2️⃣ Testing NLLB Translation...")
    try:
        # More realistic Taglish meeting content
        test_text = "Okay so ang meeting natin today ay tungkol sa quarterly sales targets. May mga concerns tayo regarding sa timeline ng implementation. Kailangan natin mag-coordinate with the marketing team para sa product launch next month."
        result = translate_text.remote(test_text)
        print(f"✅ Translation: {result['translated_text']}")
        print(f"   Original: {test_text[:80]}...")
    except Exception as e:
        print(f"❌ Translation test failed: {e}")
    
    # Test Summarization
    print("\n3️⃣ Testing Qwen Summarization...")
    try:
        test_long_text = """
        The meeting began with introductions from all participants. 
        We discussed the quarterly sales targets and reviewed the current progress. 
        The marketing team presented their new campaign strategy for the upcoming product launch.
        There were concerns raised about the timeline for implementation.
        Action items were assigned to each department lead to follow up on specific tasks.
        The meeting concluded with a commitment to reconvene in two weeks.
        """
        result = summarize_text.remote(test_long_text)
        print(f"✅ Summary: {result['summary']}")
        print(f"   Original length: {result['original_length']} words")
    except Exception as e:
        print(f"❌ Summarization test failed: {e}")
    
    print("\n✅ All tests complete!")


if __name__ == "__main__":
    # Run tests locally
    test_local()
