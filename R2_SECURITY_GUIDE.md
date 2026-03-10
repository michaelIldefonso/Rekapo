# 🔒 R2 Security Implementation Guide

## ✅ What's Been Done

I've already implemented the backend changes for you:

### 1. **Storage Layer** ([storage/storage.py](storage/storage.py))
- ✅ Modified to store R2 keys instead of public URLs
- ✅ Returns `r2://bucket/key` format (private references)
- ✅ No more permanent public URLs exposed

### 2. **API Response Schema** ([schemas/schemas.py](schemas/schemas.py))
- ✅ Added `audio_url` field to `SessionRecordingSegmentResponse`
- ✅ Contains time-limited signed URLs (1-hour expiration)
- ✅ Keeps `audio_path` for internal storage reference

### 3. **Sessions Endpoint** ([routes/sessions.py](routes/sessions.py))
- ✅ Added `_add_signed_url_to_segment()` helper function
- ✅ Automatically generates signed URLs when returning session details
- ✅ Graceful fallback if URL generation fails

---

## 📋 What You Need to Do

### Step 1: Make R2 Bucket Private (5 minutes)

**Cloudflare Dashboard Steps:**

1. Go to **Cloudflare Dashboard** → **R2 Object Storage**
2. Click on your bucket (the one storing audio files)
3. Click the **Settings** tab
4. Find **Public Access** section
5. Toggle **Allow Access** to **OFF** (disable public access)
6. Click **Confirm** to save

**What this does:** 
- Blocks all public URL access to your files
- Forces all access to go through your backend with signed URLs
- Old public URLs will return 403 Forbidden

---

### Step 2: Remove R2_PUBLIC_URL from .env (Optional Cleanup)

Since you're no longer using public URLs, you can remove or comment out this line:

```bash
# .env file
# R2_PUBLIC_URL=https://your-public-domain.com  # No longer needed
```

**Note:** The code will still work if you leave it - it just won't use it anymore.

---

### Step 3: Test the Implementation (10 minutes)

#### Test 1: Verify Backend Works

```bash
# Start your backend
cd c:\Users\MICHAEL\Documents\GitHub\Rekapo
python main.py
```

#### Test 2: Check a Session via API

Open your browser or use curl:

```bash
# Replace with your actual session ID and auth token
curl http://localhost:8000/api/sessions/123/details \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**What to look for in the response:**

```json
{
  "recording_segments": [
    {
      "id": 1,
      "segment_number": 1,
      "audio_path": "r2://your-bucket/audio/session_123_segment_1.mp3",
      "audio_url": "https://account_id.r2.cloudflarestorage.com/bucket/audio/session_123_segment_1.mp3?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=...&X-Amz-Expires=3600&X-Amz-Signature=...",
      "transcript_text": "Hello world...",
      "created_at": "2026-03-11T01:00:00Z"
    }
  ]
}
```

**Key points:**
- ✅ `audio_path` starts with `r2://` (private key)
- ✅ `audio_url` has query parameters like `X-Amz-Algorithm`, `X-Amz-Signature` (signed URL)
- ✅ `X-Amz-Expires=3600` means 1-hour expiration

#### Test 3: Verify URL Expiration

1. Copy a signed URL from the API response
2. Open it in your browser - **should work** and play audio
3. Wait 1 hour (or change `expiration_seconds=60` in code for faster testing)
4. Try the same URL again - **should return 403 Forbidden**

---

### Step 4: Update Mobile App (if needed)

Your React Native app likely fetches session details and displays audio URLs.

**Check your mobile code for:**

```javascript
// In your SessionDetailsScreen.js or similar
const audioUrl = segment.audio_path;  // ❌ Old way - won't work anymore

// Change to:
const audioUrl = segment.audio_url || segment.audio_path;  // ✅ Use signed URL first, fallback to path
```

**Before:**
```javascript
// Example old code
<Audio
  source={{ uri: segment.audio_path }}
/>
```

**After:**
```javascript
// Updated code
<Audio
  source={{ 
    uri: segment.audio_url || segment.audio_path  // Use signed URL
  }}
/>
```

---

## 🔧 Configuration Options

### Adjust Signed URL Expiration Time

In [routes/sessions.py](routes/sessions.py#L41):

```python
# Default: 1 hour (3600 seconds)
response.audio_url = generate_signed_url(r2_key, expiration_seconds=3600)

# Change to 30 minutes:
response.audio_url = generate_signed_url(r2_key, expiration_seconds=1800)

# Change to 4 hours (for long meetings):
response.audio_url = generate_signed_url(r2_key, expiration_seconds=14400)
```

**Recommendation:** 1-2 hours is good balance between security and usability.

---

## 🧪 Testing Checklist

- [ ] R2 bucket set to private in Cloudflare dashboard
- [ ] Backend starts without errors
- [ ] GET `/api/sessions/{id}/details` returns signed URLs
- [ ] Signed URLs work in browser (audio plays)
- [ ] Old public URLs return 403 Forbidden
- [ ] Mobile app displays audio correctly
- [ ] URLs expire after configured time (test with short expiration)

---

## 🐛 Troubleshooting

### Problem: "Failed to generate signed URL"

**Cause:** R2 credentials not configured or invalid

**Fix:**
```bash
# Check your .env file has these:
R2_ENABLED=true
R2_ACCESS_KEY_ID=your_access_key
R2_SECRET_ACCESS_KEY=your_secret_key
R2_BUCKET_NAME=your_bucket
R2_ENDPOINT=https://account_id.r2.cloudflarestorage.com
```

### Problem: "403 Forbidden" when accessing audio

**Possible causes:**

1. **R2 bucket is now private** (expected!) - Use signed URLs from API
2. **Signed URL expired** - URLs are only valid for 1 hour by default
3. **Credentials mismatch** - Check R2 keys in `.env`

**Solution:** Always get fresh signed URLs from your API endpoint.

### Problem: Mobile app shows broken audio

**Cause:** App still using old `audio_path` (R2 keys) instead of `audio_url` (signed URLs)

**Fix:** Update mobile app to use `segment.audio_url` instead of `segment.audio_path`

---

## 📊 Security Improvements Summary

| Before | After |
|---|---|
| ❌ Permanent public URLs | ✅ Time-limited signed URLs |
| ❌ Anyone with link can access | ✅ Only users with valid API tokens |
| ❌ URLs never expire | ✅ Auto-expire after 1 hour |
| ❌ Can be shared/leaked | ✅ Limited sharing window |
| ❌ Public R2 bucket | ✅ Private R2 bucket |

**Security benefit:** Meeting recordings are now protected with:
- Authentication required (JWT token to get signed URL)
- Time-limited access (URLs expire)
- Cloudflare TLS encryption (HTTPS)
- No permanent public exposure

---

## 🎓 For Your Thesis Defense

**Before:**
> "Audio files are stored in Cloudflare R2 with public URLs"

**After:**
> "Audio files are stored in private Cloudflare R2 storage with time-limited signed URLs (1-hour expiration). Access requires authentication through the FastAPI backend, and URLs automatically expire to prevent unauthorized long-term access. This implements secure file access without additional infrastructure costs."

**Talking points:**
- ✅ Private storage with signed URLs (AWS S3-compatible security pattern)
- ✅ Time-limited access (configurable expiration)
- ✅ Authentication-gated (JWT required to get URLs)
- ✅ TLS encryption in transit (Cloudflare HTTPS)
- ✅ Zero additional cost (configuration change only)

---

## 📁 Files Modified

1. **[storage/storage.py](storage/storage.py)** - Returns R2 keys instead of public URLs
2. **[schemas/schemas.py](schemas/schemas.py)** - Added `audio_url` field
3. **[routes/sessions.py](routes/sessions.py)** - Added signed URL generation
4. **[utils/r2_signed_urls.py](utils/r2_signed_urls.py)** - Signed URL utility (already created)

---

## ✅ Next Steps

1. **Make R2 bucket private** (5 min) ← Do this first!
2. **Test backend API** (10 min)
3. **Update mobile app** (if using `audio_path` directly)
4. **Rebuild mobile app** with new minSdkVersion (from earlier)
5. **Run security scans** (`python security_scan.py`)

**Total time:** ~30 minutes

---

## 🆘 Need Help?

If you encounter issues:

1. Check backend logs: Look for "Failed to generate signed URL" errors
2. Verify R2 credentials in `.env`
3. Test signed URL directly in browser (should have `X-Amz-*` parameters)
4. Check mobile app network requests (audio URLs should have signatures)

**Common issue:** If audio plays in browser but not mobile app, the mobile app is likely using old `audio_path` field - update to use `audio_url`.
