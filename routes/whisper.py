from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
import json
import base64
import os
from pathlib import Path
from datetime import datetime

from ai_models.whisper.inference import transcribe_audio_file
from ai_models.translator.inference import auto_detect_and_translate
from ai_models.llm.llm import translate_taglish_to_english
from ai_models.summarizer.inference import summarize_transcriptions
from services.services import ConnectionManager
from db.db import get_db, RecordingSegment, Summary, Session as DBSession, SessionLocal
from schemas.schemas import AudioChunkMessage, TranscriptionResponse
from config.config import R2_ENABLED, R2_AUDIO_PREFIX
from storage.storage import r2_client

router = APIRouter()
manager = ConnectionManager()

# Directory to store audio files (fallback for local storage)
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
        "model": "small",  # optional: tiny, base, small, medium, large-v3
        "temperature": 0.2,  # optional: sampling temperature (lower = more deterministic)
        "repetition_penalty": 1.1,  # optional: penalty for repeated tokens
        "no_repeat_ngram_size": 3  # optional: prevent repeating n-grams
    }
    
    Response format:
    {
        "status": "processing" | "success" | "error" | "summary",
        "message": "...",
        "session_id": 123,
        "segment_number": 1,
        "transcription": "...",  # Original transcription
        "english_translation": "...",  # English translation
        "language": "tl",  # detected language
        "language_probability": 0.95,
        "duration": 3.5,
        "segments": [...]  # detailed segments with timestamps
        
        # For summary (every 10 chunks):
        "summary": "...",  # Summary of last 10 chunks
        "chunk_count": 10,
        "is_summary": true
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
                
                # Determine content type for audio
                content_type_map = {
                    '.wav': 'audio/wav',
                    '.mp3': 'audio/mpeg',
                    '.m4a': 'audio/mp4',
                    '.ogg': 'audio/ogg',
                    '.webm': 'audio/webm'
                }
                content_type = content_type_map.get(suffix.lower(), 'audio/wav')
                
                # Variable to track if we need to clean up temp file
                temp_file_to_cleanup = None
                
                if R2_ENABLED:
                    # Upload to R2 for permanent storage
                    r2_key = f"{R2_AUDIO_PREFIX}/session_{session_id}/segment_{segment_number}{suffix}"
                    audio_path_str = r2_client.upload_file(
                        file_content=audio_data,
                        key=r2_key,
                        content_type=content_type
                    )
                    
                    # Whisper needs a local file, so create a temporary one
                    temp_audio_path = AUDIO_STORAGE_DIR / f"temp_session_{session_id}_segment_{segment_number}{suffix}"
                    temp_audio_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(temp_audio_path, "wb") as f:
                        f.write(audio_data)
                    
                    # Use temp file for transcription
                    audio_path = temp_audio_path
                    temp_file_to_cleanup = temp_audio_path
                else:
                    # Save to local storage (permanent)
                    audio_path = AUDIO_STORAGE_DIR / f"session_{session_id}" / f"segment_{segment_number}{suffix}"
                    audio_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(audio_path, "wb") as f:
                        f.write(audio_data)
                    audio_path_str = str(audio_path)
                
                # Transcribe with faster-whisper
                language = message.get("language", None)  # Auto-detect Tagalog/English
                model = message.get("model", "small")
                
                # Get optional generation parameters for improved quality
                temperature = message.get("temperature", 0.2)
                repetition_penalty = message.get("repetition_penalty", 1.1)
                no_repeat_ngram_size = message.get("no_repeat_ngram_size", 3)
                
                result = transcribe_audio_file(
                    str(audio_path),
                    model_name_or_path=model,
                    language=language,
                    device="cuda",  # Use GPU
                    vad_filter=False,  # VAD handled on frontend
                    temperature=temperature,
                    repetition_penalty=repetition_penalty,
                    no_repeat_ngram_size=no_repeat_ngram_size
                )
                
                # Force detected language to be either Tagalog or English
                # If Whisper detects another language, default to Tagalog
                if result["language"] not in ["tl", "en"]:
                    result["language"] = "tl"  # Default to Tagalog for non-English
                
                # Translate to English using LLM (better for Taglish code-switching)
                english_translation = None
                
                try:
                    # Use LLM for Taglish translation (handles code-switching better than mBART)
                    translation_result = translate_taglish_to_english(
                        text=result["text"],
                        device="cuda",  # GPU with CUDA 13.0
                        max_new_tokens=256
                    )
                    english_translation = translation_result["translated_text"]
                except Exception as e:
                    print(f"Translation error: {e}")
                    # Continue without translation if it fails
                    english_translation = result["text"]
                
                # Send success response to user immediately
                response = {
                    "status": "success",
                    "message": "Transcription completed",
                    "session_id": session_id,
                    "segment_number": segment_number,
                    "transcription": result["text"],
                    "english_translation": english_translation,
                    "language": result["language"],
                    "language_probability": result["language_probability"],
                    "duration": result["duration"],
                    "segments": result["segments"]
                }
                
                await websocket.send_json(response)
                
                # After sending to user, save to database
                try:
                    db = SessionLocal()
                    recording_segment = RecordingSegment(
                        session_id=session_id,
                        segment_number=segment_number,
                        audio_path=audio_path_str,  # Store R2 URL or local path
                        transcript_text=result["text"],
                        english_translation=english_translation
                    )
                    db.add(recording_segment)
                    db.commit()
                    db.close()
                except Exception as e:
                    print(f"Database save error: {e}")
                finally:
                    # Clean up temporary file if using R2
                    if temp_file_to_cleanup and temp_file_to_cleanup.exists():
                        try:
                            temp_file_to_cleanup.unlink()
                        except Exception as e:
                            print(f"Failed to cleanup temp file: {e}")
                
                # Store transcription for summarization
                manager.add_transcription(session_id, {
                    "segment_number": segment_number,
                    "transcription": result["text"],
                    "english_translation": english_translation,
                    "language": result["language"],
                    "duration": result["duration"]
                })
                
                # Check if we should generate a summary (every 10 chunks)
                if manager.should_summarize(session_id, chunk_threshold=10):
                    try:
                        # Get all transcriptions for this session
                        transcriptions = manager.get_transcriptions(session_id)
                        
                        # Generate summary
                        summary_result = summarize_transcriptions(
                            transcriptions=transcriptions[-10:],  # Last 10 chunks
                            device="cuda",  # GPU with CUDA 13.0
                            max_length=200,
                            min_length=50
                        )
                        
                        # Send summary to client
                        await websocket.send_json({
                            "status": "summary",
                            "message": f"Summary generated for chunks {segment_number-9} to {segment_number}",
                            "session_id": session_id,
                            "summary": summary_result["summary"],
                            "chunk_count": summary_result["chunk_count"],
                            "is_summary": True
                        })
                        
                        # Save summary to database
                        try:
                            db = SessionLocal()
                            summary = Summary(
                                session_id=session_id,
                                chunk_range_start=segment_number - 9,
                                chunk_range_end=segment_number,
                                summary_text=summary_result["summary"]
                            )
                            db.add(summary)
                            db.commit()
                            db.close()
                        except Exception as e:
                            print(f"Summary database save error: {e}")
                        
                    except Exception as e:
                        print(f"Summarization error: {e}")
                        await websocket.send_json({
                            "status": "error",
                            "message": f"Summarization failed: {str(e)}",
                            "is_summary": True
                        })
                
                # Database operations are now handled inline above
                
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