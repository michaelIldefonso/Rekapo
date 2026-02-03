# Manual Model Download Instructions

Since you have 8GB RAM, downloading large models through CLI can cause issues. Here's how to download the Qwen 2.5-3B-CT2 model manually.

## Option 1: Download via Python Script (Recommended)

Create and run this script to download the model in chunks:

```python
# download_qwen_model.py
from huggingface_hub import snapshot_download
import os

print("📦 Downloading Qwen 2.5-3B-CT2 model...")
print("⚠️  This will download ~6GB. Make sure you have enough disk space.")

model_name = "ctranslate2-4you/qwen2.5-3b-instruct-ct2"
cache_dir = os.path.expanduser("~/.cache/huggingface/hub")

try:
    model_path = snapshot_download(
        repo_id=model_name,
        cache_dir=cache_dir,
        resume_download=True,  # Resume if interrupted
        local_files_only=False
    )
    print(f"✅ Model downloaded successfully!")
    print(f"📁 Model location: {model_path}")
except Exception as e:
    print(f"❌ Download failed: {e}")
    print("💡 You can resume by running this script again.")
```

**Run it:**
```bash
cd C:\Users\MICHAEL\Documents\GitHub\Rekapo
venv\Scripts\activate
python download_qwen_model.py
```

The script will:
- Download in chunks (resumable if interrupted)
- Store in HuggingFace cache (~6GB)
- Can be paused and resumed

---

## Option 2: Download via Git LFS (Manual)

If you prefer full control:

1. **Install Git LFS:**
```bash
# Download from: https://git-lfs.github.com/
# Or via chocolatey:
choco install git-lfs
git lfs install
```

2. **Clone the model repository:**
```bash
cd C:\Users\MICHAEL\.cache\huggingface\hub
git clone https://huggingface.co/ctranslate2-4you/qwen2.5-3b-instruct-ct2
```

3. **Update config.py to point to local path:**
```python
SUMMARIZER_MODEL_PATH = r"C:\Users\MICHAEL\.cache\huggingface\hub\qwen2.5-3b-instruct-ct2"
```

---

## Option 3: Download from HuggingFace Web UI

1. Go to: https://huggingface.co/ctranslate2-4you/qwen2.5-3b-instruct-ct2/tree/main
2. Download these files manually:
   - `config.json`
   - `model.bin` (largest file ~6GB)
   - `shared_vocabulary.json`
   - `tokenizer_config.json`
   - `tokenizer.json`
   - All other JSON files

3. Create folder structure:
```
C:\Users\MICHAEL\.cache\huggingface\hub\models--ctranslate2-4you--qwen2.5-3b-instruct-ct2\
  snapshots\
    <commit-hash>\
      config.json
      model.bin
      ...
```

4. Or simpler - put all files in:
```
C:\Users\MICHAEL\Documents\GitHub\Rekapo\ai_models\summarizer\qwen2.5-3b-ct2\
```

Then update config:
```python
SUMMARIZER_MODEL_PATH = "ai_models/summarizer/qwen2.5-3b-ct2"
```

---

## Testing After Download

```bash
python tests/test_summarization.py
```

If it loads successfully, you'll see:
```
📦 Loading CTranslate2 summarization model: ctranslate2-4you/qwen2.5-3b-instruct-ct2
🖥️  Using device: GPU
✅ CTranslate2 Qwen summarization model loaded and cached
```

---

## Troubleshooting

**Out of memory during download:**
- Use Option 1 with `resume_download=True`
- Download when other applications are closed
- Use Option 3 (manual download) with browser download manager

**Model not found:**
- Check the path in `config.py`
- Make sure all files are in the same directory
- Verify `model.bin` is present (it's the main file)

**ImportError:**
```bash
pip install huggingface-hub
```
