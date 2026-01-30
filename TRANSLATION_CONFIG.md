# Translation Model Configuration

Rekapo supports two translation models for Taglish to English translation. You can easily switch between them based on your hardware and quality requirements.

## 🎯 Available Models

### NLLB-200-1.3B (Default)
- **Model**: Meta's NLLB-200-1.3B (No Language Left Behind)
- **Size**: ~2.7GB
- **Speed**: Fast
- **Memory**: Moderate requirements
- **Quality**: Excellent (specifically optimized for Tagalog)
- **Best for**: Production servers, balanced quality and performance

### Qwen 2.5-7B Instruct
- **Size**: ~8GB (4-bit quantized)
- **Speed**: Slower
- **Memory**: Requires more VRAM/RAM
- **Quality**: Excellent (general-purpose LLM)
- **Best for**: High-quality transcription, powerful hardware

## 🔄 Quick Switch

### Using the Switch Script (Easiest)
```bash
# Switch to NLLB (lighter)
python switch_translator.py nllb

# Switch to Qwen (heavier, better quality)
python switch_translator.py qwen

# Check current configuration
python switch_translator.py status
```

### Manual Configuration
Edit your `.env` file:
```env
# Choose: "nllb" or "qwen"
TRANSLATION_MODEL=nllb

# Enable preprocessing (recommended)
ENABLE_TAGLISH_PREPROCESSING=true
```

## 📝 Taglish Preprocessing

Both models benefit from preprocessing, which includes:
- ✅ **Phonetic correction**: "kc" → "kasi", "tlga" → "talaga", "pwedi" → "pwede"
- ✅ **Dictionary lookup**: 150+ Tagalog-English word mappings
- ✅ **Language-aware tokenization**: Identifies Tagalog vs English segments
- ✅ **Context scoring**: Analyzes code-switching patterns

**Recommendation**: Keep `ENABLE_TAGLISH_PREPROCESSING=true` for both models.

## 🚀 After Switching

**Important**: Restart your server after changing the translation model:
```bash
# Stop current server (Ctrl+C)

# Restart
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## 📊 Comparison

| Feature | NLLB-200 | Qwen |
|---------|----------|------|
| Model Size | 2.7GB | 8GB |
| RAM Usage | ~5GB | ~10GB |
| Translation Speed | Fast | Slower |
| Translation Quality | Excellent | Excellent |
| Tagalog Optimization | ✅ Specifically trained | ⚠️ General purpose |
| Code-switching | Excellent (with preprocessing) | Excellent |
| GPU Required | Optional | Recommended |

## 💡 Recommendations

### For Development/Testing
```env
TRANSLATION_MODEL=nllb
ENABLE_TAGLISH_PREPROCESSING=true
```
Fast iterations, good enough quality.

### For Production (Limited Hardware)
```env
TRANSLATION_MODEL=nllb
ENABLE_TAGLISH_PREPROCESSING=true
```
Efficient and reliable.

### For Production (High Quality)
```env
TRANSLATION_MODEL=qwen
ENABLE_TAGLISH_PREPROCESSING=true
```
Best translation quality, requires more resources.

## 🛠️ Troubleshooting

### Out of Memory Errors
If you get OOM errors with Qwen:
1. Switch to NLLB: `python switch_translator.py nllb`
2. Or reduce batch sizes
3. Or use CPU instead of GPU (slower but works)

### Slow Translation with Qwen
This is normal - Qwen is more compute-intensive. Consider:
- Using NLLB for faster responses
- Upgrading hardware
- Using GPU acceleration

### Translation Quality Issues
1. Ensure preprocessing is enabled: `ENABLE_TAGLISH_PREPROCESSING=true`
2. Try switching models to compare
3. Check if text contains unusual patterns

## 📈 Performance Tips

1. **First run is slower**: Models need to load into memory
2. **GPU helps**: Both models benefit from GPU, especially Qwen
3. **Preprocessing is fast**: Adds minimal overhead, significant quality gain
4. **Cache is used**: Models stay in memory after first load

## 🔍 Current Status

Check your current configuration anytime:
```bash
python switch_translator.py status
```

Output shows:
- Active translation model
- Model specifications
- Preprocessing status
- Feature details
