"""
Whisper transcription service
Handles loading and using the Whisper model for speech-to-text
"""

import time
import logging
from pathlib import Path
import threading

# Import faster-whisper at the top
try:
    from faster_whisper import WhisperModel
    FASTER_WHISPER_AVAILABLE = True
except ImportError:
    FASTER_WHISPER_AVAILABLE = False
    
# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("whisper-service")

class WhisperTranscriber:
    """
    Handles transcription of audio files using Faster-Whisper (CTranslate2)
    """
    
    def __init__(self, model_size="base", device="auto", compute_type="auto"):
        """
        Initialize the transcriber with the specified Whisper model
        
        Args:
            model_size: Size of Whisper model to use (tiny, base, small, medium, large)
            device: Device to use for inference ("cpu", "cuda", or "auto")
            compute_type: Compute type to use ("float32", "float16", "int8", or "auto")
        """
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.model = None  # Lazy-load the model when needed
        self._transcription_complete = False
        self.cancel_requested = False
        
    def _load_model(self):
        """Lazy-load the Whisper model when needed"""
        if self.model is None:
            if not FASTER_WHISPER_AVAILABLE:
                logger.warning("faster-whisper not available, falling back to original whisper")
                import whisper
                self.model = whisper.load_model(self.model_size)
                return self.model
                
            logger.info(f"Loading Faster-Whisper {self.model_size} model...")
            logger.info(f"Device: {self.device}, Compute type: {self.compute_type}")
            
            start_time = time.time()
            self.model = WhisperModel(
                self.model_size, 
                device=self.device, 
                compute_type=self.compute_type
            )
            load_time = time.time() - start_time
            
            logger.info(f"Model loaded in {load_time:.2f} seconds")
        
        return self.model
    
    def transcribe(self, audio_path):
        """
        Transcribe an audio file using Whisper
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            Dict containing the transcription result
        """
        self.cancel_requested = False
        
        audio_path = Path(audio_path)
        
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        logger.info(f"Transcribing {audio_path}")
        
        # First, try to get audio duration for time estimate
        try:
            from src.transcription.utils import get_audio_duration
            duration = get_audio_duration(audio_path)
            if duration:
                # Rough estimates based on model size and hardware
                speed_factors = {
                    "tiny": 0.1, "base": 0.2, "small": 0.5, 
                    "medium": 1.0, "large": 2.0
                }
                estimated_time = duration * speed_factors.get(self.model_size, 0.5)
                
                # GPU is typically 5-10x faster than CPU
                if self.device == "cuda":
                    estimated_time /= 8

                if duration and estimated_time > 10:  # Only use timer for longer transcriptions
                    self._transcription_complete = False
                    
                    # Create a countdown timer function
                    def countdown_timer(total_seconds):
                        start_time = time.time()
                        while time.time() - start_time < total_seconds:
                            elapsed = time.time() - start_time
                            remaining = total_seconds - elapsed
                            percent_done = (elapsed / total_seconds) * 100
                            logger.info(f"Progress: {percent_done:.1f}% - Estimated time remaining: {remaining:.1f}s")
                            time.sleep(5)  # Update every 5 seconds
                            
                            # Check if transcription is complete
                            if self._transcription_complete:
                                break
                    
                    # Start timer in a separate thread
                    timer_thread = threading.Thread(target=countdown_timer, args=(estimated_time,))
                    timer_thread.daemon = True  # Ensures the thread won't block program exit
                    timer_thread.start()
                
                logger.info(f"Audio duration: {duration:.1f}s, estimated processing time: {estimated_time:.1f}s")
        except Exception as e:
            logger.debug(f"Could not estimate processing time: {e}")
            
        
        # Load model if not already loaded
        model = self._load_model()
        
        try:
            # Perform transcription
            start_time = time.time()
            
            # Define progress callback
            def progress_callback(progress):
                logger.info(f"Transcription progress: {progress*100:.1f}%")
            
            if FASTER_WHISPER_AVAILABLE:
                # Using faster-whisper without progress callback
                segments, info = model.transcribe(
                    str(audio_path),
                    beam_size=5,
                    vad_filter=True,
                    vad_parameters=dict(min_silence_duration_ms=500)
                )
                                
                # Create segments list with cancellation check
                segments_list = []
                for segment in segments:
                    if self.cancel_requested:
                        logger.info("Transcription cancelled by user")
                        raise InterruptedError("Transcription cancelled by user")
                    segments_list.append(segment)
                
                # Reformat to match original whisper format
                result = {
                    "text": " ".join([segment.text for segment in segments_list]),
                    "segments": [
                        {
                            "id": i,
                            "start": segment.start,
                            "end": segment.end,
                            "text": segment.text,
                            "words": getattr(segment, "words", [])
                        } for i, segment in enumerate(segments_list)
                    ],
                    "language": info.language
                }
            else:
                # Using original whisper
                result = model.transcribe(str(audio_path))
            
            transcribe_time = time.time() - start_time
            
            logger.info(f"Transcription completed in {transcribe_time:.2f} seconds")
            if FASTER_WHISPER_AVAILABLE:
                logger.info(f"Detected language: {result['language']}")
                            
            if not result.get("text"):
                logger.warning("Transcription completed but produced empty text output")
                if segments_list:
                    # Try to recreate text from segments if available
                    reconstructed_text = " ".join([s.get("text", "") for s in segments_list if s.get("text")])
                    if reconstructed_text:
                        logger.info(f"Reconstructed {len(reconstructed_text)} characters from segments")
                        result["text"] = reconstructed_text
            self._transcription_complete = True

            # Log the size of the result
            text_length = len(result.get("text", ""))
            segments_count = len(result.get("segments", []))
            logger.info(f"Transcription result: {text_length} characters in {segments_count} segments")
            
            return result
            
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            raise
    def get_segments(self, transcription_result):
        """
        Extract segments with timestamps from transcription result
        
        Args:
            transcription_result: Result dict from transcribe()
            
        Returns:
            List of segments with text and timestamps
        """
        return transcription_result.get("segments", [])

    def get_detected_language(self, transcription_result):
        """
        Get the detected language from transcription result
        
        Args:
            transcription_result: Result dict from transcribe()
            
        Returns:
            Detected language code (e.g., 'en', 'fr')
        """
        return transcription_result.get("language", "en")

    def get_text(self, transcription_result):
        """
        Get the full transcript text from transcription result
        
        Args:
            transcription_result: Result dict from transcribe()
            
        Returns:
            Full transcript text
        """
        return transcription_result.get("text", "")

    def get_word_timestamps(self, transcription_result):
        """
        Get word-level timestamps if available
        
        Args:
            transcription_result: Result dict from transcribe()
            
        Returns:
            List of words with timestamps, or empty list if not available
        """
        words = []
        for segment in transcription_result.get("segments", []):
            if "words" in segment:
                words.extend(segment["words"])
        return words
    
    def cancel_transcription(self):
        """Request cancellation of the current transcription"""
        self.cancel_requested = True
        logger.info("Transcription cancellation requested")