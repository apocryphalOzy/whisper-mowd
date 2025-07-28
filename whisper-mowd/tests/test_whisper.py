import os
import sys
from pathlib import Path

# Adjust path to import from src
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.transcription.whisper_service import WhisperTranscriber
except ImportError as e:
    print(f"Error importing WhisperTranscriber: {e}")
    print("Ensure faster-whisper is installed and src directory is in PYTHONPATH.")
    sys.exit(1)

def main():
    print("Testing WhisperTranscriber (using faster-whisper)...")

    # Use the 'tiny' model for quick testing
    model_size = "tiny"
    try:
        transcriber = WhisperTranscriber(model_size=model_size)
    except Exception as e:
        print(f"Error initializing WhisperTranscriber: {e}")
        return

    # Construct path to audio file relative to this script's parent directory
    # Assumes saqt.mp3 is in the main project root (one level up from tests/)
    audio_file_path = project_root.parent / "saqt.mp3"

    if not audio_file_path.exists():
        print(f"Error: Audio file {audio_file_path} not found")
        return

    print(f"Transcribing {audio_file_path.name} using '{model_size}' model...")
    try:
        result = transcriber.transcribe(str(audio_file_path))
        transcript_text = transcriber.get_text(result)
        language = transcriber.get_detected_language(result)

        print(f"\nDetected language: {language}")
        print("\nTranscription result:")
        print(transcript_text if transcript_text else "[No text transcribed]")
        
        if transcript_text:
             print("\nTest completed successfully!")
        else:
             print("\nTest completed, but no text was transcribed.")

    except Exception as e:
        print(f"\nError during transcription: {e}")

if __name__ == "__main__":
    main() 