# Demo App Updates Summary

## Changes Made

### 1. Increased File Size Limit
- **Previous**: 50MB maximum file size
- **New**: 150MB maximum file size
- **Changes**:
  - Updated `MAX_FILE_SIZE` constant in app_demo.py
  - Updated HTML template constraint display
  - Updated JavaScript client-side validation

### 2. Upgraded Whisper Model
- **Previous**: "tiny" model (39M parameters)
- **New**: "base" model (74M parameters)
- **Benefits**:
  - ~2x better transcription accuracy
  - Still fast performance, especially with faster-whisper
  - Good balance between speed and quality
  - Works well on CPU

## Technical Details

### File Size Support
- Server validates files up to 150MB
- Client-side JavaScript prevents upload of files >150MB
- Error messages automatically reflect the new limit

### Model Performance
- **Base model size**: ~100MB (vs 39MB for tiny)
- **Accuracy**: Significantly improved, especially for:
  - Accented speech
  - Background noise
  - Technical terminology
- **Speed**: Still fast with faster-whisper implementation
  - ~4x faster than original OpenAI implementation
  - Only ~2x slower than tiny model

### Testing Recommendations
1. Test with various file sizes (100-150MB files)
2. Compare transcription quality between old (tiny) and new (base) model
3. Monitor initial model loading time (slightly longer but still reasonable)
4. Test with challenging audio:
   - Multiple speakers
   - Background noise
   - Different accents
   - Technical content

## Usage Notes
- The demo still uses faster-whisper if available (for speed)
- Falls back to openai-whisper if faster-whisper not installed
- All 45 file formats are still supported
- File conversion still works for formats like .mkv