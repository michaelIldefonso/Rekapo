from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
import json
import base64
import os
from pathlib import Path
from datetime import datetime

from ai_models.whisper.inference import transcribe_audio_file
from services.services import ConnectionManager
from db.db import get_db, RecordingSegment, Session as DBSession
from schemas.schemas import AudioChunkMessage, TranscriptionResponse

router = APIRouter()
manager = ConnectionManager()

# Directory to store audio files
AUDIO_STORAGE_DIR = Path("audiios")
AUDIO_STORAGE_DIR.mkdir(exist_ok=True)

@router.websocket("/ws/transcribe")
async def websocket_transcribe(websocket: WebSocket):
    """
    WebSocket endpoint for real-time meeting transcription.
    Designed for mobile voice recording with VAD-based chunking.
    
    Expected message format:
    {
        "session_id": 123,  # Database session ID
        "segment_number": 1,  # Incremental segment number
        "audio": "base64_encoded_audio_data",
        "filename": "chunk_1.wav",  # optional
        "language": null,  # optional, auto-detect if null
        "model": "small"  # optional: tiny, base, small, medium, large-v3
    }
    
    Response format:
    {
        "status": "processing" | "success" | "error",
        "message": "...",
        "session_id": 123,
        "segment_number": 1,
        "transcription": "...",  # Taglish transcription
        "english_translation": null,  # Will add translation later
        "language": "tl",  # detected language (Tagalog)
        "language_probability": 0.95,
        "duration": 3.5,
        "segments": [...]  # detailed segments with timestamps
    }
    """
    await manager.connect(websocket)
    
    try:
        await websocket.send_json({
            "status": "connected",
            "message": "WebSocket connected. Ready for meeting recording."
        })
        
        while True:
            # Receive audio chunk from mobile client
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                
                # Validate required fields
                if "session_id" not in message:
                    await websocket.send_json({
                        "status": "error",
                        "message": "Missing 'session_id' field"
                    })
                    continue
                
                if "audio" not in message:
                    await websocket.send_json({
                        "status": "error",
                        "message": "Missing 'audio' field"
                    })
                    continue
                
                session_id = message["session_id"]
                segment_number = message.get("segment_number", manager.increment_segment_count(session_id))
                
                # Send processing status
                await websocket.send_json({
                    "status": "processing",
                    "message": f"Processing segment {segment_number}...",
                    "session_id": session_id,
                    "segment_number": segment_number
                })
                
                # Decode base64 audio
                audio_data = base64.b64decode(message["audio"])
                
                # Save audio file permanently for the session
                filename = message.get("filename", f"segment_{segment_number}.wav")
                suffix = Path(filename).suffix or ".wav"
                audio_path = AUDIO_STORAGE_DIR / f"session_{session_id}" / f"segment_{segment_number}{suffix}"
                audio_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(audio_path, "wb") as f:
                    f.write(audio_data)
                
                # Transcribe with faster-whisper
                language = message.get("language", None)  # Auto-detect Tagalog/English
                model = message.get("model", "small")
                
                result = transcribe_audio_file(
                    str(audio_path),
                    model_name_or_path=model,
                    language=language,
                    vad_filter=True  # Filter non-speech
                )
                
                # TODO: Add English translation using LLM
                # english_translation = await translate_to_english(result["text"])
                
                # Send success response
                response = {
                    "status": "success",
                    "message": "Transcription completed",
                    "session_id": session_id,
                    "segment_number": segment_number,
                    "transcription": result["text"],
                    "english_translation": None,  # Will implement translation
                    "language": result["language"],
                    "language_probability": result["language_probability"],
                    "duration": result["duration"],
                    "segments": result["segments"]
                }
                
                await websocket.send_json(response)
                
                # Store in database (async operation, don't block)
                # This would need proper async DB session
                # For now, the route handler should save to DB separately
                
            except json.JSONDecodeError:
                await websocket.send_json({
                    "status": "error",
                    "message": "Invalid JSON format"
                })
            except Exception as e:
                await websocket.send_json({
                    "status": "error",
                    "message": f"Error: {str(e)}"
                })
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("Client disconnected from meeting recording")
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)