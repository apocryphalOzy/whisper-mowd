"""
Base summarizer abstract class
Defines the interface for all summarizers
"""

import logging
from abc import ABC, abstractmethod

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("base-summarizer")

class BaseSummarizer(ABC):
    """
    Abstract base class for all summarizers
    Defines the common interface
    """
    
    @abstractmethod
    def summarize(self, transcript_text, max_length=600):
        """
        Summarize a transcript
        
        Args:
            transcript_text: The transcript text to summarize
            max_length: Maximum length of output summary in tokens
            
        Returns:
            Summary text or None if summarization failed
        """
        pass
    
    @abstractmethod
    def get_name(self):
        """
        Get the name of the summarizer for display purposes
        
        Returns:
            String name of the summarizer
        """
        pass
    
    def preprocess_transcript(self, transcript_text, max_context_length=None):
        """
        Preprocess transcript text before summarization
        
        Args:
            transcript_text: The transcript to preprocess
            max_context_length: Maximum context length to use (for LLMs with context limits)
            
        Returns:
            Preprocessed transcript text
        """
        # Basic preprocessing logic
        # 1. Remove excessive whitespace
        text = ' '.join(transcript_text.split())
        
        # 2. Truncate if needed to fit context window
        if max_context_length and len(text) > max_context_length:
            logger.warning(f"Transcript length ({len(text)}) exceeds max context length ({max_context_length})")
            logger.warning("Truncating transcript to fit context window")
            text = text[:max_context_length]
            
            # Try to truncate at a sentence boundary
            last_period = text.rfind('.')
            if last_period > 0.8 * max_context_length:  # Only if period is reasonably close to the end
                text = text[:last_period + 1]
        
        return text

    def format_output(self, summary_text):
        """
        Format the summary output for better readability
        
        Args:
            summary_text: Raw summary text
            
        Returns:
            Formatted summary text
        """
        # Add a title
        if not summary_text.startswith('#'):
            summary_text = "# Lecture Summary\n\n" + summary_text
            
        return summary_text


class NullSummarizer(BaseSummarizer):
    """
    Null summarizer that returns None
    Used when summarization is disabled
    """
    
    def summarize(self, transcript_text, max_length=600):
        """
        Returns None for all inputs
        """
        logger.info("Summarization is disabled")
        return None
    
    def get_name(self):
        """
        Get the name of the summarizer
        """
        return "Disabled"