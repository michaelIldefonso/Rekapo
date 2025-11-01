# Rekapo

Meeting Summarizer API with near real-time transcription and Taglish support.

## Features

- 🎤 Real-time transcription with faster-whisper
- 🌐 WebSocket support for mobile voice chunks
- 🔊 VAD-based audio segmentation
- 🇵🇭 Taglish support (Tagalog + English)
- 📝 Meeting session management
- 👤 User authentication via Google OAuth
- 🖼️ Profile photo upload
- ✏️ Customizable usernames

## API Documentation

- **Main API**: See `/docs` when server is running for interactive documentation
- **User Profile API**: See [USER_PROFILE_API.md](USER_PROFILE_API.md) for profile management endpoints
- **Mobile Integration**: See [MOBILE_INTEGRATION.md](MOBILE_INTEGRATION.md)

## Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables (create `.env` file):
```env
DATABASE_URL=sqlite:///./rekapo.db
JWT_SECRET=your_secret_key_here
GOOGLE_CLIENT_ID=your_google_client_id
```

3. Run the server:
```bash
uvicorn main:app --reload
```

4. Access the API documentation at: `http://localhost:8000/docs`

## New User Profile Endpoints

### Change Username
```bash
PATCH /api/users/me/username
Authorization: Bearer {token}
Content-Type: application/json

{
  "username": "new_username"
}
```

### Upload Profile Photo
```bash
PATCH /api/users/me/photo
Authorization: Bearer {token}
Content-Type: multipart/form-data

file: [image file]
```

### Get Current User Profile
```bash
GET /api/users/me
Authorization: Bearer {token}
```

See [USER_PROFILE_API.md](USER_PROFILE_API.md) for complete documentation.

## Project Structure

```
.
├── main.py                 # FastAPI application entry point
├── routes/
│   ├── auth.py            # Authentication endpoints
│   ├── users.py           # User profile endpoints
│   └── whisper.py         # Transcription endpoints
├── db/
│   └── db.py              # Database models and connection
├── schemas/
│   └── schemas.py         # Pydantic models
├── utils/
│   └── utils.py           # Utility functions
├── ai_models/
│   ├── whisper/           # Whisper inference
│   └── llm/               # LLM integration
├── uploads/               # User uploaded files
│   └── profile_photos/    # Profile photos storage
└── tests/                 # Test files
```

## License

MIT
