"""
Tests for the storage module
Unit tests for local_storage.py and aws_storage.py
"""

import os
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile
import json

# Add the parent directory to the Python path
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import modules to test
from src.storage.local_storage import LocalStorage
from src.storage.secure_aws_storage import SecureAWSStorage as AWSStorage

class TestLocalStorage(unittest.TestCase):
    """Test cases for LocalStorage class"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create temporary directory for storage
        self.temp_dir = tempfile.mkdtemp()
        self.storage = LocalStorage(base_dir=self.temp_dir)
        
        # Create test data
        self.lecture_id = "test_lecture_123"
        self.transcript_text = "This is a test transcript."
        self.summary_text = "This is a test summary."
        self.metadata = {"title": "Test Lecture", "duration": 300}
    
    def tearDown(self):
        """Tear down test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_init_creates_directories(self):
        """Test that initialization creates required directories"""
        # Check that directories were created
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, "audio")))
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, "transcripts")))
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, "summaries")))
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, "metadata")))
    
    def test_save_audio(self):
        """Test save_audio method"""
        # Create a temporary audio file
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            temp_file.write(b"fake audio data")
            audio_path = temp_file.name
        
        try:
            # Save audio file
            lecture_id = self.storage.save_audio(audio_path, self.lecture_id)
            
            # Check that the file was copied
            self.assertEqual(lecture_id, self.lecture_id)
            saved_path = os.path.join(self.temp_dir, "audio", f"{self.lecture_id}.mp3")
            self.assertTrue(os.path.exists(saved_path))
            
            # Check that the get_audio_path method works
            self.assertEqual(self.storage.get_audio_path(self.lecture_id), saved_path)
        finally:
            # Clean up
            if os.path.exists(audio_path):
                os.unlink(audio_path)
    
    def test_save_transcript(self):
        """Test save_transcript method"""
        # Save transcript
        transcript_path = self.storage.save_transcript(self.lecture_id, self.transcript_text)
        
        # Check that the file was created
        self.assertTrue(os.path.exists(transcript_path))
        
        # Check that the content is correct
        with open(transcript_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertEqual(content, self.transcript_text)
        
        # Check that the get_transcript method works
        self.assertEqual(self.storage.get_transcript(self.lecture_id), self.transcript_text)
    
    def test_save_summary(self):
        """Test save_summary method"""
        # Save summary
        summary_path = self.storage.save_summary(self.lecture_id, self.summary_text)
        
        # Check that the file was created
        self.assertTrue(os.path.exists(summary_path))
        
        # Check that the content is correct
        with open(summary_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertEqual(content, self.summary_text)
        
        # Check that the get_summary method works
        self.assertEqual(self.storage.get_summary(self.lecture_id), self.summary_text)
        
        # Test with None summary
        self.assertIsNone(self.storage.save_summary("none_test", None))
    
    def test_save_metadata(self):
        """Test save_metadata method"""
        # Save metadata
        metadata_path = self.storage.save_metadata(self.lecture_id, self.metadata)
        
        # Check that the file was created
        self.assertTrue(os.path.exists(metadata_path))
        
        # Check that the content is correct
        with open(metadata_path, 'r', encoding='utf-8') as f:
            content = json.load(f)
            # Check original metadata fields
            self.assertEqual(content["title"], self.metadata["title"])
            self.assertEqual(content["duration"], self.metadata["duration"])
            # Check added fields
            self.assertEqual(content["lecture_id"], self.lecture_id)
            self.assertIn("created_at", content)
            self.assertIn("updated_at", content)
        
        # Check that the get_metadata method works
        saved_metadata = self.storage.get_metadata(self.lecture_id)
        self.assertEqual(saved_metadata["title"], self.metadata["title"])
    
    def test_list_lectures(self):
        """Test list_lectures method"""
        # Save some metadata
        self.storage.save_metadata("lecture1", {"title": "Lecture 1"})
        self.storage.save_metadata("lecture2", {"title": "Lecture 2"})
        self.storage.save_metadata("lecture3", {"title": "Lecture 3"})
        
        # List lectures
        lectures = self.storage.list_lectures()
        
        # Check that all lectures are returned
        self.assertEqual(len(lectures), 3)
        self.assertIn("lecture1", lectures)
        self.assertIn("lecture2", lectures)
        self.assertIn("lecture3", lectures)
        
        # Test pagination
        lectures = self.storage.list_lectures(limit=2)
        self.assertEqual(len(lectures), 2)

class TestAWSStorage(unittest.TestCase):
    """Test cases for AWSStorage class"""
    
    @patch('boto3.client')
    @patch('boto3.resource')
    def setUp(self, mock_resource, mock_client):
        """Set up test fixtures with mocked AWS services"""
        # Set up environment variables
        self.env_patcher = patch.dict('os.environ', {
            'S3_LECTURE_BUCKET': 'test-lecture-bucket',
            'S3_TRANSCRIPT_BUCKET': 'test-transcript-bucket',
            'DYNAMODB_TABLE': 'test-metadata-table',
            'AWS_REGION': 'us-east-1'
        })
        self.env_patcher.start()
        
        # Mock S3 client
        self.mock_s3 = MagicMock()
        mock_client.return_value = self.mock_s3
        
        # Mock DynamoDB resource and table
        self.mock_table = MagicMock()
        self.mock_dynamodb = MagicMock()
        self.mock_dynamodb.Table.return_value = self.mock_table
        mock_resource.return_value = self.mock_dynamodb
        
        # Initialize the storage
        self.storage = AWSStorage()
        
        # Create test data
        self.lecture_id = "test_lecture_123"
        self.transcript_text = "This is a test transcript."
        self.summary_text = "This is a test summary."
        self.metadata = {"title": "Test Lecture", "duration": 300}
    
    def tearDown(self):
        """Tear down test fixtures"""
        self.env_patcher.stop()
    
    def test_init(self):
        """Test initialization"""
        self.assertEqual(self.storage.audio_bucket, 'test-lecture-bucket')
        self.assertEqual(self.storage.transcript_bucket, 'test-transcript-bucket')
        self.assertEqual(self.storage.metadata_table_name, 'test-metadata-table')
        self.assertEqual(self.storage.region, 'us-east-1')
    
    def test_save_audio(self):
        """Test save_audio method"""
        # Create a temporary audio file
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            temp_file.write(b"fake audio data")
            audio_path = temp_file.name
        
        try:
            # Save audio file
            lecture_id = self.storage.save_audio(audio_path, self.lecture_id)
            
            # Check that S3 upload was called
            self.mock_s3.upload_file.assert_called_once()
            
            # Check arguments
            args, kwargs = self.mock_s3.upload_file.call_args
            self.assertEqual(args[0], audio_path)  # Source file
            self.assertEqual(args[1], 'test-lecture-bucket')  # Bucket name
            self.assertIn('lectures/test_lecture_123.mp3', args[2])  # S3 key
            
            # Check that ExtraArgs contains ContentType
            self.assertIn('ExtraArgs', kwargs)
            self.assertIn('ContentType', kwargs['ExtraArgs'])
            
            # Check lecture_id
            self.assertEqual(lecture_id, self.lecture_id)
        finally:
            # Clean up
            if os.path.exists(audio_path):
                os.unlink(audio_path)
    
    def test_save_transcript(self):
        """Test save_transcript method"""
        # Save transcript
        uri = self.storage.save_transcript(self.lecture_id, self.transcript_text)
        
        # Check that S3 put_object was called
        self.mock_s3.put_object.assert_called_once()
        
        # Check arguments
        kwargs = self.mock_s3.put_object.call_args[1]
        self.assertEqual(kwargs['Bucket'], 'test-transcript-bucket')
        self.assertEqual(kwargs['Key'], f'transcripts/{self.lecture_id}.txt')
        self.assertEqual(kwargs['Body'], self.transcript_text)
        self.assertEqual(kwargs['ContentType'], 'text/plain')
        
        # Check URI
        self.assertEqual(uri, f's3://test-transcript-bucket/transcripts/{self.lecture_id}.txt')
    
    def test_save_summary(self):
        """Test save_summary method"""
        # Save summary
        uri = self.storage.save_summary(self.lecture_id, self.summary_text)
        
        # Check that S3 put_object was called
        self.mock_s3.put_object.assert_called_once()
        
        # Check arguments
        kwargs = self.mock_s3.put_object.call_args[1]
        self.assertEqual(kwargs['Bucket'], 'test-transcript-bucket')
        self.assertEqual(kwargs['Key'], f'summaries/{self.lecture_id}.txt')
        self.assertEqual(kwargs['Body'], self.summary_text)
        self.assertEqual(kwargs['ContentType'], 'text/plain')
        
        # Check URI
        self.assertEqual(uri, f's3://test-transcript-bucket/summaries/{self.lecture_id}.txt')
        
        # Test with None summary
        self.mock_s3.reset_mock()
        self.assertIsNone(self.storage.save_summary("none_test", None))
        self.mock_s3.put_object.assert_not_called()
    
    def test_save_metadata(self):
        """Test save_metadata method"""
        # Save metadata
        self.storage.save_metadata(self.lecture_id, self.metadata.copy())
        
        # Check that DynamoDB put_item was called
        self.mock_table.put_item.assert_called_once()
        
        # Check arguments
        kwargs = self.mock_table.put_item.call_args[1]
        item = kwargs['Item']
        
        # Check original metadata fields
        self.assertEqual(item["title"], self.metadata["title"])
        self.assertEqual(item["duration"], self.metadata["duration"])
        
        # Check added fields
        self.assertEqual(item["lecture_id"], self.lecture_id)
        self.assertIn("created_at", item)
        self.assertIn("updated_at", item)
    
    @patch('boto3.client')
    def test_get_transcript(self, mock_client):
        """Test get_transcript method"""
        # Mock S3 response
        mock_s3 = MagicMock()
        mock_body = MagicMock()
        mock_body.read.return_value = self.transcript_text.encode('utf-8')
        mock_s3.get_object.return_value = {'Body': mock_body}
        mock_client.return_value = mock_s3
        
        # Update storage with new mock
        self.storage.s3_client = mock_s3
        
        # Get transcript
        transcript = self.storage.get_transcript(self.lecture_id)
        
        # Check that S3 get_object was called
        mock_s3.get_object.assert_called_once()
        
        # Check arguments
        kwargs = mock_s3.get_object.call_args[1]
        self.assertEqual(kwargs['Bucket'], 'test-transcript-bucket')
        self.assertEqual(kwargs['Key'], f'transcripts/{self.lecture_id}.txt')
        
        # Check result
        self.assertEqual(transcript, self.transcript_text)
    
    @patch('boto3.client')
    def test_get_summary(self, mock_client):
        """Test get_summary method"""
        # Mock S3 response
        mock_s3 = MagicMock()
        mock_body = MagicMock()
        mock_body.read.return_value = self.summary_text.encode('utf-8')
        mock_s3.get_object.return_value = {'Body': mock_body}
        mock_client.return_value = mock_s3
        
        # Update storage with new mock
        self.storage.s3_client = mock_s3
        
        # Get summary
        summary = self.storage.get_summary(self.lecture_id)
        
        # Check that S3 get_object was called
        mock_s3.get_object.assert_called_once()
        
        # Check arguments
        kwargs = mock_s3.get_object.call_args[1]
        self.assertEqual(kwargs['Bucket'], 'test-transcript-bucket')
        self.assertEqual(kwargs['Key'], f'summaries/{self.lecture_id}.txt')
        
        # Check result
        self.assertEqual(summary, self.summary_text)
    
    def test_get_metadata(self):
        """Test get_metadata method"""
        # Mock DynamoDB response
        self.mock_table.get_item.return_value = {'Item': self.metadata}
        
        # Get metadata
        metadata = self.storage.get_metadata(self.lecture_id)
        
        # Check that DynamoDB get_item was called
        self.mock_table.get_item.assert_called_once()
        
        # Check arguments
        kwargs = self.mock_table.get_item.call_args[1]
        self.assertEqual(kwargs['Key'], {'lecture_id': self.lecture_id})
        
        # Check result
        self.assertEqual(metadata, self.metadata)
    
    def test_list_lectures(self):
        """Test list_lectures method"""
        # Mock DynamoDB response
        self.mock_table.scan.return_value = {
            'Items': [
                {'lecture_id': 'lecture1', 'title': 'Lecture 1'},
                {'lecture_id': 'lecture2', 'title': 'Lecture 2'},
                {'lecture_id': 'lecture3', 'title': 'Lecture 3'}
            ]
        }
        
        # List lectures
        lectures = self.storage.list_lectures()
        
        # Check that DynamoDB scan was called
        self.mock_table.scan.assert_called_once()
        
        # Check arguments
        kwargs = self.mock_table.scan.call_args[1]
        self.assertEqual(kwargs['Limit'], 100)
        
        # Check result
        self.assertEqual(len(lectures), 3)
        self.assertEqual(lectures[0]['lecture_id'], 'lecture1')

if __name__ == '__main__':
    unittest.main()