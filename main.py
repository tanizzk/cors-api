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


# -----------------------------
# CORS
# -----------------------------

ALLOWED_ORIGIN = "https://dash-sa5phz.example.com"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------
# Required headers middleware
# -----------------------------

class TimingMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request, call_next):

        start = time.perf_counter()

        response = await call_next(request)

        elapsed = time.perf_counter() - start

        response.headers["X-Request-ID"] = str(uuid.uuid4())
        response.headers["X-Process-Time"] = str(elapsed)

        return response


app.add_middleware(TimingMiddleware)


# ============================================================
# Assignment 1: Metrics API
# ============================================================

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


# ============================================================
# Assignment 2: JWT Verification
# ============================================================

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
            content={
                "valid": False
            }
        )


# ============================================================
# Assignment 3: Effective Config
# ============================================================

DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}


def to_bool(value):

    return str(value).lower() in (
        "true",
        "1",
        "yes",
        "on"
    )


@app.get("/effective-config")
async def effective_config(
    set: list[str] = Query(default=[])
):

    config = DEFAULTS.copy()


    # YAML layer

    try:

        with open("config.development.yaml", "r") as f:

            yaml_config = yaml.safe_load(f)

            if yaml_config:
                config.update(yaml_config)

    except FileNotFoundError:
        pass



    # .env layer

    env_file = dotenv_values(".env")

    env_mapping = {

        "APP_PORT": "port",
        "APP_DEBUG": "debug",
        "APP_LOG_LEVEL": "log_level",
        "APP_API_KEY": "api_key",
        "NUM_WORKERS": "workers",

    }


    for env_key, config_key in env_mapping.items():

        if env_file.get(env_key) is not None:

            config[config_key] = env_file[env_key]



    # OS environment layer

    os_mapping = {

        "APP_PORT": "port",
        "APP_WORKERS": "workers",
        "APP_DEBUG": "debug",
        "APP_LOG_LEVEL": "log_level",
        "APP_API_KEY": "api_key",

    }


    for env_key, config_key in os_mapping.items():

        value = os.environ.get(env_key)

        if value is not None:

            config[config_key] = value



    # CLI overrides

    for item in set:

        if "=" in item:

            key, value = item.split("=", 1)

            config[key] = value



    # Type conversion

    config["port"] = int(config["port"])
    config["workers"] = int(config["workers"])
    config["debug"] = to_bool(config["debug"])
    config["log_level"] = str(config["log_level"])



    # Never expose secret

    config["api_key"] = "****"


    return config



# ============================================================
# Assignment 5: Analytics
# ============================================================

API_KEY = "ak_bjhm2nqfl5b8yf7w5357wlsm"



class Event(BaseModel):

    user: str
    amount: float
    ts: int



class AnalyticsRequest(BaseModel):

    events: list[Event]



@app.post("/analytics")
async def analytics(
    request: AnalyticsRequest,
    x_api_key: str | None = Header(default=None),
):

    if x_api_key != API_KEY:

        raise HTTPException(
            status_code=401,
            detail="Unauthorized"
        )



    total_events = len(request.events)


    unique_users = len(
        {
            event.user
            for event in request.events
        }
    )


    revenue = sum(
        event.amount
        for event in request.events
        if event.amount > 0
    )


    user_totals = {}


    for event in request.events:

        if event.amount > 0:

            user_totals[event.user] = (
                user_totals.get(event.user, 0)
                + event.amount
            )


    top_user = (
        max(user_totals, key=user_totals.get)
        if user_totals
        else ""
    )


    return {

        "email": "23f3004469@ds.study.iitm.ac.in",

        "total_events": total_events,

        "unique_users": unique_users,

        "revenue": revenue,

        "top_user": top_user,

    }