"""
Simple test script to verify Whisper setup
"""
import os
import sys

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'whisper-mowd'))

print("Testing Whisper MOWD setup...")
print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}")

# Test imports
try:
    print("\nTesting imports...")
    from src.transcription.whisper_service import WhisperTranscriber
    print("✓ WhisperTranscriber imported successfully")
    
    from src.storage.local_storage import LocalStorage
    print("✓ LocalStorage imported successfully")
    
    from src.summarization.base_summarizer import NullSummarizer
    print("✓ NullSummarizer imported successfully")
    
    print("\nAll imports successful! The environment is set up correctly.")
    
    # Test if we can load Whisper
    print("\nTesting Whisper model loading...")
    transcriber = WhisperTranscriber(model_size="base")
    print("✓ Whisper transcriber initialized successfully")
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()