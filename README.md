# Rekapo

> Mobile-based near real-time meeting summarizer with Taglish (Tagalog + English) support.

Rekapo is a FastAPI backend that transcribes, translates, and summarizes meeting audio in near real-time. It is built for a mobile-first workflow — audio chunks are streamed from a mobile app over WebSocket, transcribed using a fine-tuned Whisper model, translated with NLLB-1.3B, and summarized using a Qwen LLM. AI inference can run locally or on serverless GPUs via [Modal](https://modal.com).

---

## Features

- 🎤 **Near real-time transcription** with a fine-tuned `faster-whisper` model
- 🌐 **WebSocket streaming** — receive audio chunks from mobile in real time
- 🔊 **VAD-based audio segmentation** for accurate silence detection
- 🇵🇭 **Taglish support** — phonetic correction, dictionary lookup, and context analysis for Tagalog/English mixed speech
- 📝 **Meeting session management** — create, update, complete, and replay sessions
- 🤖 **AI summarization** — Qwen via Modal (serverless GPU)
- 🌍 **Translation** — NLLB-200 1.3B model
- ☁️ **Cloudflare R2 storage** — optional cloud storage for audio and logs
- 👤 **Google OAuth** — sign in with Google on mobile
- 🖼️ **Profile photo upload** with local or R2 storage
- 🛡️ **Admin panel** — user management, session analytics, logs, and statistics
- ⏰ **Background scheduler** — automated tasks via APScheduler

---

## Tech Stack

| Layer | Technology |
|---|---|
| API Framework | FastAPI |
| Database | PostgreSQL (SQLAlchemy + Alembic) |
| Auth | Google OAuth 2.0 + JWT |
| Transcription | faster-whisper (fine-tuned Whisper) |
| Translation | NLLB-200-1.3B (CTranslate2) |
| Summarization | Qwen 2.5 (Modal) |
| Serverless GPU | Modal |
| Object Storage | Cloudflare R2 (optional) |
| Background Jobs | APScheduler |

---

## Project Structure

```
Rekapo/
├── main.py                         # FastAPI app entry point
├── config/
│   └── config.py                   # Environment-based configuration
├── routes/
│   ├── auth.py                     # Google OAuth + JWT auth
│   ├── users.py                    # User profile endpoints
│   ├── sessions.py                 # Meeting session management
│   ├── whisper.py                  # WebSocket transcription endpoint
│   └── logs.py                     # Logging endpoints
├── admin/
│   ├── admin_auth.py               # Admin authentication
│   ├── admin_users.py              # User management
│   ├── admin_sessions.py           # Session oversight
│   ├── admin_statistics.py         # System statistics
│   ├── admin_user_analytics.py     # Per-user analytics
│   └── admin_logs.py               # Log management
├── ai_models/
│   ├── whisper/inference.py        # Local Whisper inference
│   ├── translator/inference.py     # Local NLLB translation
│   ├── summarizer/inference.py     # QWEN 2.5
│   ├── modal_client.py             # Modal serverless GPU client
│   └── preprocessing/taglish.py   # Taglish preprocessing pipeline
├── db/
│   └── db.py                       # SQLAlchemy models + DB init
├── schemas/
│   └── schemas.py                  # Pydantic request/response models
├── services/
│   └── services.py                 # WebSocket connection manager
├── storage/
│   └── storage.py                  # Local + Cloudflare R2 storage abstraction
├── utils/
│   ├── utils.py                    # Logging helpers
│   └── scheduler.py                # Background task scheduler
├── uploads/
│   └── profile_photos/             # User profile photos (local storage)
└── tests/                          # Test suite
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- PostgreSQL database
- Google Cloud project with OAuth 2.0 credentials
- (Optional) [Modal](https://modal.com) account for serverless GPU inference
- (Optional) Cloudflare R2 bucket for cloud storage

### 1. Clone and install dependencies

```bash
git clone https://github.com/your-username/Rekapo.git
cd Rekapo
pip install -r requirements.txt
```

### 2. Configure environment variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/rekapo

# Auth
JWT_SECRET_KEY=your-secret-key-here
GOOGLE_CLIENT_ID=your-google-client-id

# AI Inference (true = Modal serverless GPU, false = local models)
USE_MODAL=true

# Optional: Cloudflare R2
R2_ENABLED=false
R2_ENDPOINT_URL=https://your-account-id.r2.cloudflarestorage.com
R2_ACCESS_KEY_ID=your-r2-access-key-id
R2_SECRET_ACCESS_KEY=your-r2-secret-access-key
R2_BUCKET_NAME=rekapo-audio
```

See `.env.example` for all available options.

### 3. Run the server

```bash
uvicorn main:app --reload
```

The interactive API docs will be available at **`http://localhost:8000/docs`** locally, or at **`https://rekapo-api.ildf.site/docs`** on the live server.

---

## API Overview

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/google-mobile` | Sign in with Google ID token |

### Sessions

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/sessions` | Create a new meeting session |
| `GET` | `/api/sessions` | List user's sessions |
| `GET` | `/api/sessions/{id}` | Get session details |
| `PATCH` | `/api/sessions/{id}` | Update session |

### Transcription

| Method | Endpoint | Description |
|---|---|---|
| `WS` | `/api/transcribe/{session_id}` | WebSocket — stream audio chunks for real-time transcription |

### User Profile

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/users/me` | Get current user profile |
| `PATCH` | `/api/users/me/username` | Update username |
| `PATCH` | `/api/users/me/photo` | Upload profile photo |

> See `/docs` for the full interactive API reference, or the markdown docs in the repo root for detailed endpoint documentation.

---

## AI Inference Modes

Rekapo supports two inference modes controlled by the `USE_MODAL` environment variable:

| Mode | `USE_MODAL` | Description |
|---|---|---|
| **Modal (recommended)** | `true` | Serverless GPU inference via Modal — no local GPU needed |
| **Local** | `false` | Run models locally — requires GPU and model files on disk |

**Local model paths** (when `USE_MODAL=false`):

- Whisper: `ai_models/whisper/models/whisper-small-fine-tuned-ct2`
- Translator: `ai_models/translator/nllb-1.3b-ct2`
- Summarizer: configured via `SUMMARIZER_MODEL_PATH` env var

---

## Documentation

| File | Description |
|---|---|
| [MOBILE_INTEGRATION.md](MOBILE_INTEGRATION.md) | Guide for integrating the mobile app |
| [USER_PROFILE_API.md](USER_PROFILE_API.md) | User profile endpoint reference |
| [SESSION_HISTORY_API.md](SESSION_HISTORY_API.md) | Session history endpoint reference |
| [ADMIN_MODULE.md](ADMIN_MODULE.md) | Admin panel documentation |
| [AUDIO_ACCURACY_IMPROVEMENTS.md](AUDIO_ACCURACY_IMPROVEMENTS.md) | Notes on improving transcription accuracy |
| [TAGALOG_REDUPLICATION_NOTES.md](TAGALOG_REDUPLICATION_NOTES.md) | Taglish preprocessing notes |

---

## License

This project is licensed under the [MIT License](LICENSE).

