#!/usr/bin/env python
"""
Command-line interface for Whisper MOWD
Process audio files and generate transcripts and summaries
"""

import os
import sys
import signal
import argparse
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import components
from src.transcription.whisper_service import WhisperTranscriber
from src.transcription.file_converter import AudioFileConverter
from src.summarization.base_summarizer import NullSummarizer
from src.summarization.openai_summarizer import OpenAISummarizer
from src.summarization.custom_llm import CustomLLMSummarizer
from src.storage.local_storage import LocalStorage
from src.storage.secure_aws_storage import SecureAWSStorage as AWSStorage

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("cli")

# Load environment variables
load_dotenv()

transcriber = None  # Global variable to hold the transcriber instance

def handle_sigint(sig, frame):
    """Handle keyboard interrupt (Ctrl+C)"""
    global transcriber
    if transcriber:
        logger.info("Cancellation requested. Please wait...")
        transcriber.cancel_transcription()
    else:
        # Exit immediately if transcriber isn't initialized
        logger.info("Exiting...")
        sys.exit(1)

# Register the signal handler
signal.signal(signal.SIGINT, handle_sigint)

def get_storage(storage_mode=None):
    """
    Get the appropriate storage implementation
    
    Args:
        storage_mode: 'local' or 'aws' (if None, uses STORAGE_MODE from env)
        
    Returns:
        Storage instance
    """
    # Get storage mode from env if not specified
    if storage_mode is None:
        storage_mode = os.getenv("STORAGE_MODE", "local")
    
    # Create and return the appropriate storage implementation
    if storage_mode.lower() == "aws":
        return AWSStorage()
    else:
        return LocalStorage()

def get_summarizer(summarizer_type=None):
    """
    Get the appropriate summarizer implementation
    
    Args:
        summarizer_type: 'openai', 'custom_llm', or 'none'
        
    Returns:
        Summarizer instance
    """
    # Get summarizer type from env if not specified
    if summarizer_type is None:
        summarizer_type = os.getenv("SUMMARIZER_TYPE", "none")
    
    # Create and return the appropriate summarizer implementation
    if summarizer_type.lower() == "openai":
        return OpenAISummarizer()
    elif summarizer_type.lower() == "custom_llm":
        return CustomLLMSummarizer()
    else:
        return NullSummarizer()

def process_file(file_path, output_dir=None, model_size=None, summarizer_type=None, 
                storage_mode=None, lecture_id=None, convert_format="mp3"):
    """
    Process a single audio file
    
    Args:
        file_path: Path to the audio file
        output_dir: Directory for output files (if None, uses system default)
        model_size: Whisper model size (tiny, base, small, medium, large)
        summarizer_type: Type of summarizer to use
        storage_mode: Storage mode (local or aws)
        lecture_id: Custom lecture ID (generated if None)
        convert_format: Format for audio conversion (mp3 or wav)
        
    Returns:
        Dictionary with results
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Get model size from env if not specified
    if model_size is None:
        model_size = os.getenv("WHISPER_MODEL_SIZE", "base")
    
    # Create components
    global transcriber
    transcriber = WhisperTranscriber(model_size=model_size)
    converter = AudioFileConverter(default_output_format=convert_format)
    summarizer = get_summarizer(summarizer_type)
    storage = get_storage(storage_mode)
    
    # Generate lecture_id if not provided
    if lecture_id is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        lecture_id = f"{timestamp}_{file_path.stem}"
    
    # Track temporary files for cleanup
    temp_files = []
    
    try:
        logger.info(f"Processing file: {file_path} (ID: {lecture_id})")
        
        # Step 1: Convert audio if needed
        if converter.needs_conversion(file_path):
            logger.info(f"Converting {file_path.suffix} file to {convert_format}")
            converted_path = converter.convert_to_audio(file_path, convert_format)
            temp_files.append(converted_path)  # Track for cleanup
            audio_path = converted_path
        else:
            audio_path = str(file_path)
        
        # Step 2: Save original audio to storage
        storage.save_audio(audio_path, lecture_id)
        
        # Step 3: Transcribe audio
        logger.info(f"Transcribing audio using Whisper ({model_size})")
        transcription = transcriber.transcribe(audio_path)
        transcript_text = transcriber.get_text(transcription)
        
        # Step 4: Save transcript to storage
        storage.save_transcript(lecture_id, transcript_text)
        storage.save_transcript_with_timestamps(lecture_id, transcription)
        logger.info(f"Transcript length: {len(transcript_text)} characters")
        if len(transcript_text) == 0:
            logger.error("WARNING: Empty transcript generated")

        # When saving to file
        transcript_path = storage.save_transcript(lecture_id, transcript_text)
        logger.info(f"Saved transcript to {transcript_path}, verifying file...")

        # Verify the file was saved properly
        try:
            with open(transcript_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if len(content) == 0:
                    logger.error(f"Verification failed - file exists but is empty: {transcript_path}")
                else:
                    logger.info(f"Verification successful - file contains {len(content)} characters")
        except Exception as e:
            logger.error(f"Error verifying transcript file: {e}")
        
        # Step 5: Generate summary if summarizer is available
        summary_text = None
        if not isinstance(summarizer, NullSummarizer):
            logger.info(f"Generating summary using {summarizer.get_name()}")
            summary_text = summarizer.summarize(transcription)
            
            # Save summary to storage if generated
            if summary_text:
                storage.save_summary(lecture_id, summary_text)
        
        # Step 6: Save metadata
        metadata = {
            'lecture_id': lecture_id,
            'original_filename': file_path.name,
            'duration_seconds': transcription['segments'][-1]['end'] if transcription['segments'] else 0,
            'model_size': model_size,
            'language': transcriber.get_detected_language(transcription),
            'date_processed': datetime.now().isoformat(),
            'has_summary': summary_text is not None,
            'word_count': len(transcript_text.split()),
            'summarizer_type': summarizer.get_name()
        }
        storage.save_metadata(lecture_id, metadata)
        
        # Step 7: Create output copies if output_dir is specified
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Save transcript
            with open(output_dir / f"{lecture_id}_transcript.txt", 'w', encoding='utf-8') as f:
                f.write(transcript_text)
            
            # Save summary if available
            if summary_text:
                with open(output_dir / f"{lecture_id}_summary.txt", 'w', encoding='utf-8') as f:
                    f.write(summary_text)
            
            # Save metadata
            with open(output_dir / f"{lecture_id}_metadata.json", 'w', encoding='utf-8') as f:
                import json
                json.dump(metadata, f, indent=2)
        
        logger.info(f"Processing complete for lecture_id: {lecture_id}")
        
        return {
            'lecture_id': lecture_id,
            'transcript': transcript_text,
            'summary': summary_text,
            'metadata': metadata
        }
    finally:
        # Clean up any temporary files
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                    logger.debug(f"Removed temporary file: {temp_file}")
                except Exception as e:
                    logger.warning(f"Failed to remove temporary file {temp_file}: {e}")

def main():
    """Main function for CLI usage"""
    parser = argparse.ArgumentParser(description="Process lecture audio files with Whisper MOWD")
    parser.add_argument("--audio", required=True, help="Path to audio or video file")
    parser.add_argument("--output", default="output", help="Output directory")
    parser.add_argument("--model", default=None, choices=["tiny", "base", "small", "medium", "large"], 
                        help="Whisper model size (default: from env or 'base')")
    parser.add_argument("--summarizer", default=None, choices=["openai", "custom_llm", "none"],
                        help="Type of summarization to use (default: from env or 'none')")
    parser.add_argument("--storage", default=None, choices=["local", "aws"],
                        help="Storage mode (default: from env or 'local')")
    parser.add_argument("--format", default="mp3", choices=["mp3", "wav"], 
                        help="Format to convert files to before processing")
    parser.add_argument("--lecture-id", default=None, 
                        help="Custom lecture ID (default: generated from timestamp and filename)")
    parser.add_argument("--device", default="cpu", choices=["cpu", "cuda", "auto"],
                    help="Device to use for inference (default: cpu)")
    parser.add_argument("--compute-type", default="default", 
                    choices=["default", "int8", "int8_float16", "int16", "float16", "float32"],
                    help="Compute type for inference (default: default)")
    
    args = parser.parse_args()
    
    try:
        # Process the file
        result = process_file(
            file_path=args.audio,
            output_dir=args.output,
            model_size=args.model,
            summarizer_type=args.summarizer,
            storage_mode=args.storage,
            lecture_id=args.lecture_id,
            convert_format=args.format
        )
        
        # Print success message
        print(f"\nProcessing completed successfully!")
        print(f"Lecture ID: {result['lecture_id']}")
        print(f"Output directory: {os.path.abspath(args.output)}")
        
        # Print summary info if available
        if result['summary']:
            print(f"Transcript length: {len(result['transcript'])} characters")
            print(f"Summary length: {len(result['summary'])} characters")
        else:
            print(f"Transcript length: {len(result['transcript'])} characters")
            print("No summary generated")
        
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        print(f"Error: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())