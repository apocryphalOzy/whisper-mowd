#!/usr/bin/env python
"""
Batch processing script for Whisper MOWD
Process multiple audio files in a directory
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import CLI module
from src.cli import process_file

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("batch-processor")

def find_audio_files(directory, recursive=False):
    """
    Find audio files in a directory
    
    Args:
        directory: Directory to search
        recursive: Whether to search recursively
        
    Returns:
        List of file paths
    """
    directory = Path(directory)
    
    # Define supported extensions
    AUDIO_EXTENSIONS = ['.mp3', '.wav', '.m4a', '.ogg', '.flac']
    VIDEO_EXTENSIONS = ['.mp4', '.mkv', '.avi', '.mov', '.flv', '.webm']
    SUPPORTED_EXTENSIONS = AUDIO_EXTENSIONS + VIDEO_EXTENSIONS
    
    # Find files
    if recursive:
        all_files = list(directory.glob('**/*.*'))
    else:
        all_files = list(directory.glob('*.*'))
    
    # Filter by extension
    audio_files = [f for f in all_files if f.suffix.lower() in SUPPORTED_EXTENSIONS]
    
    return audio_files

def process_single_file(file_path, args):
    """
    Process a single file with error handling
    
    Args:
        file_path: Path to the file
        args: Command-line arguments
        
    Returns:
        Dictionary with result information
    """
    try:
        # Generate lecture_id based on parent folder and filename
        if args.use_folder_name:
            folder_name = file_path.parent.name
            lecture_id = f"{folder_name}_{file_path.stem}"
        else:
            lecture_id = None
            
        # Process the file
        result = process_file(
            file_path=file_path,
            output_dir=args.output,
            model_size=args.model,
            summarizer_type=args.summarizer,
            storage_mode=args.storage,
            lecture_id=lecture_id,
            convert_format=args.format
        )
        
        return {'status': 'success', 'file': file_path, 'lecture_id': result['lecture_id']}
        
    except Exception as e:
        logger.error(f"Error processing {file_path}: {e}")
        return {'status': 'error', 'file': file_path, 'error': str(e)}

def main():
    """Main function for batch processing"""
    parser = argparse.ArgumentParser(description="Batch process lecture audio files with Whisper MOWD")
    parser.add_argument("--directory", required=True, help="Directory containing audio files")
    parser.add_argument("--output", default="output", help="Output directory")
    parser.add_argument("--recursive", action="store_true", help="Search for files recursively")
    parser.add_argument("--model", default=None, choices=["tiny", "base", "small", "medium", "large"], 
                        help="Whisper model size (default: from env or 'base')")
    parser.add_argument("--summarizer", default=None, choices=["openai", "custom_llm", "none"],
                        help="Type of summarization to use (default: from env or 'none')")
    parser.add_argument("--storage", default=None, choices=["local", "aws"],
                        help="Storage mode (default: from env or 'local')")
    parser.add_argument("--format", default="mp3", choices=["mp3", "wav"], 
                        help="Format to convert files to before processing")
    parser.add_argument("--use-folder-name", action="store_true",
                        help="Use parent folder name in lecture ID")
    parser.add_argument("--workers", type=int, default=1,
                        help="Number of worker threads (default: 1)")
    
    args = parser.parse_args()
    
    try:
        # Find audio files
        audio_files = find_audio_files(args.directory, args.recursive)
        
        if not audio_files:
            print(f"No audio files found in {args.directory}")
            return 1
        
        print(f"Found {len(audio_files)} audio files to process")
        
        # Create output directory
        os.makedirs(args.output, exist_ok=True)
        
        # Process files in parallel if requested
        results = []
        if args.workers > 1:
            print(f"Processing files with {args.workers} worker threads")
            with ThreadPoolExecutor(max_workers=args.workers) as executor:
                futures = [executor.submit(process_single_file, file, args) for file in audio_files]
                for future in futures:
                    results.append(future.result())
        else:
            print("Processing files sequentially")
            for file in audio_files:
                results.append(process_single_file(file, args))
        
        # Count successes and failures
        successes = [r for r in results if r['status'] == 'success']
        failures = [r for r in results if r['status'] == 'error']
        
        # Print summary
        print("\nBatch processing completed!")
        print(f"Total files: {len(audio_files)}")
        print(f"Successful: {len(successes)}")
        print(f"Failed: {len(failures)}")
        
        # Write report
        report_path = Path(args.output) / f"batch_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(f"Batch Processing Report\n")
            f.write(f"======================\n\n")
            f.write(f"Date: {datetime.now().isoformat()}\n")
            f.write(f"Directory: {args.directory}\n")
            f.write(f"Model: {args.model}\n")
            f.write(f"Summarizer: {args.summarizer}\n\n")
            
            f.write(f"Successful ({len(successes)}):\n")
            for result in successes:
                f.write(f"  - {result['file'].name} -> {result['lecture_id']}\n")
            
            if failures:
                f.write(f"\nFailed ({len(failures)}):\n")
                for result in failures:
                    f.write(f"  - {result['file'].name}: {result['error']}\n")
        
        print(f"Report saved to: {report_path}")
        
        # Return error code if any failures
        return 1 if failures else 0
        
    except Exception as e:
        logger.error(f"Error during batch processing: {e}")
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())