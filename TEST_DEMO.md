# Demo Test Guide

## Quick Demo Test

### 1. CLI Test
```bash
cd whisper-mowd
..\whisper_env_py311\Scripts\activate
python src/cli.py --audio data/audio/20250429_112153_saqt.mp3 --output output/
```

### 2. Web Demo Test
```bash
cd demo
..\whisper_env_py311\Scripts\activate
python app_demo.py
# Open http://localhost:8000
# Password: whisper2025
```

## Expected Results
- CLI should transcribe the audio file successfully
- Web demo should start on port 8000
- Both demos show security features in action

## Files Available for Demo
- Audio sample 1: `20250429_112153_saqt.mp3` (with transcript and summary)
- Audio sample 2: `20250502_095356_vaccine.mp3` (with transcript and summary)