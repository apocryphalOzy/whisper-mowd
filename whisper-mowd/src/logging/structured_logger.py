"""
Structured JSON Logger for CloudWatch
Provides consistent logging format for security and compliance
"""

import json
import logging
import traceback
from datetime import datetime
from typing import Any, Dict, Optional
import os
import sys

class StructuredLogger:
    """
    Creates structured JSON logs for CloudWatch with security context
    """
    
    def __init__(self, service_name: str, log_level: str = "INFO"):
        """
        Initialize structured logger
        
        Args:
            service_name: Name of the service/Lambda function
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        self.service_name = service_name
        self.environment = os.environ.get('ENVIRONMENT', 'dev')
        self.region = os.environ.get('AWS_REGION', 'us-east-1')
        
        # Configure root logger
        self.logger = logging.getLogger()
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # Remove default handlers
        for handler in self.logger.handlers:
            self.logger.removeHandler(handler)
        
        # Add structured JSON handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(self.StructuredFormatter(
            service_name=self.service_name,
            environment=self.environment,
            region=self.region
        ))
        self.logger.addHandler(handler)
    
    class StructuredFormatter(logging.Formatter):
        """Custom formatter for structured JSON output"""
        
        def __init__(self, service_name: str, environment: str, region: str):
            super().__init__()
            self.service_name = service_name
            self.environment = environment
            self.region = region
        
        def format(self, record: logging.LogRecord) -> str:
            """
            Format log record as JSON
            
            Args:
                record: Log record to format
                
            Returns:
                JSON formatted log string
            """
            # Base log structure
            log_data = {
                '@timestamp': datetime.utcnow().isoformat() + 'Z',
                'level': record.levelname,
                'service': self.service_name,
                'environment': self.environment,
                'region': self.region,
                'message': record.getMessage(),
                'logger': record.name,
                'thread': record.thread,
                'thread_name': record.threadName
            }
            
            # Add exception info if present
            if record.exc_info:
                log_data['exception'] = {
                    'type': record.exc_info[0].__name__,
                    'message': str(record.exc_info[1]),
                    'stacktrace': traceback.format_exception(*record.exc_info)
                }
            
            # Add custom attributes
            if hasattr(record, 'custom_attrs'):
                log_data.update(record.custom_attrs)
            
            # Add security context if present
            if hasattr(record, 'security_context'):
                log_data['security'] = record.security_context
            
            # Add request context if present
            if hasattr(record, 'request_context'):
                log_data['request'] = record.request_context
            
            return json.dumps(log_data)
    
    def log(self, level: str, message: str, **kwargs):
        """
        Log a message with structured data
        
        Args:
            level: Log level
            message: Log message
            **kwargs: Additional structured data
        """
        extra = {
            'custom_attrs': kwargs
        }
        
        # Extract special contexts
        if 'security_context' in kwargs:
            extra['security_context'] = kwargs.pop('security_context')
        
        if 'request_context' in kwargs:
            extra['request_context'] = kwargs.pop('request_context')
        
        getattr(self.logger, level.lower())(message, extra=extra)
    
    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self.log('debug', message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message"""
        self.log('info', message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self.log('warning', message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message"""
        self.log('error', message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message"""
        self.log('critical', message, **kwargs)
    
    def security_event(self, event_type: str, details: Dict[str, Any], 
                      severity: str = "INFO", user_id: Optional[str] = None):
        """
        Log a security event
        
        Args:
            event_type: Type of security event
            details: Event details
            severity: Event severity
            user_id: User associated with event
        """
        security_context = {
            'event_type': event_type,
            'user_id': user_id,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'details': details
        }
        
        self.log(severity.lower(), f"Security Event: {event_type}", 
                security_context=security_context)
    
    def audit_trail(self, action: str, resource: str, user_id: str, 
                   result: str, details: Optional[Dict[str, Any]] = None):
        """
        Create audit trail entry
        
        Args:
            action: Action performed
            resource: Resource affected
            user_id: User performing action
            result: Action result (success/failure)
            details: Additional details
        """
        audit_data = {
            'audit_action': action,
            'audit_resource': resource,
            'audit_user': user_id,
            'audit_result': result,
            'audit_timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        
        if details:
            audit_data['audit_details'] = details
        
        self.info(f"Audit: {action} on {resource} by {user_id} - {result}", 
                 **audit_data)
    
    def log_lambda_event(self, event: Dict[str, Any], context: Any):
        """
        Log Lambda invocation details
        
        Args:
            event: Lambda event
            context: Lambda context
        """
        request_context = {
            'request_id': context.request_id,
            'function_name': context.function_name,
            'function_version': context.function_version,
            'memory_limit': context.memory_limit_in_mb,
            'remaining_time': context.get_remaining_time_in_millis()
        }
        
        # Extract API Gateway context if present
        if 'requestContext' in event:
            api_context = event['requestContext']
            request_context.update({
                'api_request_id': api_context.get('requestId'),
                'api_stage': api_context.get('stage'),
                'source_ip': api_context.get('identity', {}).get('sourceIp'),
                'user_agent': api_context.get('identity', {}).get('userAgent')
            })
        
        self.info("Lambda invocation started", request_context=request_context)
    
    def log_performance(self, operation: str, duration_ms: float, 
                       success: bool = True, **kwargs):
        """
        Log performance metrics
        
        Args:
            operation: Operation name
            duration_ms: Duration in milliseconds
            success: Whether operation succeeded
            **kwargs: Additional metrics
        """
        perf_data = {
            'operation': operation,
            'duration_ms': duration_ms,
            'success': success,
            'performance_metric': True
        }
        perf_data.update(kwargs)
        
        level = 'info' if success else 'warning'
        self.log(level, f"Performance: {operation} took {duration_ms}ms", **perf_data)

# Singleton instance
_logger_instance = None

def get_logger(service_name: Optional[str] = None) -> StructuredLogger:
    """
    Get or create logger instance
    
    Args:
        service_name: Service name (uses env var if not provided)
        
    Returns:
        StructuredLogger instance
    """
    global _logger_instance
    
    if _logger_instance is None:
        service = service_name or os.environ.get('AWS_LAMBDA_FUNCTION_NAME', 'mowd-whisper')
        log_level = os.environ.get('LOG_LEVEL', 'INFO')
        _logger_instance = StructuredLogger(service, log_level)
    
    return _logger_instance

# Convenience decorators
def log_execution(func):
    """Decorator to log function execution with timing"""
    def wrapper(*args, **kwargs):
        logger = get_logger()
        start_time = datetime.utcnow()
        
        try:
            logger.debug(f"Starting {func.__name__}", function=func.__name__)
            result = func(*args, **kwargs)
            
            duration = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.log_performance(func.__name__, duration, success=True)
            
            return result
            
        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.log_performance(func.__name__, duration, success=False, 
                                 error=str(e))
            logger.error(f"Error in {func.__name__}: {str(e)}", 
                        function=func.__name__, exception_type=type(e).__name__)
            raise
    
    return wrapper

# Example usage:
"""
from logging.structured_logger import get_logger, log_execution

logger = get_logger()

@log_execution
def process_audio(file_path):
    logger.info("Processing audio file", file_path=file_path, file_size=1024)
    
    # Log security event
    logger.security_event(
        "FILE_ACCESS",
        {"file": file_path, "action": "read"},
        severity="INFO",
        user_id="user123"
    )
    
    # Log audit trail
    logger.audit_trail(
        action="TRANSCRIBE",
        resource=file_path,
        user_id="user123",
        result="success"
    )
"""