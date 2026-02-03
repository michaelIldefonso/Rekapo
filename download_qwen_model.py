"""
Download Qwen 2.5-3B-CT2 Model for Summarization

This script downloads the model in a resumable way, suitable for systems
with limited RAM (8GB). If interrupted, simply run it again to resume.
"""

from huggingface_hub import snapshot_download
import os
import sys

def download_model():
    """Download Qwen 2.5-3B-CT2 model from HuggingFace"""
    
    model_name = "ctranslate2-4you/qwen2.5-3b-instruct-ct2"
    cache_dir = os.path.expanduser("~/.cache/huggingface/hub")
    
    print("=" * 70)
    print("📦 Qwen 2.5-3B-CT2 Model Downloader")
    print("=" * 70)
    print(f"Model: {model_name}")
    print(f"Cache directory: {cache_dir}")
    print(f"⚠️  Download size: ~6GB")
    print(f"⚠️  Make sure you have enough disk space")
    print("=" * 70)
    
    confirmation = input("\n▶️  Start download? (y/n): ")
    if confirmation.lower() != 'y':
        print("❌ Download cancelled")
        sys.exit(0)
    
    print("\n🔄 Starting download...")
    print("💡 Tip: If interrupted, run this script again to resume\n")
    
    try:
        model_path = snapshot_download(
            repo_id=model_name,
            cache_dir=cache_dir,
            resume_download=True,  # Resume if interrupted
            local_files_only=False,
            # Download with progress bar
            tqdm_class=None  # Use default tqdm for progress
        )
        
        print("\n" + "=" * 70)
        print("✅ Model downloaded successfully!")
        print("=" * 70)
        print(f"📁 Model location: {model_path}")
        print("\n✅ You can now run the application:")
        print("   python main.py")
        print("\n✅ Or test the summarizer:")
        print("   python tests/test_summarization.py")
        print("=" * 70)
        
    except KeyboardInterrupt:
        print("\n\n⏸️  Download interrupted")
        print("💡 Run this script again to resume from where it stopped")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Download failed: {e}")
        print("\n💡 Troubleshooting:")
        print("   1. Check your internet connection")
        print("   2. Make sure you have enough disk space (~6GB)")
        print("   3. Try running the script again (it will resume)")
        print("   4. Install required package: pip install huggingface-hub")
        sys.exit(1)

if __name__ == "__main__":
    # Check if huggingface_hub is installed
    try:
        import huggingface_hub
        print(f"✅ huggingface_hub version: {huggingface_hub.__version__}")
    except ImportError:
        print("❌ huggingface_hub not installed")
        print("📦 Installing huggingface_hub...")
        os.system("pip install huggingface-hub")
        print("\n✅ Installation complete. Please run this script again.")
        sys.exit(0)
    
    download_model()
