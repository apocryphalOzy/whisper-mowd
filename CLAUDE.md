# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Plan & Review

### Before starting work
- You are always in plan mode to make a plan
- After you develop and get the plan, make sure you write the plan to .claude/tasks/TASK_NAME.md.
- The plan should be a detailed implementation plan and the reasoning behind them, as well as tasks broken down. 
- If the task requires external knowledge or a certain package, research to get the latest knowledge (Use Task tool for research)
- Don't over plan it, always think MVP.
- Once you write the plan, firstly ask me to review it. Do not continue until I approve the plan 

### While Implementing
- You should update the plan as you work.
- After you complete tasks in the plan, you should update and append detailed descriptions of the changes you made, so following tasks can be easily handed over to other engineers.

## Project Overview

Whisper MOWD is a cloud-based audio transcription and summarization service that uses OpenAI's Whisper model for speech-to-text and various LLMs for summarization. The project targets educational institutions, starting with K-12 schools.

## Key Commands

### Setup and Installation
```bash
# Create virtual environment (if not already created)
python -m venv whisper_env

# Activate virtual environment
# Windows:
whisper_env\Scripts\activate
# Linux/Mac:
source whisper_env/bin/activate

# Install dependencies
pip install -r whisper-mowd/requirements.txt

# Copy and configure environment variables
cp whisper-mowd/env-example.txt whisper-mowd/.env
# Edit .env file with your API keys and configuration
```

### Running the Application

#### Single File Processing
```bash
# Basic usage
python whisper-mowd/src/cli.py --audio path/to/audio.mp3

# With all options
python whisper-mowd/src/cli.py \
    --audio path/to/audio.mp3 \
    --output output/ \
    --model base \
    --summarizer openai \
    --storage local \
    --format mp3 \
    --lecture-id custom_id
```

#### Batch Processing
```bash
# Process all files in a directory
python whisper-mowd/scripts/process_batch.py \
    --directory path/to/audio/files \
    --output output/ \
    --model base \
    --summarizer openai

# Recursive processing with multiple workers
python whisper-mowd/scripts/process_batch.py \
    --directory path/to/audio/files \
    --recursive \
    --workers 4
```

### Testing
```bash
# Run the basic Whisper test
python whisper-mowd/tests/test_whisper.py

# Run all tests (if using pytest)
cd whisper-mowd
python -m pytest tests/
```

## Architecture Overview

### Core Components

1. **Transcription Service** (`src/transcription/`)
   - `whisper_service.py`: Main transcription logic using faster-whisper (with fallback to original whisper)
   - `file_converter.py`: Converts various audio/video formats to processable formats using ffmpeg
   - `utils.py`: Utility functions for transcription

2. **Summarization Service** (`src/summarization/`)
   - `base_summarizer.py`: Abstract base class for summarizers
   - `openai_summarizer.py`: OpenAI GPT-based summarization
   - `custom_llm.py`: Support for custom LLMs (Llama, Anthropic, etc.)

3. **Storage Layer** (`src/storage/`)
   - `local_storage.py`: Local file system storage
   - `aws_storage.py`: AWS S3 and DynamoDB integration

4. **CLI Interface** (`src/cli.py`)
   - Main entry point for command-line usage
   - Handles keyboard interrupts (Ctrl+C) for graceful cancellation
   - Coordinates transcription, summarization, and storage

### Data Flow

1. **Input**: Audio/video file → File converter (if needed)
2. **Transcription**: Processed audio → Whisper model → Transcript + timestamps
3. **Summarization**: Transcript → LLM (OpenAI/Custom) → Summary
4. **Storage**: All outputs saved to configured storage (local/AWS)
5. **Output**: Transcript, summary, and metadata files

### Directory Structure

```
data/
├── audio/          # Original audio files
├── transcripts/    # Generated transcripts (plain and with timestamps)
├── summaries/      # Generated summaries
└── metadata/       # JSON metadata for each processed file

output/             # CLI output directory for processed files
```

### Environment Variables

Key variables from `.env`:
- `WHISPER_MODEL_SIZE`: Model size (tiny, base, small, medium, large)
- `SUMMARIZER_TYPE`: Summarizer to use (openai, custom_llm, none)
- `STORAGE_MODE`: Storage backend (local, aws)
- `OPENAI_API_KEY`: Required for OpenAI summarization
- AWS credentials and bucket names for cloud storage

### Development Notes

1. **Model Loading**: Whisper models are lazy-loaded to optimize startup time
2. **Cancellation Support**: Transcription can be cancelled mid-process with Ctrl+C
3. **Format Support**: Handles various audio/video formats via ffmpeg conversion
4. **Batch Processing**: Supports parallel processing with configurable workers
5. **Error Handling**: Comprehensive logging and error reporting throughout

### Working with the Codebase

- The project uses a modular architecture with clear separation of concerns
- Each service (transcription, summarization, storage) can be extended independently
- The CLI provides a unified interface but individual components can be imported and used directly
- Test files are available but limited - consider adding more comprehensive tests
- The project is designed for cloud deployment but works locally for development