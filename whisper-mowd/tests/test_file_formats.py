#!/usr/bin/env python
"""
Test script to verify supported file formats
"""

import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.transcription.file_converter import AudioFileConverter

def test_format_support():
    """Test which formats are recognized as needing conversion"""
    converter = AudioFileConverter()
    
    # Test video formats
    print("VIDEO FORMATS:")
    video_formats = ['.mp4', '.mkv', '.avi', '.mov', '.flv', '.webm', '.wmv', '.mpg', '.mpeg', 
                    '.3gp', '.3g2', '.m4v', '.f4v', '.f4p', '.ogv', '.asf', '.rm', '.rmvb', 
                    '.vob', '.ts', '.mts', '.m2ts', '.divx', '.xvid']
    
    for ext in video_formats:
        test_file = f"test{ext}"
        needs_conversion = converter.needs_conversion(test_file)
        print(f"  {ext}: {'[SUPPORTED] Needs conversion' if needs_conversion else '[ERROR] No conversion'}")
    
    print("\nAUDIO FORMATS:")
    audio_formats = ['.mp3', '.wav', '.m4a', '.ogg', '.flac', '.opus', '.amr', '.ac3', '.dts', 
                    '.ape', '.wv', '.tak', '.tta', '.aiff', '.au', '.ra', '.mka', '.m4b', '.spx',
                    '.aac', '.wma']
    
    for ext in audio_formats:
        test_file = f"test{ext}"
        needs_conversion = converter.needs_conversion(test_file)
        if ext in ['.mp3', '.wav']:
            print(f"  {ext}: {'[OK] Whisper compatible (no conversion)' if not needs_conversion else '[ERROR] Should not need conversion'}")
        else:
            print(f"  {ext}: {'[SUPPORTED] Needs conversion' if needs_conversion else '[ERROR] No conversion'}")
    
    print("\nSUMMARY:")
    print(f"Total video formats supported: {len(video_formats)}")
    print(f"Total audio formats supported: {len(audio_formats)}")
    print(f"Total formats: {len(video_formats) + len(audio_formats)}")

if __name__ == "__main__":
    test_format_support()