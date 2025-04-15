"""
Tests for the transcription module
Unit tests for whisper_service.py and file_converter.py
"""

import os
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile

# Add the parent directory to the Python path
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import modules to test
from src.transcription.whisper_service import WhisperTranscriber
from src.transcription.file_converter import AudioFileConverter
from src.transcription.utils import format_timestamp, format_segments_as_srt

class TestWhisperTranscriber(unittest.TestCase):
    """Test cases for WhisperTranscriber class"""
    
    @patch('whisper.load_model')
    def test_init(self, mock_load_model):
        """Test initialization"""
        transcriber = WhisperTranscriber(model_size="tiny")
        self.assertEqual(transcriber.model_size, "tiny")
        # Model should not be loaded yet (lazy loading)
        mock_load_model.assert_not_called()
    
    @patch('whisper.load_model')
    def test_lazy_loading(self, mock_load_model):
        """Test lazy loading of model"""
        mock_model = MagicMock()
        mock_load_model.return_value = mock_model
        
        transcriber = WhisperTranscriber(model_size="tiny")
        # Access the model to trigger loading
        model = transcriber._load_model()
        
        mock_load_model.assert_called_once_with("tiny")
        self.assertEqual(model, mock_model)
    
    @patch('whisper.load_model')
    def test_get_text(self, mock_load_model):
        """Test get_text method"""
        transcriber = WhisperTranscriber()
        result = {"text": "Hello world"}
        
        self.assertEqual(transcriber.get_text(result), "Hello world")
    
    @patch('whisper.load_model')
    def test_get_segments(self, mock_load_model):
        """Test get_segments method"""
        transcriber = WhisperTranscriber()
        segments = [{"start": 0, "end": 1, "text": "Hello"}, 
                   {"start": 1, "end": 2, "text": "world"}]
        result = {"segments": segments}
        
        self.assertEqual(transcriber.get_segments(result), segments)

class TestAudioFileConverter(unittest.TestCase):
    """Test cases for AudioFileConverter class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.converter = AudioFileConverter(default_output_format="mp3")
        
        # Create sample files
        self.temp_dir = tempfile.mkdtemp()
        self.mp3_path = os.path.join(self.temp_dir, "test.mp3")
        self.mp4_path = os.path.join(self.temp_dir, "test.mp4")
        self.txt_path = os.path.join(self.temp_dir, "test.txt")
        
        # Create empty files
        Path(self.mp3_path).touch()
        Path(self.mp4_path).touch()
        Path(self.txt_path).touch()
    
    def tearDown(self):
        """Tear down test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_needs_conversion(self):
        """Test needs_conversion method"""
        # MP3 should not need conversion
        self.assertFalse(self.converter.needs_conversion(self.mp3_path))
        
        # MP4 should need conversion
        self.assertTrue(self.converter.needs_conversion(self.mp4_path))
        
        # TXT should not be recognized as audio/video
        self.assertFalse(self.converter.needs_conversion(self.txt_path))
    
    @patch('subprocess.run')
    def test_convert_to_audio(self, mock_run):
        """Test convert_to_audio method with mocked subprocess"""
        # Mock successful conversion
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_run.return_value = mock_process
        
        # No conversion needed for MP3
        result = self.converter.convert_to_audio(self.mp3_path)
        self.assertEqual(result, self.mp3_path)
        mock_run.assert_not_called()
        
        # Reset mock
        mock_run.reset_mock()
        
        # Test MP4 conversion (mocked)
        with patch('tempfile.NamedTemporaryFile') as mock_temp:
            mock_temp_file = MagicMock()
            mock_temp_file.name = "/tmp/test_output.mp3"
            mock_temp.return_value = mock_temp_file
            
            result = self.converter.convert_to_audio(self.mp4_path)
            
            # Check that ffmpeg was called
            mock_run.assert_called_once()
            # Check that the command includes ffmpeg
            self.assertEqual(mock_run.call_args[0][0][0], "ffmpeg")
            # Check that the output format is correct
            self.assertEqual(result, "/tmp/test_output.mp3")

class TestUtils(unittest.TestCase):
    """Test cases for utility functions"""
    
    def test_format_timestamp(self):
        """Test format_timestamp function"""
        self.assertEqual(format_timestamp(0), "00:00:00")
        self.assertEqual(format_timestamp(61), "00:01:01")
        self.assertEqual(format_timestamp(3661), "01:01:01")
    
    def test_format_segments_as_srt(self):
        """Test format_segments_as_srt function"""
        segments = [
            {"start": 0, "end": 2, "text": "Hello"},
            {"start": 2, "end": 4, "text": "world"}
        ]
        
        srt = format_segments_as_srt(segments)
        
        # Check that the SRT contains segment numbers
        self.assertIn("1", srt)
        self.assertIn("2", srt)
        
        # Check that it contains timestamps
        self.assertIn("00:00:00,000 --> 00:00:02,000", srt)
        
        # Check that it contains the text
        self.assertIn("Hello", srt)
        self.assertIn("world", srt)

if __name__ == '__main__':
    unittest.main()