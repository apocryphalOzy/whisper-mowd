"""
Storage module for Whisper MOWD
Handles file and metadata storage with local and cloud backends
"""

from .local_storage import LocalStorage
from .aws_storage import AWSStorage

__all__ = ['LocalStorage', 'AWSStorage']