"""
Storage module for Whisper MOWD
Handles file and metadata storage with local and cloud backends
"""

from .local_storage import LocalStorage
from .secure_aws_storage import SecureAWSStorage as AWSStorage

__all__ = ['LocalStorage', 'AWSStorage']