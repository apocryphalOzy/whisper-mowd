"""
Tests for the summarization module
Unit tests for summarizers
"""

import os
import unittest
from unittest.mock import patch, MagicMock
import tempfile

# Add the parent directory to the Python path
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import modules to test
from src.summarization.base_summarizer import BaseSummarizer, NullSummarizer
from src.summarization.openai_summarizer import OpenAISummarizer
from src.summarization.custom_llm import CustomLLMSummarizer

class TestBaseSummarizer(unittest.TestCase):
    """Test cases for BaseSummarizer abstract class"""
    
    def test_cannot_instantiate_abstract_class(self):
        """Test that BaseSummarizer cannot be instantiated directly"""
        with self.assertRaises(TypeError):
            BaseSummarizer()
    
    def test_preprocess_transcript(self):
        """Test transcript preprocessing method"""
        # Create a concrete subclass for testing
        class ConcreteSummarizer(BaseSummarizer):
            def summarize(self, transcript_text, max_length=600):
                return "Summary"
            
            def get_name(self):
                return "Concrete"
        
        summarizer = ConcreteSummarizer()
        
        # Test whitespace normalization
        text = "This  is  a  test\nwith    multiple\n\nspaces."
        processed = summarizer.preprocess_transcript(text)
        self.assertEqual(processed, "This is a test with multiple spaces.")
        
        # Test truncation
        long_text = "a" * 1000
        processed = summarizer.preprocess_transcript(long_text, max_context_length=500)
        self.assertEqual(len(processed), 500)
    
    def test_format_output(self):
        """Test summary output formatting"""
        class ConcreteSummarizer(BaseSummarizer):
            def summarize(self, transcript_text, max_length=600):
                return "Summary"
            
            def get_name(self):
                return "Concrete"
        
        summarizer = ConcreteSummarizer()
        
        # Test adding title to summary
        text = "This is a summary without a title"
        formatted = summarizer.format_output(text)
        self.assertTrue(formatted.startswith("# Lecture Summary"))
        
        # Test preserving existing title
        text = "# Custom Title\nThis is a summary with a title"
        formatted = summarizer.format_output(text)
        self.assertEqual(formatted, text)  # Should not modify

class TestNullSummarizer(unittest.TestCase):
    """Test cases for NullSummarizer class"""
    
    def test_null_summarizer(self):
        """Test NullSummarizer (disabled summarization)"""
        summarizer = NullSummarizer()
        
        # Should always return None
        self.assertIsNone(summarizer.summarize("Any text"))
        
        # Should have the correct name
        self.assertEqual(summarizer.get_name(), "Disabled")

class TestOpenAISummarizer(unittest.TestCase):
    """Test cases for OpenAISummarizer class"""
    
    @patch('openai.OpenAI')
    def test_init_with_api_key(self, mock_openai):
        """Test initialization with API key"""
        # Test with API key
        summarizer = OpenAISummarizer(api_key="test_key")
        self.assertIsNotNone(summarizer.client)
        mock_openai.assert_called_once_with(api_key="test_key")
    
    @patch('openai.OpenAI')
    @patch.dict('os.environ', {}, clear=True)  # Empty environment
    def test_init_without_api_key(self, mock_openai):
        """Test initialization without API key"""
        # Test without API key
        summarizer = OpenAISummarizer()
        self.assertIsNone(summarizer.client)
        mock_openai.assert_not_called()
    
    @patch('openai.OpenAI')
    def test_get_name(self, mock_openai):
        """Test get_name method"""
        summarizer = OpenAISummarizer(api_key="test_key", model="test-model")
        self.assertEqual(summarizer.get_name(), "OpenAI (test-model)")
    
    @patch('openai.OpenAI')
    def test_summarize_without_client(self, mock_openai):
        """Test summarize method without client"""
        summarizer = OpenAISummarizer()
        summarizer.client = None
        
        # Should return None if client is not initialized
        self.assertIsNone(summarizer.summarize("Test text"))
    
    @patch('openai.OpenAI')
    def test_summarize_with_client(self, mock_openai):
        """Test summarize method with mocked client"""
        # Create mock client and response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        
        mock_message.content = "Test summary"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response
        
        # Setup summarizer with mock client
        summarizer = OpenAISummarizer(api_key="test_key")
        summarizer.client = mock_client
        
        # Test summarize method
        summary = summarizer.summarize("Test text")
        
        # Check that the client was called correctly
        mock_client.chat.completions.create.assert_called_once()
        
        # Check that it returns the expected summary
        self.assertTrue(summary.startswith("# Lecture Summary"))
        self.assertIn("Test summary", summary)

class TestCustomLLMSummarizer(unittest.TestCase):
    """Test cases for CustomLLMSummarizer class"""
    
    def test_init_defaults(self):
        """Test initialization with defaults"""
        summarizer = CustomLLMSummarizer()
        self.assertEqual(summarizer.implementation, "placeholder")
    
    @patch.dict('os.environ', {'CUSTOM_LLM_MODEL_PATH': '/path/to/model'})
    @patch('src.summarization.custom_llm.logger')
    def test_init_with_model_path(self, mock_logger):
        """Test initialization with model path from environment"""
        summarizer = CustomLLMSummarizer()
        self.assertEqual(summarizer.implementation, "local_model")
        mock_logger.info.assert_called_with("Local model integration has been selected but needs implementation")
    
    @patch.dict('os.environ', {'CUSTOM_LLM_API_URL': 'http://localhost:8000'})
    def test_init_with_api_url(self, ):
        """Test initialization with API URL from environment"""
        summarizer = CustomLLMSummarizer()
        self.assertEqual(summarizer.implementation, "api")
    
    def test_get_name(self):
        """Test get_name method"""
        # Test placeholder implementation
        summarizer = CustomLLMSummarizer()
        self.assertEqual(summarizer.get_name(), "Custom LLM (Placeholder)")
        
        # Test local model implementation
        summarizer = CustomLLMSummarizer()
        summarizer.implementation = "local_model"
        summarizer.model_path = "/path/to/model.bin"
        self.assertEqual(summarizer.get_name(), "Custom LLM (Local: model.bin)")
        
        # Test API implementation
        summarizer = CustomLLMSummarizer()
        summarizer.implementation = "api"
        summarizer.api_url = "http://localhost:8000"
        self.assertEqual(summarizer.get_name(), "Custom LLM (API: http://localhost:8000)")
    
    def test_placeholder_summarize(self):
        """Test placeholder summarization implementation"""
        summarizer = CustomLLMSummarizer()
        
        # Create test transcript with paragraphs
        transcript = "This is the first paragraph.\n\nThis is the second paragraph.\n\nThis is the third paragraph."
        
        summary = summarizer._placeholder_summarize(transcript)
        
        # Check that it extracts first sentences
        self.assertIn("* This is the first paragraph", summary)
        self.assertIn("* This is the second paragraph", summary)
        self.assertIn("* This is the third paragraph", summary)

if __name__ == '__main__':
    unittest.main()