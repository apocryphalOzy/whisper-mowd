"""
OpenAI-based summarizer
Uses OpenAI API (ChatGPT) for transcript summarization
"""

import os
import logging
import openai
import math # Added for timestamp conversion
from .base_summarizer import BaseSummarizer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("openai-summarizer")

# Helper function for timestamp formatting
def format_timestamp(seconds):
    if seconds is None or not isinstance(seconds, (int, float)) or seconds < 0:
        return "[??:??:??]"
    h = math.floor(seconds / 3600)
    m = math.floor((seconds % 3600) / 60)
    s = math.floor(seconds % 60)
    return f"[{h:02d}:{m:02d}:{s:02d}]"

class OpenAISummarizer(BaseSummarizer):
    """
    Summarizer that uses OpenAI's API (ChatGPT) for generating summaries
    """
    
    def __init__(self, api_key=None, model="gpt-3.5-turbo"):
        """
        Initialize the OpenAI summarizer
        
        Args:
            api_key: OpenAI API key (if None, tries to get from environment)
            model: OpenAI model to use
        """
        self.model = model
        
        # Get API key from params or environment
        if api_key is None:
            api_key = os.getenv("OPENAI_API_KEY")
            
        if not api_key:
            logger.warning("No OpenAI API key provided. Summarization will fail.")
            self.client = None
        else:
            self.client = openai.OpenAI(api_key=api_key)
            logger.info(f"OpenAI summarizer initialized with model: {model}")
    
    def get_name(self):
        """
        Get the name of the summarizer
        """
        return f"OpenAI ({self.model})"
    
    def summarize(self, transcription_result, max_length=1000): # Increased default max_length for detailed summaries
        """
        Summarize a transcript using OpenAI API, including timestamps.
        
        Args:
            transcription_result: The full result dictionary from WhisperTranscriber
            max_length: Maximum length of output summary in tokens
            
        Returns:
            Summary text or None if summarization failed
        """
        if not self.client:
            logger.warning("OpenAI client not initialized. Cannot summarize.")
            return None
        
        logger.info("Generating summary using OpenAI API with timestamps")
        
        # Format transcript with timestamps
        transcript_with_timestamps = ""
        segments = transcription_result.get('segments', [])
        if not segments:
            logger.warning("No segments found in transcription result for summarization.")
            # Fallback to plain text if available
            plain_text = transcription_result.get('text', '')
            if not plain_text:
                 return "[Error: No transcript content available for summarization]"
            transcript_with_timestamps = plain_text # Use plain text if no segments
        else:
            for segment in segments:
                start_time = segment.get('start')
                text = segment.get('text', '').strip()
                if text: # Only include segments with text
                    timestamp_str = format_timestamp(start_time)
                    transcript_with_timestamps += f"{timestamp_str} {text}\n"
        
        if not transcript_with_timestamps.strip():
            logger.error("Formatted transcript with timestamps is empty.")
            return "[Error: Transcript content was empty after formatting]"

        # Preprocess the transcript to fit context window (optional, needs implementation)
        # transcript_for_api = self.preprocess_transcript(
        #     transcript_with_timestamps,
        #     max_context_length=16000
        # )
        transcript_for_api = transcript_with_timestamps # Use full for now

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": f"""
                    You are an expert educational assistant specializing in creating detailed, structured study notes from lecture transcripts. Your goal is to help students understand the material and easily review key sections.

                    Please summarize the following lecture transcript, which includes timestamps in [HH:MM:SS] format at the beginning of relevant segments:

                    1.  **Identify Key Topics:** Determine the main themes or learning objectives covered in the lecture.
                    2.  **Detailed Explanation:** For each key topic, provide a comprehensive explanation based on the transcript content. Go beyond a surface-level summary.
                    3.  **Timestamp References:** Crucially, whenever you discuss a specific point, concept, definition, or example, include the corresponding timestamp (e.g., `[HH:MM:SS]`) from the transcript where that information was presented. This allows students to quickly navigate back to the source.
                    4.  **Formatting:** Organize the summary clearly using headings for topics and bullet points for details and timestamped references.

                    Make the summary highly informative, accurate, and directly useful for studying and revision. Keep your response under {max_length} tokens.
                    """},
                    {"role": "user", "content": f"Here is the lecture transcript to summarize:\n\n{transcript_for_api}"} 
                ],
                max_tokens=max_length
            )
            
            summary = response.choices[0].message.content
            logger.info(f"Summary generated ({len(summary)} chars)")
            
            # Format the output for better readability (optional, needs implementation)
            # return self.format_output(summary)
            return summary
            
        except Exception as e:
            logger.error(f"Error generating summary with OpenAI: {e}")
            return None

    # Placeholder for preprocessing logic if needed later
    def preprocess_transcript(self, transcript, max_context_length):
        # TODO: Implement logic to truncate or chunk transcript if it exceeds max_context_length
        logger.debug(f"Preprocessing transcript (Current length: {len(transcript.split())} words approx.)")
        return transcript

    # Placeholder for output formatting logic if needed later
    def format_output(self, summary_text):
        # TODO: Implement any desired formatting (e.g., markdown enhancements)
        return summary_text