from fastapi import FastAPI, Query, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import jwt
import os
import time
import uuid
import yaml

from dotenv import dotenv_values

app = FastAPI()

# CORS (allow all for this assignment)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware
class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.perf_counter()

        response = await call_next(request)

        response.headers["X-Request-ID"] = str(uuid.uuid4())
        response.headers["X-Process-Time"] = str(time.perf_counter() - start)

        return response


app.add_middleware(TimingMiddleware)


# -----------------------------
# Assignment 1
# -----------------------------
@app.get("/stats")
async def stats(values: str = Query(...)):
    numbers = [int(v.strip()) for v in values.split(",")]

    return {
        "email": "23f3004469@ds.study.iitm.ac.in",
        "count": len(numbers),
        "sum": sum(numbers),
        "min": min(numbers),
        "max": max(numbers),
        "mean": sum(numbers) / len(numbers),
    }


# -----------------------------
# Assignment 2
# -----------------------------
PUBLIC_KEY = """
-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA2okOHspNjgA+2rTLbeuY
cxiP/hG8C6Sb9iwg3yiLAA4HCnpITcbWCSelbvbYGuc3EbNy4xFyf5Cbj5DHJMID
EkryOgyd2giIIIBOUBj8S63uGcnRpOBh9NFatfNwheKuzsPuVNldu6A9cNteNpXc
WyJjG2axVfmq7i6SuKr1JoWYG7xTTAvKPujSl4OtsQfO3h5NepzdfXpr28oNnzfW
ed+zclR6BcmNNo/WVfJ4xyCLSf0BCOgdTgW6PdaChd1l9VDetJZVEgC5tkyvXsfI
SI6iyrYbKR0NEBSqq4XkadEjsCs4F1RncsS4LlgniT7GlkL9Mce3b0wGLs9/7ZIX
dQIDAQAB
-----END PUBLIC KEY-----
"""

ISSUER = "https://idp.exam.local"
AUDIENCE = "tds-076621u5.apps.exam.local"


class TokenRequest(BaseModel):
    token: str

class Event(BaseModel):
    user: str
    amount: float
    ts: int


class AnalyticsRequest(BaseModel):
    events: list[Event]

AUDIENCE = "tds-076621u5.apps.exam.local"
API_KEY = "ak_bjhm2nqfl5b8yf7w5357wlsm"

@app.post("/verify")
async def verify(request: TokenRequest):
    try:
        payload = jwt.decode(
            request.token,
            PUBLIC_KEY,
            algorithms=["RS256"],
            issuer=ISSUER,
            audience=AUDIENCE,
        )

        return {
            "valid": True,
            "email": payload["email"],
            "sub": payload["sub"],
            "aud": payload["aud"],
        }

    except Exception:
        return JSONResponse(
            status_code=401,
            content={"valid": False},
        )


# -----------------------------
# Assignment 3
# -----------------------------
DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}


def to_bool(value):
    return str(value).lower() in ("true", "1", "yes", "on")


@app.get("/effective-config")
async def effective_config(set: list[str] = Query(default=[])):

    # defaults
    config = DEFAULTS.copy()

    # YAML
    with open("config.development.yaml", "r") as f:
        yaml_config = yaml.safe_load(f)

    if yaml_config:
        config.update(yaml_config)

    # .env
    env_file = dotenv_values(".env")

    mapping = {
        "APP_PORT": "port",
        "APP_DEBUG": "debug",
        "APP_LOG_LEVEL": "log_level",
        "APP_API_KEY": "api_key",
        "NUM_WORKERS": "workers",
    }

    for env_key, cfg_key in mapping.items():
        if env_key in env_file and env_file[env_key] is not None:
            config[cfg_key] = env_file[env_key]

    # OS environment
    mapping = {
        "APP_PORT": "port",
        "APP_WORKERS": "workers",
        "APP_DEBUG": "debug",
        "APP_LOG_LEVEL": "log_level",
        "APP_API_KEY": "api_key",
    }

    for env_key, cfg_key in mapping.items():
        value = os.environ.get(env_key)
        if value is not None:
            config[cfg_key] = value

    # CLI overrides
    for item in set:
        if "=" not in item:
            continue

        key, value = item.split("=", 1)
        config[key] = value

    # Type coercion
    config["port"] = int(config["port"])
    config["workers"] = int(config["workers"])
    config["debug"] = to_bool(config["debug"])
    config["log_level"] = str(config["log_level"])

    # Secret masking
    config["api_key"] = "****"

    return config
@app.post("/analytics")
async def analytics(
    request: AnalyticsRequest,
    x_api_key: str = Header(None),
):

    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    total_events = len(request.events)

    unique_users = len({event.user for event in request.events})

    revenue = sum(
        event.amount
        for event in request.events
        if event.amount > 0
    )

    totals = {}

    for event in request.events:
        if event.amount > 0:
            totals[event.user] = totals.get(event.user, 0) + event.amount

    top_user = max(totals, key=totals.get) if totals else ""

    return {
        "email": "23f3004469@ds.study.iitm.ac.in",
        "total_events": total_events,
        "unique_users": unique_users,
        "revenue": revenue,
        "top_user": top_user,
    }