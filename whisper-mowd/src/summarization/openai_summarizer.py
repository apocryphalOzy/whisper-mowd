"""
OpenAI-based summarizer
Uses OpenAI API (ChatGPT) for transcript summarization
"""

import os
import logging
import openai
from .base_summarizer import BaseSummarizer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("openai-summarizer")

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
    
    def summarize(self, transcript_text, max_length=600):
        """
        Summarize a transcript using OpenAI API
        
        Args:
            transcript_text: The transcript text to summarize
            max_length: Maximum length of output summary in tokens
            
        Returns:
            Summary text or None if summarization failed
        """
        if not self.client:
            logger.warning("OpenAI client not initialized. Cannot summarize.")
            return None
        
        logger.info("Generating summary using OpenAI API")
        
        # Preprocess the transcript to fit context window
        transcript = self.preprocess_transcript(
            transcript_text, 
            max_context_length=16000  # Conservative estimate for gpt-3.5-turbo
        )
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": f"""
                    You are an educational assistant that creates concise, helpful summaries of lecture transcripts.
                    Format your summary with:
                    1. Main topics/concepts (bullet points)
                    2. Key points for each topic (sub-bullets)
                    3. Important definitions or formulas
                    
                    Make your summary clear, educational, and easy to study from.
                    Keep your response under {max_length} tokens.
                    """},
                    {"role": "user", "content": f"Here is the lecture transcript to summarize:\n\n{transcript}"}
                ],
                max_tokens=max_length
            )
            
            summary = response.choices[0].message.content
            logger.info(f"Summary generated ({len(summary)} chars)")
            
            # Format the output for better readability
            return self.format_output(summary)
            
        except Exception as e:
            logger.error(f"Error generating summary with OpenAI: {e}")
            return None