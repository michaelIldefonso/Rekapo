#!/usr/bin/env python3
"""
Translation Model Switcher

Quick utility to switch between NLLB-200 and Qwen translation models.
Usage:
    python switch_translator.py nllb     # Switch to NLLB-200-1.3B (lighter, ~2.7GB)
    python switch_translator.py qwen     # Switch to Qwen (heavier, ~8GB)
    python switch_translator.py status   # Show current configuration
"""

import sys
from pathlib import Path
import os

def read_env():
    """Read current .env file"""
    env_path = Path(__file__).parent / '.env'
    if not env_path.exists():
        return {}
    
    env_vars = {}
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
    return env_vars

def write_env(env_vars):
    """Write .env file"""
    env_path = Path(__file__).parent / '.env'
    with open(env_path, 'w') as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")

def show_status():
    """Show current configuration"""
    env_vars = read_env()
    model = env_vars.get('TRANSLATION_MODEL', 'nllb')
    preprocessing = env_vars.get('ENABLE_TAGLISH_PREPROCESSING', 'true')
    
    print("=" * 70)
    print("📊 CURRENT TRANSLATION CONFIGURATION")
    print("=" * 70)
    print(f"\n🌐 Translation Model: {model.upper()}")
    
    if model == "nllb":
        print("   ├─ Model: NLLB-200-1.3B")
        print("   ├─ Size: ~2.7GB")
        print("   ├─ Speed: Fast")
        print("   └─ Quality: Excellent (optimized for Tagalog)")
    elif model == "qwen":
        print("   ├─ Model: Qwen 2.5-7B Instruct")
        print("   ├─ Size: ~8GB (4-bit quantized)")
        print("   ├─ Speed: Slower")
        print("   └─ Quality: Excellent")
    
    print(f"\n📝 Taglish Preprocessing: {'ENABLED ✓' if preprocessing == 'true' else 'DISABLED ✗'}")
    
    if preprocessing == "true":
        print("   ├─ Phonetic correction (kc → kasi, tlga → talaga)")
        print("   ├─ Dictionary lookup (150+ Tagalog words)")
        print("   ├─ Language-aware tokenization")
        print("   └─ Context scoring")
    
    print("\n" + "=" * 70)
    print("💡 TIP: Restart the server after changing configuration")
    print("=" * 70 + "\n")

def switch_model(target_model):
    """Switch to specified model"""
    if target_model not in ['nllb', 'qwen']:
        print(f"❌ Invalid model: {target_model}")
        print("   Valid options: nllb, qwen")
        sys.exit(1)
    
    env_vars = read_env()
    old_model = env_vars.get('TRANSLATION_MODEL', 'nllb')
    
    if old_model == target_model:
        print(f"ℹ️  Already using {target_model.upper()}")
        show_status()
        return
    
    env_vars['TRANSLATION_MODEL'] = target_model
    
    # Ensure preprocessing is enabled by default
    if 'ENABLE_TAGLISH_PREPROCESSING' not in env_vars:
        env_vars['ENABLE_TAGLISH_PREPROCESSING'] = 'true'
    
    write_env(env_vars)
    
    print(f"✅ Switched from {old_model.upper()} → {target_model.upper()}")
    print()
    show_status()

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python switch_translator.py nllb     # Use NLLB (lighter)")
        print("  python switch_translator.py qwen     # Use Qwen (heavier)")
        print("  python switch_translator.py status   # Show current config")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "status":
        show_status()
    elif command in ['nllb', 'qwen']:
        switch_model(command)
    else:
        print(f"❌ Unknown command: {command}")
        print("   Valid commands: nllb, qwen, status")
        sys.exit(1)

if __name__ == "__main__":
    main()
