"""
JWT Validator Middleware
Validates Cognito-issued JWTs for API requests
"""

import json
import time
import logging
from typing import Dict, Any, Optional
from functools import wraps
import jwt
from jwt import PyJWKClient
import os

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Configuration
REGION = os.environ.get('AWS_REGION', 'us-east-1')
USER_POOL_ID = os.environ['COGNITO_USER_POOL_ID']
CLIENT_ID = os.environ['COGNITO_CLIENT_ID']

# Cognito JWKS URL
JWKS_URL = f'https://cognito-idp.{REGION}.amazonaws.com/{USER_POOL_ID}/.well-known/jwks.json'

# Initialize JWKS client with caching
jwks_client = PyJWKClient(JWKS_URL, cache_keys=True, lifespan=3600)

class JWTValidator:
    """
    Validates JWT tokens from AWS Cognito
    """
    
    def __init__(self):
        self.region = REGION
        self.user_pool_id = USER_POOL_ID
        self.client_id = CLIENT_ID
        self.issuer = f'https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}'
    
    def validate_token(self, token: str) -> Dict[str, Any]:
        """
        Validate a JWT token
        
        Args:
            token: JWT token string
            
        Returns:
            Decoded token claims
            
        Raises:
            Exception: If token is invalid
        """
        try:
            # Get the signing key from JWKS
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            
            # Decode and verify the token
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer=self.issuer,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_nbf": True,
                    "verify_iat": True,
                    "verify_aud": True,
                    "verify_iss": True,
                    "require": ["exp", "iat", "auth_time", "cognito:username"]
                }
            )
            
            # Additional validation
            self._validate_claims(claims)
            
            return claims
            
        except jwt.ExpiredSignatureError:
            logger.error("Token has expired")
            raise Exception("Token has expired")
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid token: {str(e)}")
            raise Exception(f"Invalid token: {str(e)}")
        except Exception as e:
            logger.error(f"Token validation error: {str(e)}")
            raise Exception(f"Token validation failed: {str(e)}")
    
    def _validate_claims(self, claims: Dict[str, Any]) -> None:
        """
        Perform additional claim validation
        
        Args:
            claims: Decoded JWT claims
            
        Raises:
            Exception: If claims are invalid
        """
        # Check token use
        if claims.get('token_use') not in ['id', 'access']:
            raise Exception("Invalid token_use claim")
        
        # Check authentication time (max 24 hours)
        auth_time = claims.get('auth_time', 0)
        if time.time() - auth_time > 86400:
            raise Exception("Authentication too old, please re-authenticate")
        
        # Validate custom attributes
        if 'custom:school_id' not in claims:
            raise Exception("Missing required school_id attribute")
        
        if 'custom:role' not in claims:
            raise Exception("Missing required role attribute")
        
        # Validate role values
        valid_roles = ['admin', 'teacher', 'student', 'viewer']
        if claims['custom:role'] not in valid_roles:
            raise Exception(f"Invalid role: {claims['custom:role']}")

def extract_token(event: Dict[str, Any]) -> Optional[str]:
    """
    Extract JWT token from Lambda event
    
    Args:
        event: API Gateway Lambda event
        
    Returns:
        JWT token string or None
    """
    # Check Authorization header
    headers = event.get('headers', {})
    auth_header = headers.get('Authorization') or headers.get('authorization')
    
    if auth_header and auth_header.startswith('Bearer '):
        return auth_header[7:]
    
    # Check for token in query parameters (not recommended)
    query_params = event.get('queryStringParameters', {})
    if query_params and 'token' in query_params:
        logger.warning("Token passed in query parameters - security risk")
        return query_params['token']
    
    return None

def requires_auth(handler):
    """
    Decorator for Lambda handlers requiring authentication
    
    Args:
        handler: Lambda handler function
        
    Returns:
        Wrapped handler with authentication
    """
    @wraps(handler)
    def wrapper(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
        try:
            # Extract token
            token = extract_token(event)
            if not token:
                return {
                    'statusCode': 401,
                    'body': json.dumps({'error': 'Missing authentication token'})
                }
            
            # Validate token
            validator = JWTValidator()
            claims = validator.validate_token(token)
            
            # Add claims to event for handler use
            event['claims'] = claims
            event['user_id'] = claims.get('cognito:username')
            event['school_id'] = claims.get('custom:school_id')
            event['role'] = claims.get('custom:role')
            
            # Call the actual handler
            return handler(event, context)
            
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            return {
                'statusCode': 401,
                'body': json.dumps({'error': str(e)})
            }
    
    return wrapper

def requires_role(*allowed_roles):
    """
    Decorator for role-based access control
    
    Args:
        allowed_roles: List of allowed roles
        
    Returns:
        Decorator function
    """
    def decorator(handler):
        @wraps(handler)
        def wrapper(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
            # First validate authentication
            auth_wrapper = requires_auth(handler)
            result = auth_wrapper(event, context)
            
            # If authentication failed, return the error
            if isinstance(result, dict) and result.get('statusCode') == 401:
                return result
            
            # Check role
            user_role = event.get('role')
            if user_role not in allowed_roles:
                logger.warning(f"Access denied for role {user_role}, required: {allowed_roles}")
                return {
                    'statusCode': 403,
                    'body': json.dumps({
                        'error': f'Insufficient permissions. Required role: {allowed_roles}'
                    })
                }
            
            return result
        
        return wrapper
    
    return decorator

def get_user_context(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract user context from authenticated event
    
    Args:
        event: Authenticated Lambda event
        
    Returns:
        User context dictionary
    """
    return {
        'user_id': event.get('user_id'),
        'school_id': event.get('school_id'),
        'role': event.get('role'),
        'email': event.get('claims', {}).get('email'),
        'auth_time': event.get('claims', {}).get('auth_time')
    }

# Example usage in Lambda handler:
"""
from auth.jwt_validator import requires_auth, requires_role

@requires_auth
def get_transcript_handler(event, context):
    user_context = get_user_context(event)
    # Handler logic here
    
@requires_role('admin', 'teacher')
def delete_lecture_handler(event, context):
    # Only admins and teachers can delete
    pass
"""