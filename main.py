"""
HealthOS API — Medical-grade AI health optimization system for college students.

Features:
- JWT authentication with rate limiting
- Comprehensive error handling
- Input validation with Pydantic models
- OpenAPI/Swagger documentation
- Supabase + local fallback storage
- Streaming chat responses
- Real-time feedback learning

Run: uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

import os
import re
import sys
import json
import bcrypt
import jwt as _jwt
import logging
from typing import cast as _cast, Optional
from datetime import datetime
from uuid import uuid4
from fastapi import FastAPI, Form, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from dotenv import load_dotenv

load_dotenv()

# ─── Logging Setup ────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

SECRET = os.environ.get("SECRET_KEY", "elden_ring")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

os.makedirs("user_profiles", exist_ok=True)

def _profile_path(username: str) -> str:
    safe = re.sub(r"[^\w\-]", "_", username.lower())
    return os.path.join("user_profiles", f"{safe}.json")

# --- Supabase (optional) ---
try:
    from supabase import create_client
    _sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
    USE_SUPABASE = True
    logger.info("✓ Supabase connected")
except Exception as e:
    USE_SUPABASE = False
    logger.info(f"✗ Supabase unavailable: {e} (using local fallback)")

# Import exceptions and models (with graceful fallback)
# Define fallback classes first
class HealthOSAPIError(Exception):
    """Base exception class."""
    def to_response(self):
        return JSONResponse({"success": False, "error": str(self)}, status_code=400)

class ValidationError(HealthOSAPIError):
    """Validation error."""
    pass

class InternalServerError(HealthOSAPIError):
    """Internal server error."""
    pass

def get_rate_limiter():
    """Fallback rate limiter."""
    class FallbackRateLimiter:
        def check_rate_limit(self, request, endpoint, username=None):
            pass
    return FallbackRateLimiter()

# Try to import actual implementations
try:
    from api_exceptions import (
        HealthOSAPIError as _HealthOSAPIError,
        AuthenticationError,
        AuthorizationError,
        ValidationError as _ValidationError,
        ResourceNotFoundError,
        RateLimitError,
        ConflictError,
        InternalServerError as _InternalServerError,
        ExternalServiceError,
    )
    from api_models import AuthResponse, UserResponse, ErrorResponse
    from rate_limiter import get_rate_limiter as _get_rate_limiter
    
    # Use imported versions
    HealthOSAPIError = _HealthOSAPIError  # type: ignore
    ValidationError = _ValidationError  # type: ignore
    InternalServerError = _InternalServerError  # type: ignore
    get_rate_limiter = _get_rate_limiter  # type: ignore
    USE_API_UTILS = True
except ImportError as e:
    logger.warning(f"API utilities not available: {e} (using basic error handling)")
    USE_API_UTILS = False
    AuthenticationError = HealthOSAPIError  # type: ignore
    AuthorizationError = HealthOSAPIError  # type: ignore
    ResourceNotFoundError = HealthOSAPIError  # type: ignore
    RateLimitError = HealthOSAPIError  # type: ignore
    ConflictError = HealthOSAPIError  # type: ignore
    ExternalServiceError = HealthOSAPIError  # type: ignore

# ══════════════════════════════════════════════
# APP SETUP
# ══════════════════════════════════════════════

app = FastAPI(
    title="HealthOS API",
    description="Medical-grade AI health optimization system for college students",
    version="3.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

# Configure CORS for both development and production
allowed_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
]

# Add Vercel domains in production
if os.environ.get("VERCEL_URL"):
    allowed_origins.extend([
        f"https://{os.environ.get('VERCEL_URL')}",
        "https://*.vercel.app",
    ])

# Allow custom domain if set
if frontend_url := os.environ.get("FRONTEND_URL"):
    allowed_origins.append(frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_origin_regex=r"https://.*\.vercel\.app",
)

# Request/response logging middleware
import time
from starlette.middleware.base import BaseHTTPMiddleware

class LoggingMiddleware(BaseHTTPMiddleware):
    """Log all HTTP requests and responses with structured JSON."""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        try:
            from structured_logging import logger as struct_logger
            struct_logger.log_request(request.method, request.url.path)
            logger_available = True
        except ImportError:
            logger_available = False
        
        response = await call_next(request)
        
        if logger_available:
            elapsed_ms = (time.time() - start_time) * 1000
            from structured_logging import logger as struct_logger
            struct_logger.log_response(response.status_code, elapsed_ms)
        
        return response

app.add_middleware(LoggingMiddleware)

# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors."""
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": "Request validation failed",
            "error_code": "VALIDATION_ERROR",
            "details": {
                "errors": [
                    {
                        "field": ".".join(str(x) for x in err["loc"]),
                        "message": err["msg"],
                    }
                    for err in exc.errors()
                ]
            },
        },
    )

@app.exception_handler(HealthOSAPIError)
async def healthos_exception_handler(request: Request, exc: HealthOSAPIError):
    """Handle HealthOS custom exceptions."""
    logger.warning(f"API Error: {getattr(exc, 'error_code', 'UNKNOWN')} - {str(exc)}")
    if hasattr(exc, 'to_response'):
        return exc.to_response()
    return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

# ══════════════════════════════════════════════
# MONITORING & HEALTH CHECKS
# ══════════════════════════════════════════════

health_checker = None
perf_metrics = None
churn_predictor = None

try:
    from monitoring import HealthCheck, PerformanceMetrics, capture_exception
    health_checker = HealthCheck()
    perf_metrics = PerformanceMetrics()
    MONITORING_ENABLED = True
except ImportError:
    MONITORING_ENABLED = False
    logger.warning("Monitoring module not available")

# Import churn prediction model
try:
    from model.churn_prediction import churn_predictor as _churn_predictor
    churn_predictor = _churn_predictor
    logger.info("✓ Churn prediction model loaded")
except ImportError as e:
    logger.warning(f"Churn prediction module not available: {e}")

# Register health checks
if MONITORING_ENABLED and health_checker:
    # Supabase health check
    def check_supabase() -> tuple[bool, dict]:
        """Check Supabase connectivity."""
        if not USE_SUPABASE:
            return False, {"status": "not_configured"}
        try:
            _sb.table("users").select("id").limit(1).execute()
            return True, {"status": "connected"}
        except Exception as e:
            return False, {"status": "disconnected", "error": str(e)}
    
    # Gemini health check
    def check_gemini() -> tuple[bool, dict]:
        """Check Gemini API key is configured."""
        if GEMINI_API_KEY:
            return True, {"status": "configured"}
        return False, {"status": "missing API key"}
    
    # ChromaDB health check
    def check_chromadb() -> tuple[bool, dict]:
        """Check ChromaDB availability."""
        try:
            import chromadb
            db = chromadb.PersistentClient(path="model/chroma_db")
            collections = db.list_collections()
            return True, {"status": "connected", "collections": len(collections)}
        except Exception as e:
            return False, {"status": "disconnected", "error": str(e)}
    
    health_checker.register("supabase", check_supabase, critical=True)
    health_checker.register("gemini", check_gemini, critical=False)
    health_checker.register("chromadb", check_chromadb, critical=False)

@app.get("/health", tags=["monitoring"])
async def health_check_endpoint():
    """System health check endpoint.
    
    Returns comprehensive health status of all critical services.
    Used by load balancers and monitoring systems.
    """
    if MONITORING_ENABLED and health_checker:
        status = await health_checker.run_all()
        status_code = 200 if status["healthy"] else 503
        return JSONResponse(status, status_code=status_code)
    return JSONResponse({
        "healthy": True,
        "services": {"basic": {"healthy": True}},
    }, status_code=200)

@app.get("/metrics", tags=["monitoring"])
def metrics_endpoint():
    """Performance metrics endpoint.
    
    Returns API performance statistics (requests, response times, error rates).
    """
    if MONITORING_ENABLED and perf_metrics:
        return JSONResponse(perf_metrics.get_summary())
    return JSONResponse({"message": "Metrics not available"})

def _make_token(username: str, user_id: Optional[str] = None) -> str:
    """Create JWT token for user."""
    try:
        payload = {"username": username}
        if user_id is not None:
            payload["user_id"] = user_id
        return _jwt.encode(payload, SECRET, algorithm="HS256")
    except Exception as e:
        logger.error(f"Token creation failed: {e}")
        raise InternalServerError("Failed to create authentication token") if USE_API_UTILS else Exception("Token creation failed")

def _decode_token(request: Request) -> Optional[dict]:
    """
    Extract and decode Bearer token from Authorization header.
    
    Returns:
        Decoded payload dict if valid, None otherwise
    """
    auth = request.headers.get("Authorization", "").strip()
    if not auth.startswith("Bearer "):
        return None
    
    token = auth[7:]  # Remove "Bearer " prefix
    try:
        return _jwt.decode(token, SECRET, algorithms=["HS256"])
    except _jwt.ExpiredSignatureError:
        logger.warning("Expired token presented")
        return None
    except _jwt.InvalidTokenError:
        logger.warning("Invalid token presented")
        return None
    except Exception as e:
        logger.error(f"Token decode error: {e}")
        return None

def _validate_username(username: str) -> None:
    """Validate username format."""
    if not (3 <= len(username) <= 50):
        raise ValidationError("Username must be 3-50 characters")
    if not re.match(r"^[a-zA-Z0-9_-]+$", username):
        raise ValidationError(
            "Username must contain only letters, numbers, hyphen, underscore"
        ) if USE_API_UTILS else ValueError("Invalid username format")

def _validate_password(password: str) -> None:
    """Validate password strength."""
    if not (8 <= len(password) <= 128):
        raise ValidationError("Password must be 8-128 characters")

def _local_login(username: str, password: str) -> tuple[bool, Optional[str], Optional[str]]:
    """Local file-based login (fallback)."""
    try:
        with open("users.json", "r") as f:
            users = json.load(f)
        for u in users:
            if u["username"] == username:
                if bcrypt.checkpw(password.encode(), u["password"].encode()):
                    return True, str(u.get("id")), None
                return False, None, "Incorrect password"
        return False, None, "User not found"
    except FileNotFoundError:
        return False, None, "No users registered yet"
    except Exception as e:
        logger.error(f"Local login error: {e}")
        return False, None, "Login service unavailable"

def _local_signup(username: str, password: str) -> tuple[bool, Optional[str], Optional[str]]:
    """Local file-based signup (fallback)."""
    try:
        try:
            with open("users.json", "r") as f:
                users = json.load(f)
        except FileNotFoundError:
            users = []
        
        # Check for duplicates
        if any(u["username"] == username for u in users):
            return False, None, "Username already taken"
        
        # Create new user
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        new_id = len(users) + 1
        users.append({"id": new_id, "username": username, "password": hashed})
        
        with open("users.json", "w") as f:
            json.dump(users, f, indent=2)
        
        return True, str(new_id), None
    except Exception as e:
        logger.error(f"Local signup error: {e}")
        return False, None, "Signup service unavailable"

def _local_change_password(username: str, current_password: str, new_password: str) -> tuple[bool, Optional[str]]:
    """Change password in local users.json store."""
    try:
        with open("users.json", "r") as f:
            users = json.load(f)

        updated = False
        for user in users:
            if user.get("username") == username:
                if not bcrypt.checkpw(current_password.encode(), user["password"].encode()):
                    return False, "Current password is incorrect"
                user["password"] = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
                updated = True
                break

        if not updated:
            return False, "User not found"

        with open("users.json", "w") as f:
            json.dump(users, f, indent=2)

        return True, None
    except FileNotFoundError:
        return False, "No local users found"
    except Exception as e:
        logger.error(f"Local change password error: {e}")
        return False, "Password update service unavailable"

def _water_path(username: str) -> str:
    return _profile_path(username).replace(".json", "_water.json")

def _workouts_path(username: str) -> str:
    return _profile_path(username).replace(".json", "_workouts.json")

# ══════════════════════════════════════════════
# HEALTH CHECK ENDPOINT
# ══════════════════════════════════════════════

@app.get(
    "/api/health",
    tags=["System"],
    summary="Health check",
    description="Check system and service health",
    responses={
        200: {
            "description": "System is healthy",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "status": "healthy",
                        "timestamp": "2026-03-01T10:30:00Z",
                        "services": {
                            "ollama": "healthy",
                            "supabase": "healthy",
                            "nutrition_db": "healthy",
                        },
                    }
                }
            },
        }
    },
)
async def health_check():
    """Check system health and service availability."""
    services = {}
    
    # Check Gemini
    services["gemini"] = "healthy" if GEMINI_API_KEY else "missing API key"
    
    # Check Supabase
    services["supabase"] = "healthy" if USE_SUPABASE else "unavailable (using local fallback)"
    
    # Check nutrition DB
    try:
        from model import nutrition_db
        services["nutrition_db"] = "healthy" if nutrition_db.is_loaded() else "loading"
    except Exception as e:
        services["nutrition_db"] = f"error: {str(e)[:30]}"
    
    # Determine overall status
    critical_services = [s for s, status in services.items() if "unavailable" in str(status)]
    overall_status = "degraded" if critical_services else "healthy"
    
    return JSONResponse({
        "success": True,
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "services": services,
    })

# ══════════════════════════════════════════════
# AUTH ENDPOINTS
# ══════════════════════════════════════════════

@app.post(
    "/login",
    tags=["Auth"],
    summary="User login",
    description="Authenticate user and return JWT token",
    responses={
        200: {
            "description": "Login successful",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "username": "alice",
                    }
                }
            },
        },
        401: {
            "description": "Invalid credentials",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": "Incorrect password",
                        "error_code": "AUTH_FAILED",
                    }
                }
            },
        },
    },
)
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    """Authenticate user and return JWT token."""
    try:
        # Rate limiting
        try:
            rate_limiter = get_rate_limiter()
            rate_limiter.check_rate_limit(request, "/api/login")
        except:
            pass  # Graceful fallback if rate limiter fails
        
        # Validation
        try:
            _validate_username(username)
            _validate_password(password)
        except Exception as e:
            logger.warning(f"Validation failed: {e}")
            if USE_API_UTILS and isinstance(e, ValidationError):
                raise
            return JSONResponse({"success": False, "error": str(e)}, status_code=422)
        
        # Try Supabase first
        if USE_SUPABASE:
            try:
                res = _sb.table("users").select("*").eq("username", username).execute()
                if res.data:
                    row = _cast(dict, res.data[0])
                    if bcrypt.checkpw(password.encode(), row["password"].encode()):
                        token = _make_token(username, row.get("id"))
                        logger.info(f"✓ Login successful: {username} (Supabase)")
                        return JSONResponse({
                            "success": True,
                            "token": token,
                            "username": username,
                            "user_id": row.get("id"),
                        })
                    return JSONResponse(
                        {"success": False, "error": "Incorrect password", "error_code": "AUTH_FAILED"},
                        status_code=401
                    )
                return JSONResponse(
                    {"success": False, "error": "User not found", "error_code": "NOT_FOUND"},
                    status_code=404
                )
            except Exception as e:
                logger.warning(f"Supabase login failed: {e}, falling back to local")
        
        # Fallback to local
        ok, uid, err = _local_login(username, password)
        if ok:
            token = _make_token(username, uid)
            logger.info(f"✓ Login successful: {username} (local)")
            return JSONResponse({
                "success": True,
                "token": token,
                "username": username,
                "user_id": uid,
            })
        
        logger.warning(f"✗ Login failed: {username} - {err}")
        return JSONResponse(
            {"success": False, "error": err, "error_code": "AUTH_FAILED"},
            status_code=401
        )
    
    except Exception as e:
        logger.error(f"Login endpoint error: {e}", exc_info=True)
        return JSONResponse(
            {
                "success": False,
                "error": "Internal server error",
                "error_code": "INTERNAL_SERVER_ERROR",
            },
            status_code=500,
        )

@app.post(
    "/api/signup",
    tags=["Auth"],
    summary="User registration",
    description="Create new user account and return JWT token",
    responses={
        200: {"description": "Signup successful"},
        409: {"description": "Username already taken"},
    },
)
async def signup(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
):
    """Create new user account."""
    try:
        # Rate limiting
        try:
            rate_limiter = get_rate_limiter()
            rate_limiter.check_rate_limit(request, "/api/signup")
        except:
            pass
        
        # Validation
        try:
            _validate_username(username)
            _validate_password(password)
            if password != password_confirm:
                raise ValidationError("Passwords do not match")
        except Exception as e:
            logger.warning(f"Signup validation failed: {e}")
            if USE_API_UTILS and isinstance(e, ValidationError):
                raise
            return JSONResponse({"success": False, "error": str(e)}, status_code=422)
        
        # Try Supabase first
        if USE_SUPABASE:
            try:
                existing = _sb.table("users").select("id").eq("username", username).execute()
                if existing.data:
                    return JSONResponse(
                        {"success": False, "error": "Username already taken", "error_code": "CONFLICT"},
                        status_code=409,
                    )
                
                hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
                res = _sb.table("users").insert({
                    "username": username,
                    "password": hashed,
                }).execute()
                
                uid: Optional[str] = None
                if res.data:
                    user_row = _cast(dict, res.data[0])
                    uid = _cast(Optional[str], user_row.get("id"))
                token = _make_token(username, uid)
                logger.info(f"✓ Signup successful: {username} (Supabase)")
                return JSONResponse({
                    "success": True,
                    "token": token,
                    "username": username,
                    "user_id": uid,
                })
            except Exception as e:
                logger.warning(f"Supabase signup failed: {e}, falling back to local")
        
        # Fallback to local
        ok, uid, err = _local_signup(username, password)
        if ok:
            token = _make_token(username, uid)
            logger.info(f"✓ Signup successful: {username} (local)")
            return JSONResponse({
                "success": True,
                "token": token,
                "username": username,
                "user_id": uid,
            })
        
        status_code = 409 if "already taken" in (err or "") else 400
        logger.warning(f"✗ Signup failed: {username} - {err}")
        return JSONResponse(
            {"success": False, "error": err, "error_code": "SIGNUP_FAILED"},
            status_code=status_code,
        )
    
    except Exception as e:
        logger.error(f"Signup endpoint error: {e}", exc_info=True)
        return JSONResponse(
            {
                "success": False,
                "error": "Internal server error",
                "error_code": "INTERNAL_SERVER_ERROR",
            },
            status_code=500,
        )

@app.post(
    "/api/logout",
    tags=["Auth"],
    summary="User logout",
    description="Logout user (JWT is stateless, just delete token on client)",
)
async def logout(request: Request):
    """Logout user."""
    payload = _decode_token(request)
    if payload:
        logger.info(f"✓ Logout: {payload.get('username')}")
    return JSONResponse({"success": True})


@app.post(
    "/api/change-password",
    tags=["Auth"],
    summary="Change password",
    description="Change authenticated user's password",
)
async def change_password(request: Request):
    """Change current user's password."""
    try:
        payload = _decode_token(request)
        if not payload:
            return JSONResponse(
                {"success": False, "error": "Not authenticated", "error_code": "AUTH_FAILED"},
                status_code=401,
            )

        body = await request.json()
        username = payload["username"]
        user_id = payload.get("user_id")

        current_password = str(body.get("current_password", "")).strip()
        new_password = str(body.get("new_password", "")).strip()
        confirm_password = str(body.get("confirm_password", "")).strip()

        if not current_password or not new_password:
            return JSONResponse(
                {"success": False, "error": "Current and new password are required", "error_code": "VALIDATION_ERROR"},
                status_code=422,
            )

        if confirm_password and new_password != confirm_password:
            return JSONResponse(
                {"success": False, "error": "New passwords do not match", "error_code": "VALIDATION_ERROR"},
                status_code=422,
            )

        _validate_password(new_password)

        # Try Supabase first
        if USE_SUPABASE:
            try:
                row = None
                if user_id:
                    res = _sb.table("users").select("id,username,password").eq("id", user_id).execute()
                    if res.data:
                        row = _cast(dict, res.data[0])
                if not row:
                    res = _sb.table("users").select("id,username,password").eq("username", username).execute()
                    if res.data:
                        row = _cast(dict, res.data[0])

                if row:
                    if not bcrypt.checkpw(current_password.encode(), row["password"].encode()):
                        return JSONResponse(
                            {"success": False, "error": "Current password is incorrect", "error_code": "AUTH_FAILED"},
                            status_code=401,
                        )

                    new_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
                    _sb.table("users").update({"password": new_hash}).eq("id", row.get("id")).execute()
                    logger.info(f"✓ Password changed: {username} (Supabase)")
                    return JSONResponse({"success": True})
            except Exception as e:
                logger.warning(f"Supabase password change failed: {e}, falling back to local")

        ok, err = _local_change_password(username, current_password, new_password)
        if not ok:
            status_code = 401 if "incorrect" in (err or "").lower() else 400
            return JSONResponse(
                {"success": False, "error": err or "Failed to change password", "error_code": "PASSWORD_CHANGE_FAILED"},
                status_code=status_code,
            )

        logger.info(f"✓ Password changed: {username} (local)")
        return JSONResponse({"success": True})

    except json.JSONDecodeError:
        return JSONResponse(
            {"success": False, "error": "Invalid JSON", "error_code": "VALIDATION_ERROR"},
            status_code=422,
        )
    except Exception as e:
        logger.error(f"Change password error: {e}", exc_info=True)
        return JSONResponse(
            {"success": False, "error": "Internal server error", "error_code": "INTERNAL_SERVER_ERROR"},
            status_code=500,
        )


@app.get(
    "/api/water",
    tags=["Hydration"],
    summary="Get water intake",
    description="Get user's water intake for a specific date",
)
async def get_water_intake(request: Request, date: Optional[str] = None):
    """Get water intake for date (defaults to today)."""
    try:
        payload = _decode_token(request)
        if not payload:
            return JSONResponse(
                {"success": False, "error": "Not authenticated", "error_code": "AUTH_FAILED"},
                status_code=401,
            )

        username = payload["username"]
        user_id = payload.get("user_id")
        day = date or datetime.utcnow().strftime("%Y-%m-%d")

        if USE_SUPABASE and user_id:
            try:
                res = _sb.table("water_logs").select("glasses,date").eq("user_id", user_id).eq("date", day).execute()
                glasses = 0
                if res.data:
                    entry = _cast(dict, res.data[0])
                    glasses = int(entry.get("glasses") or 0)
                return JSONResponse({"success": True, "date": day, "glasses": glasses})
            except Exception as e:
                logger.warning(f"Supabase water fetch failed: {e}, falling back to local")

        try:
            with open(_water_path(username), "r") as f:
                water_map = json.load(f)
        except FileNotFoundError:
            water_map = {}

        glasses = int(water_map.get(day, 0) or 0)
        return JSONResponse({"success": True, "date": day, "glasses": glasses})

    except Exception as e:
        logger.error(f"Get water intake error: {e}", exc_info=True)
        return JSONResponse(
            {"success": False, "error": "Internal server error", "error_code": "INTERNAL_SERVER_ERROR"},
            status_code=500,
        )


@app.post(
    "/api/water",
    tags=["Hydration"],
    summary="Save water intake",
    description="Save user's water intake for a specific date",
)
async def save_water_intake(request: Request):
    """Save water intake for date."""
    try:
        payload = _decode_token(request)
        if not payload:
            return JSONResponse(
                {"success": False, "error": "Not authenticated", "error_code": "AUTH_FAILED"},
                status_code=401,
            )

        username = payload["username"]
        user_id = payload.get("user_id")
        body = await request.json()

        day = str(body.get("date") or datetime.utcnow().strftime("%Y-%m-%d"))
        glasses = int(body.get("glasses", 0))
        glasses = max(0, min(glasses, 30))

        if USE_SUPABASE and user_id:
            try:
                existing = _sb.table("water_logs").select("id").eq("user_id", user_id).eq("date", day).execute()
                if existing.data:
                    _sb.table("water_logs").update({"glasses": glasses}).eq("user_id", user_id).eq("date", day).execute()
                else:
                    _sb.table("water_logs").insert({"user_id": user_id, "date": day, "glasses": glasses}).execute()
                return JSONResponse({"success": True, "date": day, "glasses": glasses})
            except Exception as e:
                logger.warning(f"Supabase water save failed: {e}, falling back to local")

        try:
            with open(_water_path(username), "r") as f:
                water_map = json.load(f)
        except FileNotFoundError:
            water_map = {}

        water_map[day] = glasses
        with open(_water_path(username), "w") as f:
            json.dump(water_map, f, indent=2)

        return JSONResponse({"success": True, "date": day, "glasses": glasses})

    except json.JSONDecodeError:
        return JSONResponse(
            {"success": False, "error": "Invalid JSON", "error_code": "VALIDATION_ERROR"},
            status_code=422,
        )
    except Exception as e:
        logger.error(f"Save water intake error: {e}", exc_info=True)
        return JSONResponse(
            {"success": False, "error": "Internal server error", "error_code": "INTERNAL_SERVER_ERROR"},
            status_code=500,
        )


@app.get(
    "/api/workouts",
    tags=["Workouts"],
    summary="Get workouts",
    description="Get user's workout logs (optionally by date range)",
)
async def get_workouts(request: Request, start_date: Optional[str] = None, end_date: Optional[str] = None):
    """Get workout logs."""
    try:
        payload = _decode_token(request)
        if not payload:
            return JSONResponse(
                {"success": False, "error": "Not authenticated", "error_code": "AUTH_FAILED"},
                status_code=401,
            )

        username = payload["username"]
        user_id = payload.get("user_id")

        if USE_SUPABASE and user_id:
            try:
                query = _sb.table("workouts").select("*").eq("user_id", user_id)
                if start_date:
                    query = query.gte("date", start_date)
                if end_date:
                    query = query.lte("date", end_date)
                res = query.execute()
                workouts_raw = res.data or []
                workouts: list[dict] = [item for item in workouts_raw if isinstance(item, dict)]
                workouts.sort(key=lambda item: str(item.get("timestamp", "")), reverse=True)
                return JSONResponse({"success": True, "workouts": workouts})
            except Exception as e:
                logger.warning(f"Supabase workouts fetch failed: {e}, falling back to local")

        try:
            with open(_workouts_path(username), "r") as f:
                workouts = json.load(f)
        except FileNotFoundError:
            workouts = []

        workouts = [w for w in workouts if isinstance(w, dict)]

        if start_date:
            workouts = [w for w in workouts if str(w.get("date", "")) >= start_date]
        if end_date:
            workouts = [w for w in workouts if str(w.get("date", "")) <= end_date]

        workouts.sort(key=lambda item: str(item.get("timestamp", "")), reverse=True)
        return JSONResponse({"success": True, "workouts": workouts})

    except Exception as e:
        logger.error(f"Get workouts error: {e}", exc_info=True)
        return JSONResponse(
            {"success": False, "error": "Internal server error", "error_code": "INTERNAL_SERVER_ERROR"},
            status_code=500,
        )


@app.post(
    "/api/workouts",
    tags=["Workouts"],
    summary="Log workout",
    description="Create a new workout log entry",
)
async def log_workout(request: Request):
    """Log workout entry."""
    try:
        payload = _decode_token(request)
        if not payload:
            return JSONResponse(
                {"success": False, "error": "Not authenticated", "error_code": "AUTH_FAILED"},
                status_code=401,
            )

        username = payload["username"]
        user_id = payload.get("user_id")
        body = await request.json()

        workout_type = str(body.get("type", "")).strip()
        duration = int(body.get("duration", 0) or 0)
        if not workout_type or duration <= 0:
            return JSONResponse(
                {"success": False, "error": "Workout type and positive duration are required", "error_code": "VALIDATION_ERROR"},
                status_code=422,
            )

        workout = {
            "id": str(body.get("id") or uuid4()),
            "type": workout_type,
            "duration": duration,
            "notes": str(body.get("notes", "")).strip(),
            "date": str(body.get("date") or datetime.utcnow().strftime("%Y-%m-%d")),
            "timestamp": str(body.get("timestamp") or datetime.utcnow().isoformat()),
        }

        if USE_SUPABASE and user_id:
            try:
                _sb.table("workouts").insert({**workout, "user_id": user_id}).execute()
                return JSONResponse({"success": True, "workout": workout})
            except Exception as e:
                logger.warning(f"Supabase workout save failed: {e}, falling back to local")

        try:
            with open(_workouts_path(username), "r") as f:
                workouts = json.load(f)
        except FileNotFoundError:
            workouts = []

        workouts.append(workout)
        with open(_workouts_path(username), "w") as f:
            json.dump(workouts, f, indent=2)

        return JSONResponse({"success": True, "workout": workout})

    except json.JSONDecodeError:
        return JSONResponse(
            {"success": False, "error": "Invalid JSON", "error_code": "VALIDATION_ERROR"},
            status_code=422,
        )
    except Exception as e:
        logger.error(f"Log workout error: {e}", exc_info=True)
        return JSONResponse(
            {"success": False, "error": "Internal server error", "error_code": "INTERNAL_SERVER_ERROR"},
            status_code=500,
        )


@app.delete(
    "/api/workouts/{workout_id}",
    tags=["Workouts"],
    summary="Delete workout",
    description="Delete a workout log entry by id",
)
async def delete_workout(request: Request, workout_id: str):
    """Delete workout entry."""
    try:
        payload = _decode_token(request)
        if not payload:
            return JSONResponse(
                {"success": False, "error": "Not authenticated", "error_code": "AUTH_FAILED"},
                status_code=401,
            )

        username = payload["username"]
        user_id = payload.get("user_id")

        if USE_SUPABASE and user_id:
            try:
                _sb.table("workouts").delete().eq("user_id", user_id).eq("id", workout_id).execute()
                return JSONResponse({"success": True})
            except Exception as e:
                logger.warning(f"Supabase workout delete failed: {e}, falling back to local")

        try:
            with open(_workouts_path(username), "r") as f:
                workouts = json.load(f)
        except FileNotFoundError:
            return JSONResponse(
                {"success": False, "error": "Workout not found", "error_code": "NOT_FOUND"},
                status_code=404,
            )

        filtered = [w for w in workouts if str(w.get("id")) != workout_id]
        if len(filtered) == len(workouts):
            return JSONResponse(
                {"success": False, "error": "Workout not found", "error_code": "NOT_FOUND"},
                status_code=404,
            )

        with open(_workouts_path(username), "w") as f:
            json.dump(filtered, f, indent=2)

        return JSONResponse({"success": True})

    except Exception as e:
        logger.error(f"Delete workout error: {e}", exc_info=True)
        return JSONResponse(
            {"success": False, "error": "Internal server error", "error_code": "INTERNAL_SERVER_ERROR"},
            status_code=500,
        )

# ══════════════════════════════════════════════
# PROFILE ENDPOINTS
# ══════════════════════════════════════════════

@app.get(
    "/api/me",
    tags=["Profile"],
    summary="Get current user profile",
    description="Get authenticated user's profile data",
)
async def me(request: Request):
    """Get authenticated user profile."""
    try:
        payload = _decode_token(request)
        if not payload:
            return JSONResponse(
                {"success": False, "error": "Not authenticated", "error_code": "AUTH_FAILED"},
                status_code=401,
            )
        
        username = payload["username"]
        user_id = payload.get("user_id")
        profile = {}
        
        # Try Supabase first
        if USE_SUPABASE and user_id:
            try:
                res = _sb.table("profiles").select("*").eq("user_id", user_id).execute()
                if res.data:
                    profile = res.data[0]
                    logger.debug(f"Profile loaded from Supabase: {username}")
            except Exception as e:
                logger.warning(f"Supabase profile load failed: {e}")
        
        # Fallback to local
        if not profile:
            try:
                with open(_profile_path(username), "r") as f:
                    profile = json.load(f)
                    logger.debug(f"Profile loaded from local: {username}")
            except FileNotFoundError:
                logger.debug(f"No profile found for: {username}")
        
        return JSONResponse({
            "success": True,
            "username": username,
            "user_id": user_id,
            "profile": profile,
        })
    
    except Exception as e:
        logger.error(f"Profile endpoint error: {e}", exc_info=True)
        return JSONResponse(
            {
                "success": False,
                "error": "Internal server error",
                "error_code": "INTERNAL_SERVER_ERROR",
            },
            status_code=500,
        )

@app.post(
    "/api/profile",
    tags=["Profile"],
    summary="Update user profile",
    description="Update authenticated user's profile data",
)
async def save_profile(request: Request):
    """Save/update user profile."""
    try:
        payload = _decode_token(request)
        if not payload:
            return JSONResponse(
                {"success": False, "error": "Not authenticated", "error_code": "AUTH_FAILED"},
                status_code=401,
            )
        
        username = payload["username"]
        user_id = payload.get("user_id")
        data = await request.json()
        
        # Validate profile data (basic checks) - handle both string and numeric values
        if isinstance(data, dict):
            # Convert age to int if it's a string and validate
            if "age" in data:
                try:
                    age_val = int(data["age"]) if isinstance(data["age"], str) else data["age"]
                    if not (13 <= age_val <= 120):
                        return JSONResponse(
                            {"success": False, "error": "Age must be between 13 and 120", "error_code": "VALIDATION_ERROR"},
                            status_code=422,
                        )
                except (ValueError, TypeError):
                    pass  # Allow non-numeric age strings like "20s"
            
            # Convert weight_kg to float if it's a string and validate
            if "weight_kg" in data:
                try:
                    weight_val = float(data["weight_kg"]) if isinstance(data["weight_kg"], str) else data["weight_kg"]
                    if not (30 < weight_val < 200):
                        return JSONResponse(
                            {"success": False, "error": "Weight must be between 30 and 200 kg", "error_code": "VALIDATION_ERROR"},
                            status_code=422,
                        )
                except (ValueError, TypeError):
                    pass  # Allow non-numeric weight strings like "150 lbs"
        
        # Try Supabase first
        if USE_SUPABASE and user_id:
            try:
                existing = _sb.table("profiles").select("id").eq("user_id", user_id).execute()
                if existing.data:
                    _sb.table("profiles").update(data).eq("user_id", user_id).execute()
                    logger.info(f"✓ Profile updated: {username} (Supabase)")
                else:
                    _sb.table("profiles").insert({**data, "user_id": user_id}).execute()
                    logger.info(f"✓ Profile created: {username} (Supabase)")
                return JSONResponse({"success": True})
            except Exception as e:
                logger.warning(f"Supabase profile save failed: {e}, falling back to local")
        
        # Fallback to local
        with open(_profile_path(username), "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"✓ Profile saved: {username} (local)")
        return JSONResponse({"success": True})
    
    except json.JSONDecodeError:
        return JSONResponse(
            {"success": False, "error": "Invalid JSON", "error_code": "VALIDATION_ERROR"},
            status_code=422,
        )
    except Exception as e:
        logger.error(f"Profile save error: {e}", exc_info=True)
        return JSONResponse(
            {
                "success": False,
                "error": "Internal server error",
                "error_code": "INTERNAL_SERVER_ERROR",
            },
            status_code=500,
        )

# ══════════════════════════════════════════════
# CHURN PREDICTION ENDPOINTS
# ══════════════════════════════════════════════

@app.post(
    "/api/churn-risk",
    tags=["Churn Prediction"],
    summary="Predict user churn risk",
    description="Predict likelihood of user churn based on engagement metrics",
)
async def predict_churn(request: Request):
    """Predict churn risk for a user.
    
    Expected JSON payload:
    {
        "user_id": "user_123",
        "last_login": "2024-02-15T10:30:00",
        "login_history": [...],
        "total_goals": 5,
        "completed_goals": 3,
        "total_meals": 30,
        "adhered_meals": 24,
        "feedback_count": 8,
        "days_since_signup": 90,
        "activity_days": 60,
        "profile_completion_percent": 85,
        "health_check_count": 15
    }
    """
    try:
        payload = _decode_token(request)
        if not payload:
            return JSONResponse(
                {"success": False, "error": "Not authenticated", "error_code": "AUTH_FAILED"},
                status_code=401,
            )
        
        # Get request body
        body = await request.json()
        
        if not churn_predictor:
            return JSONResponse(
                {"success": False, "error": "Churn prediction model not available", "error_code": "SERVICE_UNAVAILABLE"},
                status_code=503,
            )
        
        # Predict churn
        result = churn_predictor.predict(body)
        
        return JSONResponse({
            "success": True,
            "data": result.to_dict()
        }, status_code=200)
    
    except json.JSONDecodeError:
        return JSONResponse(
            {"success": False, "error": "Invalid JSON", "error_code": "VALIDATION_ERROR"},
            status_code=422,
        )
    except Exception as e:
        logger.error(f"Churn prediction error: {e}", exc_info=True)
        return JSONResponse(
            {"success": False, "error": "Internal server error", "error_code": "INTERNAL_SERVER_ERROR"},
            status_code=500,
        )


@app.get(
    "/api/churn-risk/cohort",
    tags=["Churn Prediction"],
    summary="Get at-risk user cohort",
    description="Get list of users at risk of churn above threshold",
)
async def get_at_risk_cohort(request: Request, threshold: float = 0.5):
    """Get cohort of users at risk of churn.
    
    Parameters:
    - threshold: Churn probability threshold (0.0-1.0), default 0.5
    
    In production, this would query Supabase:
    SELECT * FROM churn_features WHERE churn_risk_score >= threshold
    ORDER BY churn_risk_score DESC
    """
    try:
        payload = _decode_token(request)
        if not payload:
            return JSONResponse(
                {"success": False, "error": "Not authenticated", "error_code": "AUTH_FAILED"},
                status_code=401,
            )
        
        if threshold < 0 or threshold > 1:
            return JSONResponse(
                {"success": False, "error": "Threshold must be between 0 and 1", "error_code": "VALIDATION_ERROR"},
                status_code=422,
            )
        
        # In production:
        # result = _sb.table("churn_features") \
        #     .select("*") \
        #     .gte("churn_risk_score", threshold) \
        #     .order("churn_risk_score", desc=True) \
        #     .execute()
        # return JSONResponse({"success": True, "data": result.data})
        
        return JSONResponse({
            "success": True,
            "data": [],
            "threshold": threshold,
            "count": 0
        }, status_code=200)
    
    except Exception as e:
        logger.error(f"Get at-risk cohort error: {e}", exc_info=True)
        return JSONResponse(
            {"success": False, "error": "Internal server error", "error_code": "INTERNAL_SERVER_ERROR"},
            status_code=500,
        )


@app.get(
    "/api/churn-risk/{user_id}",
    tags=["Churn Prediction"],
    summary="Get user churn risk",
    description="Get stored churn risk for a specific user",
)
async def get_user_churn_risk(user_id: str, request: Request):
    """Get churn risk for specific user from database.
    
    In a production system, this would fetch pre-calculated churn scores
    from the churn_features table in Supabase.
    """
    try:
        payload = _decode_token(request)
        if not payload:
            return JSONResponse(
                {"success": False, "error": "Not authenticated", "error_code": "AUTH_FAILED"},
                status_code=401,
            )
        
        # In production, query Supabase:
        # result = _sb.table("churn_features").select("*").eq("user_id", user_id).execute()
        # if result.data:
        #     return JSONResponse({"success": True, "data": result.data[0]})
        
        return JSONResponse(
            {"success": False, "error": "User not found", "error_code": "NOT_FOUND"},
            status_code=404,
        )
    except Exception as e:
        logger.error(f"Get churn risk error: {e}", exc_info=True)
        return JSONResponse(
            {"success": False, "error": "Internal server error", "error_code": "INTERNAL_SERVER_ERROR"},
            status_code=500,
        )

# ══════════════════════════════════════════════
# CHAT ENDPOINT
# ══════════════════════════════════════════════

@app.post(
    "/api/chat",
    tags=["Chat"],
    summary="Stream health advice",
    description="Send message and stream AI health advice with protocol recommendations",
)
async def chat(request: Request):
    """Stream chat response with health advice."""
    try:
        payload = _decode_token(request)
        if not payload:
            return JSONResponse(
                {"success": False, "error": "Not authenticated", "error_code": "AUTH_FAILED"},
                status_code=401,
            )
        
        # Rate limiting
        try:
            rate_limiter = get_rate_limiter()
            rate_limiter.check_rate_limit(request, "/api/chat", username=payload["username"])
        except:
            pass  # Graceful fallback
        
        username = payload["username"]
        user_id = payload.get("user_id")
        
        body = await request.json()
        message = (body.get("message") or "").strip()
        if not message or len(message) > 2000:
            return JSONResponse(
                {"success": False, "error": "Message must be 1-2000 characters", "error_code": "VALIDATION_ERROR"},
                status_code=422,
            )
        
        # Load profile
        profile = {}
        if USE_SUPABASE and user_id:
            try:
                res = _sb.table("profiles").select("*").eq("user_id", user_id).execute()
                if res.data:
                    profile = res.data[0]
            except Exception as e:
                logger.warning(f"Profile load error: {e}")
        
        if not profile:
            try:
                with open(_profile_path(username), "r") as f:
                    profile = json.load(f)
            except FileNotFoundError:
                pass
        
        def generate():
            """Generate chat response stream using Gemini."""
            try:
                if not GEMINI_API_KEY:
                    yield "⚠️ **AI Service Unavailable** — Gemini API key not configured."
                    return
                
                import google.generativeai as genai
                from model.model import build_full_context
                from model.constraint_graph import ConstraintGraph
                from model.validation import parse_profile as _parse_profile
                from model.meal_swap import detect_swap_request, find_swaps, format_swap_block
                from model import nutrition_db, user_state
                
                _profile = _cast(dict, profile) if profile else {}
                system_full, seed_message = build_full_context(_profile, username)
                
                # Meal swap injection
                _swap_prefix = ""
                _rejected = detect_swap_request(message)
                if _rejected and nutrition_db.is_loaded():
                    try:
                        _pp = _parse_profile(_profile)
                        _cg = ConstraintGraph.from_parsed_profile(_pp)
                        _state = user_state.analyze_user_state(_profile)
                        _protocols = user_state.map_state_to_protocols(_state)
                        _prioritized = user_state.prioritize_protocols(_protocols, _state, {})
                        _active_p = [p for p, _ in _prioritized[:5]]
                        _swaps = find_swaps(_rejected, constraint_graph=_cg, active_protocols=_active_p, n=5)
                        _swap_prefix = format_swap_block(_rejected, _swaps, constraint_graph=_cg)
                    except Exception as e:
                        logger.warning(f"Meal swap failed: {e}")
                
                _final_message = f"{_swap_prefix}\n\n{message}" if _swap_prefix else message
                
                # Extract feedback from message
                try:
                    feedback = user_state.parse_feedback_from_text(message)
                    if feedback:
                        user_state.update_weights_from_feedback(username, feedback, learning_rate=0.05)
                        logger.info(f"✓ Feedback recorded for {username}: {feedback}")
                except Exception as e:
                    logger.warning(f"Feedback processing failed: {e}")
                
                # Build Gemini model with system instruction
                genai.configure(api_key=GEMINI_API_KEY)
                gemini_model = genai.GenerativeModel(
                    "gemini-1.5-flash",
                    system_instruction=system_full,
                )
                
                # Seed the conversation history then send the real message
                chat_session = gemini_model.start_chat(history=[
                    {"role": "user", "parts": [seed_message]},
                    {"role": "model", "parts": ["Understood. I have your full profile, state analysis, protocol priorities, and nutrition data loaded."]},
                ])
                
                response = chat_session.send_message(_final_message, stream=True)
                for chunk in response:
                    if chunk.text:
                        yield chunk.text
                
                logger.info(f"✓ Gemini chat completed: {username}")
            
            except ImportError as e:
                logger.error(f"Import error in chat: {e}")
                yield f"[Error: Missing dependency: {e}]"
            except Exception as e:
                logger.error(f"Chat error: {e}", exc_info=True)
                yield f"[Error: {str(e)[:100]}]"
        
        return StreamingResponse(generate(), media_type="text/plain")
    
    except json.JSONDecodeError:
        return JSONResponse(
            {"success": False, "error": "Invalid JSON", "error_code": "VALIDATION_ERROR"},
            status_code=422,
        )
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}", exc_info=True)
        return JSONResponse(
            {
                "success": False,
                "error": "Internal server error",
                "error_code": "INTERNAL_SERVER_ERROR",
            },
            status_code=500,
        )

# ══════════════════════════════════════════════
# NUTRITION ENDPOINTS
# ══════════════════════════════════════════════

@app.get(
    "/api/nutrition/search",
    tags=["Nutrition"],
    summary="Search nutrition database",
    description="Search for foods in the nutrition database",
)
async def search_nutrition(request: Request, q: str):
    """Search nutrition database by food name."""
    try:
        payload = _decode_token(request)
        if not payload:
            return JSONResponse(
                {"success": False, "error": "Not authenticated", "error_code": "AUTH_FAILED"},
                status_code=401,
            )
        
        if not q or len(q) < 2:
            return JSONResponse(
                {"success": False, "error": "Query must be at least 2 characters", "error_code": "VALIDATION_ERROR"},
                status_code=422,
            )
        
        try:
            from model import nutrition_db
            
            if not nutrition_db.is_loaded():
                return JSONResponse(
                    {"success": False, "error": "Nutrition database not loaded", "error_code": "SERVICE_UNAVAILABLE"},
                    status_code=503,
                )
            
            # Search using fuzzy search
            results = nutrition_db.fuzzy_search(q, top_n=10)
            
            return JSONResponse({
                "success": True,
                "results": results,
                "count": len(results)
            })
        
        except Exception as e:
            logger.error(f"Nutrition search error: {e}", exc_info=True)
            return JSONResponse(
                {"success": False, "error": "Search failed", "error_code": "SEARCH_ERROR"},
                status_code=500,
            )
    
    except Exception as e:
        logger.error(f"Nutrition endpoint error: {e}", exc_info=True)
        return JSONResponse(
            {"success": False, "error": "Internal server error", "error_code": "INTERNAL_SERVER_ERROR"},
            status_code=500,
        )

@app.get(
    "/api/nutrition/food/{food_name}",
    tags=["Nutrition"],
    summary="Get food details",
    description="Get detailed nutrition information for a specific food",
)
async def get_food_details(food_name: str, request: Request):
    """Get detailed nutrition info for a specific food."""
    try:
        payload = _decode_token(request)
        if not payload:
            return JSONResponse(
                {"success": False, "error": "Not authenticated", "error_code": "AUTH_FAILED"},
                status_code=401,
            )
        
        try:
            from model import nutrition_db
            
            if not nutrition_db.is_loaded():
                return JSONResponse(
                    {"success": False, "error": "Nutrition database not loaded", "error_code": "SERVICE_UNAVAILABLE"},
                    status_code=503,
                )
            
            # Get food by name using lookup
            food = nutrition_db.lookup(food_name)
            
            if not food:
                return JSONResponse(
                    {"success": False, "error": "Food not found", "error_code": "NOT_FOUND"},
                    status_code=404,
                )
            
            return JSONResponse({
                "success": True,
                "food": food
            })
        
        except Exception as e:
            logger.error(f"Food details error: {e}", exc_info=True)
            return JSONResponse(
                {"success": False, "error": "Failed to get food details", "error_code": "FETCH_ERROR"},
                status_code=500,
            )
    
    except Exception as e:
        logger.error(f"Food details endpoint error: {e}", exc_info=True)
        return JSONResponse(
            {"success": False, "error": "Internal server error", "error_code": "INTERNAL_SERVER_ERROR"},
            status_code=500,
        )

# ══════════════════════════════════════════════
# MEALS LOGGING ENDPOINTS
# ══════════════════════════════════════════════

@app.post(
    "/api/meals",
    tags=["Meals"],
    summary="Log a meal",
    description="Log a new meal with food items and nutritional information",
)
async def log_meal(request: Request):
    """Log a new meal."""
    try:
        payload = _decode_token(request)
        if not payload:
            return JSONResponse(
                {"success": False, "error": "Not authenticated", "error_code": "AUTH_FAILED"},
                status_code=401,
            )
        
        username = payload["username"]
        user_id = payload.get("user_id")
        
        data = await request.json()
        
        # Validate data
        if not data.get("type") or not data.get("items"):
            return JSONResponse(
                {"success": False, "error": "Missing required fields: type, items", "error_code": "VALIDATION_ERROR"},
                status_code=422,
            )
        
        # Add timestamp if not provided
        if "timestamp" not in data:
            data["timestamp"] = datetime.utcnow().isoformat()
        if "id" not in data or not data.get("id"):
            data["id"] = str(uuid4())
        
        # Store in Supabase or local file
        if USE_SUPABASE and user_id:
            try:
                _sb.table("meals").insert({
                    **data,
                    "user_id": user_id,
                }).execute()
                logger.info(f"✓ Meal logged: {username} (Supabase)")
                return JSONResponse({"success": True})
            except Exception as e:
                logger.warning(f"Supabase meal log failed: {e}, falling back to local")
        
        # Fallback to local storage
        meals_path = _profile_path(username).replace(".json", "_meals.json")
        try:
            with open(meals_path, "r") as f:
                meals = json.load(f)
        except FileNotFoundError:
            meals = []
        
        meals.append(data)
        
        with open(meals_path, "w") as f:
            json.dump(meals, f, indent=2)
        
        logger.info(f"✓ Meal logged: {username} (local)")
        return JSONResponse({"success": True})
    
    except json.JSONDecodeError:
        return JSONResponse(
            {"success": False, "error": "Invalid JSON", "error_code": "VALIDATION_ERROR"},
            status_code=422,
        )
    except Exception as e:
        logger.error(f"Meal logging error: {e}", exc_info=True)
        return JSONResponse(
            {"success": False, "error": "Internal server error", "error_code": "INTERNAL_SERVER_ERROR"},
            status_code=500,
        )

@app.get(
    "/api/meals",
    tags=["Meals"],
    summary="Get user meals",
    description="Get all meals logged by the authenticated user",
)
async def get_meals(request: Request, date: Optional[str] = None):
    """Get user's logged meals."""
    try:
        payload = _decode_token(request)
        if not payload:
            return JSONResponse(
                {"success": False, "error": "Not authenticated", "error_code": "AUTH_FAILED"},
                status_code=401,
            )
        
        username = payload["username"]
        user_id = payload.get("user_id")
        
        # Try Supabase first
        if USE_SUPABASE and user_id:
            try:
                query = _sb.table("meals").select("*").eq("user_id", user_id)
                if date:
                    query = query.eq("date", date)
                res = query.execute()
                return JSONResponse({
                    "success": True,
                    "meals": res.data or []
                })
            except Exception as e:
                logger.warning(f"Supabase meals fetch failed: {e}")
        
        # Fallback to local
        meals_path = _profile_path(username).replace(".json", "_meals.json")
        try:
            with open(meals_path, "r") as f:
                meals = json.load(f)
            
            # Filter by date if provided
            if date:
                meals = [m for m in meals if m.get("date") == date]
            
            return JSONResponse({
                "success": True,
                "meals": meals
            })
        except FileNotFoundError:
            return JSONResponse({
                "success": True,
                "meals": []
            })
    
    except Exception as e:
        logger.error(f"Get meals error: {e}", exc_info=True)
        return JSONResponse(
            {"success": False, "error": "Internal server error", "error_code": "INTERNAL_SERVER_ERROR"},
            status_code=500,
        )


@app.put(
    "/api/meals/{meal_id}",
    tags=["Meals"],
    summary="Update a meal",
    description="Update a logged meal by id",
)
async def update_meal(request: Request, meal_id: str):
    """Update an existing meal by id."""
    try:
        payload = _decode_token(request)
        if not payload:
            return JSONResponse(
                {"success": False, "error": "Not authenticated", "error_code": "AUTH_FAILED"},
                status_code=401,
            )

        username = payload["username"]
        user_id = payload.get("user_id")
        data = await request.json()

        if not data.get("type") or not data.get("items"):
            return JSONResponse(
                {"success": False, "error": "Missing required fields: type, items", "error_code": "VALIDATION_ERROR"},
                status_code=422,
            )

        data["id"] = meal_id

        if USE_SUPABASE and user_id:
            try:
                _sb.table("meals").update(data).eq("user_id", user_id).eq("id", meal_id).execute()
                logger.info(f"✓ Meal updated: {username} ({meal_id}) (Supabase)")
                return JSONResponse({"success": True})
            except Exception as e:
                logger.warning(f"Supabase meal update failed: {e}, falling back to local")

        meals_path = _profile_path(username).replace(".json", "_meals.json")
        try:
            with open(meals_path, "r") as f:
                meals = json.load(f)
        except FileNotFoundError:
            meals = []

        updated = False
        for idx, meal in enumerate(meals):
            if str(meal.get("id", "")) == meal_id or str(meal.get("timestamp", "")) == meal_id:
                meals[idx] = {
                    **meal,
                    **data,
                    "id": meal_id,
                    "timestamp": data.get("timestamp") or meal.get("timestamp") or datetime.utcnow().isoformat(),
                }
                updated = True
                break

        if not updated:
            return JSONResponse(
                {"success": False, "error": "Meal not found", "error_code": "NOT_FOUND"},
                status_code=404,
            )

        with open(meals_path, "w") as f:
            json.dump(meals, f, indent=2)

        logger.info(f"✓ Meal updated: {username} ({meal_id}) (local)")
        return JSONResponse({"success": True})

    except json.JSONDecodeError:
        return JSONResponse(
            {"success": False, "error": "Invalid JSON", "error_code": "VALIDATION_ERROR"},
            status_code=422,
        )
    except Exception as e:
        logger.error(f"Update meal error: {e}", exc_info=True)
        return JSONResponse(
            {"success": False, "error": "Internal server error", "error_code": "INTERNAL_SERVER_ERROR"},
            status_code=500,
        )


@app.delete(
    "/api/meals/{meal_id}",
    tags=["Meals"],
    summary="Delete a meal",
    description="Delete a logged meal by id",
)
async def delete_meal(request: Request, meal_id: str):
    """Delete an existing meal by id."""
    try:
        payload = _decode_token(request)
        if not payload:
            return JSONResponse(
                {"success": False, "error": "Not authenticated", "error_code": "AUTH_FAILED"},
                status_code=401,
            )

        username = payload["username"]
        user_id = payload.get("user_id")

        if USE_SUPABASE and user_id:
            try:
                _sb.table("meals").delete().eq("user_id", user_id).eq("id", meal_id).execute()
                logger.info(f"✓ Meal deleted: {username} ({meal_id}) (Supabase)")
                return JSONResponse({"success": True})
            except Exception as e:
                logger.warning(f"Supabase meal delete failed: {e}, falling back to local")

        meals_path = _profile_path(username).replace(".json", "_meals.json")
        try:
            with open(meals_path, "r") as f:
                meals = json.load(f)
        except FileNotFoundError:
            return JSONResponse(
                {"success": False, "error": "Meal not found", "error_code": "NOT_FOUND"},
                status_code=404,
            )

        filtered = [
            meal for meal in meals
            if str(meal.get("id", "")) != meal_id and str(meal.get("timestamp", "")) != meal_id
        ]

        if len(filtered) == len(meals):
            return JSONResponse(
                {"success": False, "error": "Meal not found", "error_code": "NOT_FOUND"},
                status_code=404,
            )

        with open(meals_path, "w") as f:
            json.dump(filtered, f, indent=2)

        logger.info(f"✓ Meal deleted: {username} ({meal_id}) (local)")
        return JSONResponse({"success": True})

    except Exception as e:
        logger.error(f"Delete meal error: {e}", exc_info=True)
        return JSONResponse(
            {"success": False, "error": "Internal server error", "error_code": "INTERNAL_SERVER_ERROR"},
            status_code=500,
        )

# ══════════════════════════════════════════════
# FOOD / NUTRITION DATABASE
# ══════════════════════════════════════════════

_FOOD_DB: list | None = None
_FOOD_INDEX: dict = {}

_NUTRIENT_MAP = {
    "Energy":                           ("calories",       "kcal"),
    "Protein":                          ("protein_g",      "g"),
    "Total lipid (fat)":                ("fat_g",          "g"),
    "Carbohydrate, by difference":      ("carbs_g",        "g"),
    "Fiber, total dietary":             ("fiber_g",        "g"),
    "Sugars, total including NLEA":     ("sugar_g",        "g"),
    "Sodium, Na":                       ("sodium_mg",      "mg"),
    "Cholesterol":                      ("cholesterol_mg", "mg"),
    "Calcium, Ca":                      ("calcium_mg",     "mg"),
    "Iron, Fe":                         ("iron_mg",        "mg"),
    "Potassium, K":                     ("potassium_mg",   "mg"),
    "Vitamin C, total ascorbic acid":   ("vitamin_c_mg",   "mg"),
    "Vitamin D (D2 + D3)":             ("vitamin_d_mcg",  "µg"),
    "Vitamin A, RAE":                   ("vitamin_a_mcg",  "µg"),
    "Fatty acids, total saturated":     ("sat_fat_g",      "g"),
    "Fatty acids, total trans":         ("trans_fat_g",    "g"),
    "Zinc, Zn":                         ("zinc_mg",        "mg"),
}

def _extract_nutrients(food_nutrients: list) -> dict:
    result = {}
    for n in food_nutrients:
        name = n.get("nutrient", {}).get("name", "")
        if name in _NUTRIENT_MAP:
            field, _ = _NUTRIENT_MAP[name]
            # For Energy prefer kcal over kJ
            if name == "Energy" and n.get("nutrient", {}).get("unitName", "") == "kJ":
                continue
            val = n.get("amount")
            if val is not None and field not in result:
                result[field] = round(float(val), 1)
    return result

def _load_food_db() -> list:
    global _FOOD_DB, _FOOD_INDEX
    if _FOOD_DB is not None:
        return _FOOD_DB
    base = os.path.dirname(os.path.abspath(__file__))
    foods = []
    sources = [
        ("FoodData_Central_foundation_food_json_2025-12-18.json", "FoundationFoods", "Foundation"),
        ("surveyDownload.json", "SurveyFoods", "Survey"),
    ]
    for filename, key, source_label in sources:
        path = os.path.join(base, filename)
        if not os.path.exists(path):
            logger.warning(f"Food DB not found: {path}")
            continue
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            raw = data.get(key, [])
            for item in raw:
                nutrients = _extract_nutrients(item.get("foodNutrients", []))
                cat = (
                    (item.get("foodCategory") or {}).get("description")
                    or (item.get("wweiaFoodCategory") or {}).get("wweiaFoodCategoryDescription")
                    or ""
                )
                portions = item.get("foodPortions", [])
                serving = None
                if portions:
                    p = portions[0]
                    gw = p.get("gramWeight")
                    unit = (p.get("measureUnit") or {}).get("abbreviation") or p.get("modifier", "")
                    amt = p.get("amount", 1)
                    if gw:
                        serving = {"amount": amt, "unit": unit or "serving", "grams": gw}
                food = {
                    "fdc_id": str(item.get("fdcId", "")),
                    "name": item.get("description", ""),
                    "category": cat,
                    "source": source_label,
                    "serving": serving,
                    "_key": item.get("description", "").lower(),
                    **nutrients,
                }
                foods.append(food)
                _FOOD_INDEX[food["fdc_id"]] = food
            logger.info(f"Loaded {len(raw)} {source_label} foods")
        except Exception as exc:
            logger.error(f"Error loading {filename}: {exc}")
    _FOOD_DB = foods
    logger.info(f"Food DB ready: {len(_FOOD_DB)} total items")
    return _FOOD_DB


@app.get("/api/nutrition/search")
async def nutrition_search(request: Request, q: str = "", limit: int = 20):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        return JSONResponse({"success": False, "error": "Unauthorized"}, status_code=401)
    try:
        _jwt.decode(token, SECRET, algorithms=["HS256"])
    except Exception:
        return JSONResponse({"success": False, "error": "Invalid token"}, status_code=401)
    q = q.strip()
    if not q:
        return JSONResponse({"success": False, "error": "Query required"}, status_code=400)
    db = _load_food_db()
    query = q.lower()
    scored = []
    for food in db:
        sk = food["_key"]
        if query in sk:
            if sk == query:
                score = 3
            elif sk.startswith(query):
                score = 2
            else:
                score = 1
            scored.append((score, food))
    scored.sort(key=lambda x: (-x[0], x[1]["name"]))
    limit = min(limit, 50)
    out = [{k: v for k, v in f.items() if k != "_key"} for _, f in scored[:limit]]
    return JSONResponse({"success": True, "results": out, "total": len(scored), "query": q})


@app.get("/api/nutrition/food/{fdc_id}")
async def nutrition_food_detail(fdc_id: str, request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        return JSONResponse({"success": False, "error": "Unauthorized"}, status_code=401)
    try:
        _jwt.decode(token, SECRET, algorithms=["HS256"])
    except Exception:
        return JSONResponse({"success": False, "error": "Invalid token"}, status_code=401)
    _load_food_db()
    food = _FOOD_INDEX.get(str(fdc_id))
    if not food:
        return JSONResponse({"success": False, "error": "Food not found"}, status_code=404)
    out = {k: v for k, v in food.items() if k != "_key"}
    return JSONResponse({"success": True, "food": out})


# ══════════════════════════════════════════════
# APP STARTUP/SHUTDOWN
# ══════════════════════════════════════════════

@app.on_event("startup")
async def startup_event():
    """Initialize on app startup."""
    logger.info("="*60)
    logger.info("  HealthOS API v3.0 — Starting")
    logger.info("="*60)
    logger.info(f"  Ollama: Available")
    logger.info(f"  Supabase: {'Connected' if USE_SUPABASE else 'Unavailable (using local fallback)'}")
    logger.info(f"  Docs: http://localhost:8000/api/docs")
    logger.info("="*60)
    # Pre-load food DB in background so first search is instant
    import threading
    threading.Thread(target=_load_food_db, daemon=True).start()

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on app shutdown."""
    logger.info("HealthOS API shutting down...")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
