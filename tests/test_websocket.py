"""
Module: tests/test_websocket.py.

This module contains test coverage and regression validation.
"""

import asyncio
import websockets
import json
import base64
from pathlib import Path

async def test_websocket_with_audio(audio_file_path=None):
    """
    Test the WebSocket transcription endpoint with real audio data.
    If no audio file is provided, you can record or use a sample.
    """
    uri = "ws://127.0.0.1:8000/api/ws/transcribe"
    
    # If you have an audio file, provide its path
    if audio_file_path and Path(audio_file_path).exists():
        with open(audio_file_path, "rb") as f:
            audio_bytes = f.read()
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
        filename = Path(audio_file_path).name
    else:
        print("No audio file provided. Please provide a valid .wav or .mp3 file path.")
        print("Example: python test_websocket.py path/to/audio.wav")
        return
    
    async with websockets.connect(uri) as websocket:
        # Wait for connection confirmation
        response = await websocket.recv()
        print(f"Connected: {response}")
        
        # Send audio data
        message = {
            "session_id": 1,
            "segment_number": 1,
            "audio": audio_base64,
            "filename": filename,
            "language": None,  # Auto-detect
            "model": "small"   # Use small model for faster testing
        }
        
        print(f"Sending audio file: {filename}")
        await websocket.send(json.dumps(message))
        
        # Receive responses
        while True:
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                data = json.loads(response)
                print(f"\nReceived: {json.dumps(data, indent=2)}")
                
                if data.get("status") == "success":
                    print(f"\nTranscription: {data.get('transcription')}")
                    break
                elif data.get("status") == "error":
                    print(f"\nError: {data.get('message')}")
                    break
            except asyncio.TimeoutError:
                print("Timeout waiting for response")
                break

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        audio_path = sys.argv[1]
    else:
        # Prompt for audio file path
        audio_path = input("Enter path to audio file (.wav, .mp3, etc.): ").strip()
    
    asyncio.run(test_websocket_with_audio(audio_path))

