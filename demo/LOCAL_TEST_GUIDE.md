# Local Testing Guide - Whisper MOWD Demo

## Quick Start (5 minutes)

### 1. Set Up Environment

Open a command prompt in the whisper directory:

```cmd
cd demo
..\Scripts\activate
pip install -r requirements-demo.txt
```

### 2. Run the Demo

```cmd
python app_demo.py
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Loading Whisper model: tiny
Model loaded successfully
```

### 3. Test the Application

1. Open browser: http://localhost:8000
2. Enter password: `whisper2025`
3. Upload a test file from: `whisper-mowd\data\audio\`
   - Try: `20250429_112153_saqt.mp3` (already there)
4. Watch progress bar
5. Get transcription!

## What to Test

### ✅ Functionality Tests
- [ ] Password protection works
- [ ] File upload accepts MP3/WAV
- [ ] Progress bar updates
- [ ] Transcription completes
- [ ] Results display correctly
- [ ] Copy button works
- [ ] Download button works

### ⏱️ Performance Tests
- [ ] 2-minute audio: Should take <30 seconds
- [ ] 5-minute audio: Should take <60 seconds
- [ ] Memory usage stays reasonable
- [ ] No crashes with multiple uploads

### 🚫 Constraint Tests
- [ ] Try file >50MB (should reject)
- [ ] Upload 11 times (should hit limit)
- [ ] Wrong file type (should reject)
- [ ] Check if old files delete

## Common Issues

### "Module not found"
```cmd
pip install faster-whisper
# or if that fails:
pip install openai-whisper
```

### "Port already in use"
```cmd
# Change port in app_demo.py:
uvicorn.run(app, host="0.0.0.0", port=8001)
```

### "Out of memory"
- Close other applications
- Use tiny model (default)
- Process one file at a time

## Test Scenarios

### Scenario 1: Happy Path
1. Upload clear audio
2. Get accurate transcript
3. Download result
4. Upload another file

### Scenario 2: Edge Cases
1. Upload 49MB file (should work)
2. Upload 51MB file (should fail)
3. Upload .txt file (should fail)
4. Spam uploads (rate limit)

### Scenario 3: User Experience
1. Test on phone browser
2. Slow internet (throttle in DevTools)
3. Multiple tabs open
4. Back button behavior

## Performance Benchmarks

Record these for your demo:

| Audio Length | File Size | Processing Time | Accuracy |
|--------------|-----------|-----------------|----------|
| 1 minute | ___MB | ___seconds | Good/Fair/Poor |
| 2 minutes | ___MB | ___seconds | Good/Fair/Poor |
| 5 minutes | ___MB | ___seconds | Good/Fair/Poor |

## Pre-Deployment Checklist

Before moving to cloud:

- [ ] All tests pass locally
- [ ] Processing times acceptable
- [ ] UI works on mobile
- [ ] Error messages helpful
- [ ] Demo password changed in .env
- [ ] Sample audio files ready

## Next: Cloud Deployment

Once local testing passes:

1. **Commit your code**
   ```cmd
   git add demo/
   git commit -m "Add demo application"
   git push
   ```

2. **Choose hosting**
   - Oracle Cloud (free, complex)
   - Hetzner (€4.85, simple)
   - DigitalOcean ($6, familiar)

3. **Deploy**
   - Follow demo/README.md
   - Use deploy.sh script

---

**Tip**: Keep this window open while testing. Check off items as you go!