# auth_utils.py

import os
import json
import logging
import azure.functions as func
from functools import wraps
from urllib.request import urlopen
import jwt
from jwt.algorithms import RSAAlgorithm

# Konfigurasi dari Environment Variables
AUTH0_DOMAIN = os.environ.get("AUTH0_DOMAIN") # e.g., dev-e8ui3zf8tpnbr3xm.us.auth0.com
API_AUDIENCE = os.environ.get("API_AUDIENCE") # e.g., https://bisbi.api.identifier
ALGORITHMS = ["RS256"]

# Cache sederhana untuk JWKS
jwks_cache = None

class AuthError(Exception):
    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code

def get_jwks():
    global jwks_cache
    if jwks_cache:
        return jwks_cache
    try:
        jsonurl = urlopen(f"https://{AUTH0_DOMAIN}/.well-known/jwks.json") # Corrected https
        jwks = json.loads(jsonurl.read())
        jwks_cache = jwks
        return jwks
    except Exception as e:
        logging.error(f"Failed to fetch JWKS: {e}")
        raise AuthError({"code": "jwks_fetch_error",
                         "description": "Unable to fetch JWKS."}, 500)


def get_token_auth_header(req: func.HttpRequest):
    """Obtains the Access Token from the Authorization Header
    """
    auth = req.headers.get("Authorization", None)
    if not auth:
        raise AuthError({"code": "authorization_header_missing",
                        "description": "Authorization header is expected"}, 401)

    parts = auth.split()

    if parts[0].lower() != "bearer":
        raise AuthError({"code": "invalid_header",
                        "description": "Authorization header must start with Bearer"}, 401)
    elif len(parts) == 1:
        raise AuthError({"code": "invalid_header",
                        "description": "Token not found"}, 401)
    elif len(parts) > 2:
        raise AuthError({"code": "invalid_header",
                        "description": "Authorization header must be Bearer token"}, 401)

    token = parts[1]
    return token

def decode_verify_token(token):
    jwks = get_jwks()
    try:
        unverified_header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as e:
        logging.error(f"JWT Header Error: {e}")
        raise AuthError({"code": "invalid_header",
                        "description": "Unable to parse authentication token."}, 401)
    
    rsa_key = {}
    if 'kid' not in unverified_header:
        raise AuthError({"code": "invalid_header",
                         "description": "Authorization malformed."}, 401)

    for key in jwks["keys"]:
        if key["kid"] == unverified_header["kid"]:
            rsa_key = {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"]
            }
            # Jika menggunakan PyJWT < 2.0, Anda mungkin perlu ini:
            # rsa_key = RSAAlgorithm.from_jwk(json.dumps(key))
            break
    
    if rsa_key:
        try:
            payload = jwt.decode(
                token,
                key=jwt.PyJWK(rsa_key).key,
                algorithms=ALGORITHMS,
                audience=API_AUDIENCE,
                issuer=f"https://{AUTH0_DOMAIN}/" # Corrected https
            )
            return payload
        except jwt.ExpiredSignatureError:
            logging.warning("Token is expired")
            raise AuthError({"code": "token_expired",
                            "description": "token is expired"}, 401)
        except jwt.InvalidAudienceError:
            logging.warning(f"Incorrect audience. Expected: {API_AUDIENCE}")
            raise AuthError({"code": "invalid_audience",
                            "description": "incorrect audience"}, 401)
        except jwt.InvalidIssuerError:
            logging.warning(f"Incorrect issuer. Expected: https://{AUTH0_DOMAIN}/") # Corrected https
            raise AuthError({"code": "invalid_issuer",
                            "description": "incorrect issuer"}, 401)
        except jwt.PyJWTError as e:
            logging.error(f"JWT Decode Error: {e}")
            raise AuthError({"code": "invalid_token",
                            "description": "Unable to parse authentication token."}, 401)
        except Exception as e:
            logging.error(f"General error during token decoding: {e}")
            raise AuthError({"code": "internal_error",
                            "description": "An internal error occurred."}, 500)
    
    logging.warning("No appropriate key found in JWKS")
    raise AuthError({"code": "invalid_header",
                    "description": "Unable to find appropriate key"}, 401)


# Decorator untuk Azure Functions HTTP Trigger
def require_auth(func_to_decorate):
    @wraps(func_to_decorate)
    def wrapper(req: func.HttpRequest, *args, **kwargs) -> func.HttpResponse:
        try:
            token = get_token_auth_header(req)
            payload = decode_verify_token(token)
            user_id = payload.get("sub") # Assuming "sub" is the claim for user_id

            if not user_id:
                logging.error("User ID (sub) not found in JWT payload.")
                raise AuthError({"code": "user_id_missing",
                                 "description": "User ID not found in token."}, 401)

            # Inject user_id into the req object
            setattr(req, 'user_id_injected', user_id)
            
            # Call the original decorated function (the handler)
            return func_to_decorate(req, *args, **kwargs)

        except AuthError as e:
            logging.warning(f"AuthError in decorator: {e.error}")
            return func.HttpResponse(
                json.dumps(e.error),
                status_code=e.status_code,
                mimetype="application/json"
            )
        except Exception as e:
            logging.error(f"Unexpected error in auth decorator: {str(e)}")
            # import traceback # Already imported system-wide for Azure Functions
            # logging.error(traceback.format_exc())
            return func.HttpResponse(
                json.dumps({"code": "internal_server_error", "description": "An internal error occurred during authentication."}),
                status_code=500,
                mimetype="application/json"
            )
    return wrapper