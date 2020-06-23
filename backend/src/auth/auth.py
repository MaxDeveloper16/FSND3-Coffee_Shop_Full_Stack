import json
from flask import request, _request_ctx_stack, abort, current_app
from functools import wraps

from urllib.request import urlopen
from jose import jwt
import logging


AUTH0_DOMAIN = 'dev-maxdeveloper.us.auth0.com'
ALGORITHMS = ['RS256']
API_AUDIENCE = 'Coffee_Shop'

## AuthError Exception
'''
AuthError Exception
A standardized way to communicate auth failure modes
'''
class AuthError(Exception):
    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code


## Auth Header
def get_token_auth_header():
    '''
        Get the header from the request
            Raise an AuthError if no header is present
        Split bearer and the token
            Raise an AuthError if the header is malformed
        return the token part of the header
    '''
    if 'Authorization' not in request.headers:
        raise AuthError(
            {
                "code": "authorization_header_missing",
                "description": "Authorization header is expected.",
            },
            401,
        )

    auth_header = request.headers['Authorization']
    header_parts = auth_header.split(' ')

    if len(header_parts) != 2:
        raise AuthError(
            {
                "code": "invalid_header",
                "description": 'Authorization header must be exactly as '
                               '"Bearer token".',
            },
            401,
        )
    elif header_parts[0].lower() != 'bearer':
        raise AuthError(
            {
                "code": "invalid_header",
                "description": 'Authorization header must start with '
                               '"Bearer".',
            },
            401,
        )

    return header_parts[1]


def check_permissions(permission, payload):
    '''
        @INPUTS
            permission: string permission (i.e. 'post:drink')
            payload: decoded jwt payload

        Raise an AuthError if permissions are not included in the payload
            !!NOTE check your RBAC settings in Auth0
        Raise an AuthError if the requested permission string is not in the payload permissions array
        return true otherwise
    '''
    permissions = payload.get('permissions')
    if permissions and permission in permissions:
        return True

    return False

def verify_decode_jwt(token):
    '''
        @INPUTS
            token: a json web token (string)

        it should be an Auth0 token with key id (kid)
        it should verify the token using Auth0 /.well-known/jwks.json
        it should decode the payload from the token
        it should validate the claims
        return the decoded payload

        !!NOTE urlopen has a common certificate error described here: https://stackoverflow.com/questions/50236117/scraping-ssl-certificate-verify-failed-error-for-http-en-wikipedia-org
    '''
    if current_app.config.get('TESTING'):
        if not request.args.get('verify_token'):
            return jwt.get_unverified_claims(token)

    jsonurl = urlopen(f'https://{AUTH0_DOMAIN}/.well-known/jwks.json')
    jwks = json.loads(jsonurl.read())

    # Get the data in the header
    unverified_header = jwt.get_unverified_header(token)

    # choose our key
    rsa_key = {}
    if 'kid' not in unverified_header:
        raise AuthError({
            'code': 'invalid_header',
            'description': 'Authorization malformed'
        }, 401)

    for key in jwks['keys']:
        if key['kid'] == unverified_header['kid']:
            rsa_key = {
                'kty': key['kty'],
                'kid': key['kid'],
                'use': key['use'],
                'n': key['n'],
                'e': key['e']
            }

    if rsa_key:
        try:
            # use the key to validate the jwt
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=ALGORITHMS,
                audience=API_AUDIENCE,
                issuer='https://' + AUTH0_DOMAIN + '/'
            )
            return payload

        except jwt.ExpiredSignatureError:
            raise AuthError({
                'code': 'token_expired',
                'description': 'Token expired'
            }, 401)

        except jwt.JWTClaimsError:
            raise AuthError({
                'code': 'invalid_claims',
                'description': 'Incorrect claims. Please check '
                               'the audience and issuer.'
            }, 401)

        except Exception:
            raise AuthError({
                'code': 'invalid_header',
                'description': 'Unable to parse authentication token.'
            }, 400)

    raise AuthError({
        'code': 'invalid_header',
        'description': 'Unable to find the appropriate key.'
    }, 400)
  

    

def requires_auth(permission=''):
    '''
    @INPUTS
        permission: string permission (i.e. 'post:drink')

    get_token_auth_header method to get the token
    verify_decode_jwt method to decode the jwt
    check_permissions method validate claims and check the requested permission
    return the decorator which passes the decoded payload to the decorated method
    '''
    def requires_auth_decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            token = get_token_auth_header()
            payload = verify_decode_jwt(token)
            if not check_permissions(permission, payload):
                raise AuthError({
                    'code': 'no_permission',
                    'description': 'No Permission'
                }, 401)

            return f(payload, *args, **kwargs)

        return wrapper
    return requires_auth_decorator