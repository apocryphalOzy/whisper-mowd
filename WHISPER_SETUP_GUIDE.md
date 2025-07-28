# Whisper Audio Transcription - Setup Guide

## Overview

This is a desktop application for transcribing audio files using OpenAI's Whisper model. No browser required!

## Requirements

- Windows 10/11
- Python 3.11 (already installed)
- Virtual environment (already set up)

## Quick Start

1. **Run the Application**
   - Double-click `RUN_WHISPER_DESKTOP.bat`
   - Or run from command line: `RUN_WHISPER_DESKTOP.bat`

2. **Using the Application**
   - Click "Select Audio File" to choose your audio
   - Supported formats: MP3, WAV, M4A, FLAC, OGG, MP4
   - Click "Transcribe Audio" to start
   - Wait for transcription (30-60 seconds typically)
   - Copy text or save to file

## Features

- **Multiple Models**: Choose from tiny, base, small, medium, or large
  - Tiny: Fastest, least accurate
  - Base: Good balance
  - Small/Medium: Better accuracy
  - Large: Best accuracy (requires more RAM)

- **Simple Interface**: No web browser needed
- **Progress Indication**: Shows when processing
- **Export Options**: Copy to clipboard or save as text file

## Troubleshooting

1. **"Whisper not installed" error**
   - Run: `whisper_env_py311\Scripts\activate`
   - Then: `pip install openai-whisper`

2. **Out of memory error**
   - Use a smaller model (tiny or base)
   - Close other applications

3. **Slow transcription**
   - Normal for longer audio files
   - Tiny model is fastest

## Project Structure

```
whisper/
├── whisper_desktop.py      # Desktop GUI application
├── RUN_WHISPER_DESKTOP.bat # Run the application
├── whisper_env_py311/      # Python 3.11 environment
└── whisper-mowd/           # Original project files
```

## Notes

- First run may take longer as it downloads the model
- Models are cached after first download
- Audio files are not uploaded anywhere - all processing is local

## Alternative: Command Line

If you prefer command line, you can use the original CLI:

```bash
cd whisper-mowd
python src/cli.py --audio path/to/audio.mp3
```

See `whisper-mowd/README.md` for CLI documentation.