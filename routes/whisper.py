from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
import json
import base64
import os
import asyncio
import unicodedata
from pathlib import Path
from datetime import datetime
from contextlib import asynccontextmanager

from ai_models.whisper.inference import transcribe_audio_file
from ai_models.translator.inference import auto_detect_and_translate, translate_text
from ai_models.llm.llm import translate_taglish_to_english
from ai_models.summarizer.inference import summarize_transcriptions
from services.services import ConnectionManager
from db.db import get_db, RecordingSegment, Summary, Session as DBSession, SessionLocal
from schemas.schemas import AudioChunkMessage, TranscriptionResponse
from config.config import R2_ENABLED, R2_AUDIO_PREFIX, TRANSLATION_MODEL, ENABLE_TAGLISH_PREPROCESSING
from storage.storage import r2_client

router = APIRouter()
manager = ConnectionManager()

# Directory to store audio files (fallback for local storage)
AUDIO_STORAGE_DIR = Path("audio")
AUDIO_STORAGE_DIR.mkdir(exist_ok=True)

# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def log_to_mobile(message_type: str, data: dict, session_id: str = None):
    """Log messages being sent to mobile app with colored output"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    if message_type == "connected":
        print(f"{Colors.GREEN}[{timestamp}] 📱 → MOBILE: Connection established{Colors.ENDC}")
    
    elif message_type == "processing":
        print(f"{Colors.CYAN}[{timestamp}] 📱 → MOBILE [{session_id}]: Processing segment...{Colors.ENDC}")
    
    elif message_type == "transcription":
        text = data.get('transcription', '')[:60]
        translation = data.get('english_translation', '')[:60]
        lang = data.get('language', '')
        seg_num = data.get('segment_number', '')
        print(f"{Colors.GREEN}[{timestamp}] 📱 → MOBILE [{session_id}] Segment #{seg_num}:{Colors.ENDC}")
        print(f"  {Colors.BOLD}Original ({lang}):{Colors.ENDC} {text}...")
        print(f"  {Colors.BOLD}Translation:{Colors.ENDC} {translation}...")
    
    elif message_type == "summary":
        summary = data.get('summary', '')[:80]
        chunk_count = data.get('chunk_count', '')
        print(f"{Colors.BLUE}[{timestamp}] 📱 → MOBILE [{session_id}]: Summary (chunks: {chunk_count}):{Colors.ENDC}")
        print(f"  {summary}...")
    
    elif message_type == "skipped":
        reason = data.get('message', '')
        print(f"{Colors.YELLOW}[{timestamp}] 📱 → MOBILE [{session_id}]: Skipped - {reason}{Colors.ENDC}")
    
    elif message_type == "error":
        error = data.get('message', '')
        print(f"{Colors.RED}[{timestamp}] 📱 → MOBILE: Error - {error}{Colors.ENDC}")

# Print active translation configuration
print(f"🌐 Translation Model: {TRANSLATION_MODEL.upper()}")
print(f"📝 Taglish Preprocessing: {'ENABLED' if ENABLE_TAGLISH_PREPROCESSING else 'DISABLED'}")


def translate_to_english(text: str, detected_lang: str = "tl") -> str:
    """
    Unified translation function that routes to NLLB or Qwen based on config.
    
    Args:
        text: Text to translate
        detected_lang: Detected language code ('tl', 'en', etc.)
    
    Returns:
        Translated English text
    """
    if TRANSLATION_MODEL == "qwen":
        # Use Qwen LLM (heavier, better quality)
        result = translate_taglish_to_english(
            text=text,
            device="cuda",
            max_new_tokens=512
        )
        return result["translated_text"]
    
    elif TRANSLATION_MODEL == "nllb":
        # Use NLLB-200 (lighter, faster)
        # Map Whisper language codes to NLLB codes
        lang_map = {'tl': 'tgl_Latn', 'en': 'eng_Latn'}
        source_lang = lang_map.get(detected_lang, 'tgl_Latn')
        
        # Skip translation if already English
        if detected_lang == 'en':
            return text
        
        result = translate_text(
            text=text,
            source_lang=source_lang,
            target_lang="eng_Latn",
            device="auto",
            use_preprocessing=ENABLE_TAGLISH_PREPROCESSING
        )
        return result["translated_text"]
    
    else:
        # Fallback: return original text
        print(f"⚠️  Unknown translation model: {TRANSLATION_MODEL}")
        return text


def is_valid_taglish_text(text: str) -> bool:
    """Check if text is valid Taglish (Latin + English characters)"""
    # Count valid characters vs invalid
    total_chars = 0
    invalid_chars = 0
    
    for char in text:
        # Skip whitespace
        if char.isspace():
            continue
        
        total_chars += 1
        char_code = ord(char)
        
        # Allow standard ASCII (letters, numbers, punctuation)
        if char_code < 128:
            continue
        
        # Allow Latin Extended-A and Extended-B (accented characters like é, ñ, etc.)
        if 0x0100 <= char_code <= 0x024F:
            continue
        
        # Reject IPA phonetic symbols
        if (0x0250 <= char_code <= 0x02AF or  # IPA Extensions
            0x1D00 <= char_code <= 0x1D7F or  # Phonetic Extensions
            0x1D80 <= char_code <= 0x1DBF):   # Phonetic Extensions Supplement
            invalid_chars += 1
            continue
        
        # Reject CJK characters (Chinese, Japanese, Korean)
        if (0x4E00 <= char_code <= 0x9FFF or  # CJK Unified Ideographs
            0x3040 <= char_code <= 0x309F or  # Hiragana
            0x30A0 <= char_code <= 0x30FF or  # Katakana
            0x2E80 <= char_code <= 0x2EFF or  # CJK Radicals Supplement
            0x3400 <= char_code <= 0x4DBF):   # CJK Extension A
            invalid_chars += 1
            continue
        
        # Reject Arabic, Hebrew, and other Middle Eastern scripts
        if (0x0600 <= char_code <= 0x06FF or  # Arabic
            0x0590 <= char_code <= 0x05FF or  # Hebrew
            0x0700 <= char_code <= 0x074F):   # Syriac
            invalid_chars += 1
            continue
        
        # Reject South Asian scripts
        if (0x0900 <= char_code <= 0x097F or  # Devanagari
            0x0980 <= char_code <= 0x09FF or  # Bengali
            0x0A00 <= char_code <= 0x0A7F or  # Gurmukhi
            0x0A80 <= char_code <= 0x0AFF):   # Gujarati
            invalid_chars += 1
            continue
        
        # Reject replacement character and other invalid Unicode
        if char_code == 0xFFFD:  # Replacement character �
            invalid_chars += 1
            continue
        
        # Check Unicode category for other non-standard characters
        category = unicodedata.category(char)
        if category in ['Cn', 'Co', 'Cs']:  # Unassigned, Private use, Surrogate
            invalid_chars += 1
    
    # Reject if more than 30% of characters are invalid, or if text is mostly invalid
    if total_chars == 0:
        return False
    
    invalid_ratio = invalid_chars / total_chars
    return invalid_ratio < 0.3


async def cleanup_invalid_segment(temp_file_to_cleanup, audio_path, audio_path_str, session_id):
    """Clean up files for invalid/empty segments"""
    # Clean up temporary file
    if temp_file_to_cleanup and temp_file_to_cleanup.exists():
        try:
            temp_file_to_cleanup.unlink()
        except Exception as e:
            print(f"Failed to cleanup temp file: {e}")
    
    # Clean up local storage file if using local storage (not R2)
    if not R2_ENABLED and isinstance(audio_path, Path) and audio_path.exists():
        try:
            audio_path.unlink()
        except Exception as e:
            print(f"Failed to cleanup local file: {e}")
    
    # Clean up R2 file if it was uploaded
    if R2_ENABLED and audio_path_str:
        try:
            r2_client.delete_file(audio_path_str)
        except Exception as e:
            print(f"Failed to cleanup R2 file: {e}")

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
        "language": null,  # optional, auto-detect if null (tl/en)
        "model": "small",  # optional: tiny, base, small, medium, large-v3
        "beam_size": 5,  # optional: 3-10, higher = more accurate but slower
        "temperature": 0.2,  # optional: 0.0-1.0, lower = more deterministic
        "repetition_penalty": 1.1,  # optional: penalty for repeated tokens
        "no_repeat_ngram_size": 3,  # optional: prevent repeating n-grams
        "initial_prompt": "Meeting in Tagalog and English."  # optional: context for better accuracy
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
    
    # Track session ID for this connection
    current_session_id = None
    
    try:
        connection_msg = {
            "status": "connected",
            "message": "WebSocket connected. Ready for meeting recording."
        }
        log_to_mobile("connected", connection_msg)
        await websocket.send_json(connection_msg)
        
        while True:
            # Receive audio chunk from mobile client
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                
                # Validate required fields
                if "session_id" not in message:
                    error_msg = {
                        "status": "error",
                        "message": "Missing 'session_id' field"
                    }
                    log_to_mobile("error", error_msg)
                    await websocket.send_json(error_msg)
                    continue
                
                if "audio" not in message:
                    error_msg = {
                        "status": "error",
                        "message": "Missing 'audio' field"
                    }
                    log_to_mobile("error", error_msg)
                    await websocket.send_json(error_msg)
                    continue
                
                session_id = message["session_id"]
                client_segment_number = message.get("segment_number", None)
                
                # Initialize session in manager if first time seeing this session_id
                if current_session_id is None:
                    current_session_id = session_id
                    # Initialize the session in manager to track segments
                    if session_id not in manager.active_sessions:
                        manager.active_sessions[session_id] = {
                            "start_time": datetime.now(),
                            "segment_count": 0,
                            "connections": [websocket]
                        }
                        manager.session_transcriptions[session_id] = []
                        print(f"{Colors.GREEN}📝 Initialized session {session_id} in manager{Colors.ENDC}")
                
                # For processing messages and file naming, we may need a temporary number
                # The real segment_number will be assigned after validation
                temp_segment_id = client_segment_number or datetime.now().timestamp()
                
                # Send processing status
                processing_msg = {
                    "status": "processing",
                    "message": f"Processing segment...",
                    "session_id": session_id
                }
                log_to_mobile("processing", processing_msg, session_id)
                await websocket.send_json(processing_msg)
                
                # Decode base64 audio
                audio_data = base64.b64decode(message["audio"])
                
                # Save audio file permanently for the session
                filename = message.get("filename", f"segment_{temp_segment_id}.wav")
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
                    # Upload to R2 for permanent storage (will be deleted if validation fails)
                    r2_key = f"{R2_AUDIO_PREFIX}/session_{session_id}/segment_{temp_segment_id}{suffix}"
                    audio_path_str = r2_client.upload_file(
                        file_content=audio_data,
                        key=r2_key,
                        content_type=content_type
                    )
                    
                    # Whisper needs a local file, so create a temporary one
                    temp_audio_path = AUDIO_STORAGE_DIR / f"temp_session_{session_id}_segment_{temp_segment_id}{suffix}"
                    temp_audio_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(temp_audio_path, "wb") as f:
                        f.write(audio_data)
                    
                    # Use temp file for transcription
                    audio_path = temp_audio_path
                    temp_file_to_cleanup = temp_audio_path
                else:
                    # Save to local storage (permanent - will be deleted if validation fails)
                    audio_path = AUDIO_STORAGE_DIR / f"session_{session_id}" / f"segment_{temp_segment_id}{suffix}"
                    audio_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(audio_path, "wb") as f:
                        f.write(audio_data)
                    audio_path_str = str(audio_path)
                
                # Transcribe with faster-whisper
                language = message.get("language", None)  # Auto-detect Tagalog/English
                model = message.get("model", None)  # None = use fine-tuned model from config
                
                # Get optional generation parameters for improved quality
                temperature = message.get("temperature", 0.2)
                repetition_penalty = message.get("repetition_penalty", 1.1)
                no_repeat_ngram_size = message.get("no_repeat_ngram_size", 3)
                beam_size = message.get("beam_size", 5)  # Higher = more accurate but slower
                
                # Build initial prompt from recent transcriptions for better context
                # Whisper uses this to maintain consistency across chunks (names, terms, etc.)
                initial_prompt = message.get("initial_prompt", None)
                if initial_prompt is None:
                    # Get last 3 transcriptions for context
                    recent_transcriptions = manager.get_recent_transcriptions(session_id, count=3)
                    if recent_transcriptions:
                        # Build prompt from recent text (keep it short - max ~224 tokens)
                        context_texts = [t.get("transcription", "") for t in recent_transcriptions]
                        initial_prompt = " ".join(context_texts)
                        # Limit to ~200 characters to avoid token limit
                        if len(initial_prompt) > 200:
                            initial_prompt = initial_prompt[-200:]
                        print(f"🔗 Using context from last {len(recent_transcriptions)} chunks: {initial_prompt[:80]}...")
                    else:
                        print(f"📝 First chunk - no context available yet")
                
                result = transcribe_audio_file(
                    str(audio_path),
                    model_name_or_path=model,
                    language=language,
                    device="cuda",  # Use GPU
                    vad_filter=True,  # Enable backend VAD (Silero) for better silence detection
                    beam_size=beam_size,
                    temperature=temperature,
                    repetition_penalty=repetition_penalty,
                    no_repeat_ngram_size=no_repeat_ngram_size,
                    initial_prompt=initial_prompt
                )
                
                # Force detected language to be either Tagalog or English
                # If Whisper detects another language, default to Tagalog
                if result["language"] not in ["tl", "en"]:
                    result["language"] = "tl"  # Default to Tagalog for non-English
                
                # Check if transcription is empty (skip empty segments)
                if not result["text"] or not result["text"].strip():
                    print(f"Skipping empty segment for session {session_id}")
                    await cleanup_invalid_segment(temp_file_to_cleanup, audio_path, audio_path_str, session_id)
                    skip_msg = {
                        "status": "skipped",
                        "message": "Segment was empty and was not saved",
                        "session_id": session_id
                    }
                    log_to_mobile("skipped", skip_msg, session_id)
                    await websocket.send_json(skip_msg)
                    continue
                
                # Check if transcription contains non-Taglish characters
                if not is_valid_taglish_text(result["text"]):
                    print(f"Skipping segment - contains non-Taglish characters")
                    await cleanup_invalid_segment(temp_file_to_cleanup, audio_path, audio_path_str, session_id)
                    skip_msg = {
                        "status": "skipped",
                        "message": "Segment contains non-Taglish characters and was not saved",
                        "session_id": session_id
                    }
                    log_to_mobile("skipped", skip_msg, session_id)
                    await websocket.send_json(skip_msg)
                    continue
                
                # Assign the official segment number after validation
                # Only valid segments get official numbers
                if client_segment_number is not None:
                    segment_number = client_segment_number
                    # Update manager's counter to match client's segment number
                    if session_id in manager.active_sessions:
                        manager.active_sessions[session_id]["segment_count"] = segment_number
                else:
                    segment_number = manager.increment_segment_count(session_id)
                
                # Rename files to use official segment number (if temp ID was used)
                if client_segment_number is None:
                    if R2_ENABLED:
                        # Rename R2 file to use official segment number
                        try:
                            old_r2_key = f"{R2_AUDIO_PREFIX}/session_{session_id}/segment_{temp_segment_id}{suffix}"
                            new_r2_key = f"{R2_AUDIO_PREFIX}/session_{session_id}/segment_{segment_number}{suffix}"
                            
                            # Use efficient server-side copy instead of download/upload
                            audio_path_str = r2_client.copy_file(old_r2_key, new_r2_key)
                            
                            # Delete old file
                            r2_client.delete_file(old_r2_key)
                            print(f"Renamed R2 file from {old_r2_key} to {new_r2_key}")
                        except Exception as e:
                            print(f"Failed to rename R2 file: {e}")
                            # Keep using the temp_segment_id path if rename fails
                    else:
                        # Rename local file to use official segment number
                        try:
                            new_audio_path = AUDIO_STORAGE_DIR / f"session_{session_id}" / f"segment_{segment_number}{suffix}"
                            if audio_path.exists():
                                audio_path.rename(new_audio_path)
                                audio_path = new_audio_path
                                audio_path_str = str(audio_path)
                                print(f"Renamed local file to segment_{segment_number}{suffix}")
                        except Exception as e:
                            print(f"Failed to rename local file: {e}")
                            # Keep using the temp_segment_id path if rename fails
                
                # Translate to English using configured model (NLLB or Qwen)
                async def translate_async():
                    try:
                        # Run translation in thread pool to not block event loop
                        loop = asyncio.get_event_loop()
                        english_text = await loop.run_in_executor(
                            None,
                            translate_to_english,
                            result["text"],
                            result["language"]
                        )
                        return english_text
                    except Exception as e:
                        print(f"Translation error: {e}")
                        return result["text"]
                
                english_translation = await translate_async()
                
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
                
                log_to_mobile("transcription", response, session_id)
                await websocket.send_json(response)
                
                # After sending to user, save to database
                db = SessionLocal()
                try:
                    recording_segment = RecordingSegment(
                        session_id=session_id,
                        segment_number=segment_number,
                        audio_path=audio_path_str,
                        transcript_text=result["text"],
                        english_translation=english_translation
                    )
                    db.add(recording_segment)
                    db.commit()
                except Exception as e:
                    print(f"Database save error: {e}")
                    db.rollback()
                finally:
                    db.close()
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
                
                # Get current session info for logging
                current_segment_count = manager.active_sessions.get(session_id, {}).get("segment_count", 0)
                total_transcriptions = len(manager.get_transcriptions(session_id))
                
                print(f"{Colors.BOLD}📊 Summarization Check [{session_id}]:{Colors.ENDC}")
                print(f"  • Current segment: #{segment_number}")
                print(f"  • Total segments in session: {current_segment_count}")
                print(f"  • Transcriptions buffered: {total_transcriptions}")
                print(f"  • Should summarize? (segment % 10 == 0): {current_segment_count % 10 == 0}")
                
                # Check if we should generate a summary (every 10 chunks)
                if manager.should_summarize(session_id, chunk_threshold=10):
                    print(f"{Colors.BLUE}{Colors.BOLD}🔄 TRIGGERING SUMMARIZATION for session {session_id} (segment {segment_number}){Colors.ENDC}")
                    try:
                        # Get all transcriptions for this session
                        transcriptions = manager.get_transcriptions(session_id)
                        print(f"{Colors.CYAN}  • Fetched {len(transcriptions)} transcriptions{Colors.ENDC}")
                        print(f"{Colors.CYAN}  • Summarizing last 10 chunks...{Colors.ENDC}")
                        
                        # Generate summary
                        summary_result = summarize_transcriptions(
                            transcriptions=transcriptions[-10:],  # Last 10 chunks
                            device="cuda",  # GPU with CUDA 13.0
                            max_length=200,
                            min_length=50
                        )
                        
                        print(f"{Colors.GREEN}  ✅ Summary generated: {summary_result['summary'][:100]}...{Colors.ENDC}")
                        
                        # Send summary to client
                        summary_msg = {
                            "status": "summary",
                            "message": f"Summary generated for chunks {segment_number-9} to {segment_number}",
                            "session_id": session_id,
                            "summary": summary_result["summary"],
                            "chunk_count": summary_result["chunk_count"],
                            "is_summary": True
                        }
                        
                        print(f"{Colors.BLUE}{Colors.BOLD}📤 SENDING SUMMARY TO FRONTEND:{Colors.ENDC}")
                        print(f"{Colors.CYAN}  • Session ID: {session_id}{Colors.ENDC}")
                        print(f"{Colors.CYAN}  • Chunk Range: {segment_number-9} to {segment_number}{Colors.ENDC}")
                        print(f"{Colors.CYAN}  • Summary Length: {len(summary_result['summary'])} chars{Colors.ENDC}")
                        print(f"{Colors.CYAN}  • Full Summary: {summary_result['summary']}{Colors.ENDC}")
                        print(f"{Colors.CYAN}  • WebSocket Connected: {websocket.client_state.name}{Colors.ENDC}")
                        
                        log_to_mobile("summary", summary_msg, session_id)
                        await websocket.send_json(summary_msg)
                        
                        print(f"{Colors.GREEN}  ✅ Summary sent to frontend successfully{Colors.ENDC}")
                        
                        # Save summary to database
                        db_summary = SessionLocal()
                        try:
                            summary = Summary(
                                session_id=session_id,
                                chunk_range_start=segment_number - 9,
                                chunk_range_end=segment_number,
                                summary_text=summary_result["summary"]
                            )
                            db_summary.add(summary)
                            db_summary.commit()
                            print(f"{Colors.GREEN}  ✅ Summary saved to database{Colors.ENDC}")
                        except Exception as e:
                            print(f"{Colors.RED}  ❌ Summary database save error: {e}{Colors.ENDC}")
                            db_summary.rollback()
                        finally:
                            db_summary.close()
                        
                    except Exception as e:
                        print(f"{Colors.RED}❌ Summarization error: {e}{Colors.ENDC}")
                        error_msg = {
                            "status": "error",
                            "message": f"Summarization failed: {str(e)}",
                            "is_summary": True
                        }
                        log_to_mobile("error", error_msg)
                        await websocket.send_json(error_msg)
                else:
                    print(f"{Colors.YELLOW}  ⏭️  Skipping summarization (not at 10-segment boundary){Colors.ENDC}")
                
                # Database operations are now handled inline above
                
            except json.JSONDecodeError:
                error_msg = {
                    "status": "error",
                    "message": "Invalid JSON format"
                }
                log_to_mobile("error", error_msg)
                await websocket.send_json(error_msg)
            except Exception as e:
                error_msg = {
                    "status": "error",
                    "message": f"Error: {str(e)}"
                }
                log_to_mobile("error", error_msg)
                await websocket.send_json(error_msg)
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("Client disconnected from meeting recording")
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)