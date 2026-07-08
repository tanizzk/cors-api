import os
import time
import uuid
import json
import re
from collections import defaultdict, deque

import redis
import jwt
import yaml

from fastapi import FastAPI, Request, Response, Query, Header, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, generate_latest
from pydantic import BaseModel

from dotenv import dotenv_values

import config


# -----------------------------
# App setup
# -----------------------------

app = FastAPI()

START_TIME = time.time()

ALLOWED_ORIGIN = "https://dash-sa5phz.example.com"


app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------
# Redis
# -----------------------------

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True
)


# -----------------------------
# Metrics + Logs
# -----------------------------

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP Requests"
)

logs_queue = deque(maxlen=100)


@app.middleware("http")
async def request_logger(request: Request, call_next):

    start = time.time()

    request_id = str(uuid.uuid4())

    http_requests_total.inc()

    logs_queue.append(
        {
            "level": "INFO",
            "ts": time.time(),
            "path": request.url.path,
            "request_id": request_id
        }
    )

    try:
        response = await call_next(request)
    except Exception:
        response = Response(
            status_code=500,
            content="Internal Server Error"
        )

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = str(
        time.time() - start
    )

    return response



# -----------------------------
# Q1 Stats
# -----------------------------

@app.get("/stats")
async def stats(values: str = Query(...)):

    numbers = [
        int(x.strip())
        for x in values.split(",")
    ]

    return {
        "email": config.EMAIL,
        "count": len(numbers),
        "sum": sum(numbers),
        "min": min(numbers),
        "max": max(numbers),
        "mean": sum(numbers) / len(numbers)
    }



# -----------------------------
# Q2 JWT Verification
# -----------------------------

class TokenRequest(BaseModel):
    token: str



@app.post("/verify")
async def verify(request: TokenRequest):

    try:

        payload = jwt.decode(
            request.token,
            config.PUBLIC_KEY_PEM,
            algorithms=["RS256"],
            issuer=config.ISSUER,
            audience=config.AUDIENCE
        )

        return {
            "valid": True,
            "email": payload.get("email"),
            "sub": payload.get("sub"),
            "aud": payload.get("aud")
        }


    except Exception:

        return JSONResponse(
            status_code=401,
            content={
                "valid": False
            }
        )



# -----------------------------
# Q3 Effective Config
# -----------------------------

DEFAULTS = {
    "port":8000,
    "workers":1,
    "debug":False,
    "log_level":"info",
    "api_key":"default-secret"
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

    cfg = DEFAULTS.copy()


    if os.path.exists("config.development.yaml"):

        with open(
            "config.development.yaml"
        ) as f:

            yaml_cfg = yaml.safe_load(f)

            if yaml_cfg:
                cfg.update(yaml_cfg)



    env = dotenv_values(".env")


    mapping = {
        "APP_PORT":"port",
        "APP_WORKERS":"workers",
        "APP_DEBUG":"debug",
        "APP_LOG_LEVEL":"log_level"
    }


    for key,value in mapping.items():

        if key in env:
            cfg[value] = env[key]


        if os.getenv(key):
            cfg[value] = os.getenv(key)



    for item in set:

        if "=" in item:

            key,value = item.split("=",1)

            cfg[key]=value



    cfg["port"]=int(cfg["port"])

    cfg["workers"]=int(cfg["workers"])

    cfg["debug"]=to_bool(cfg["debug"])

    cfg["api_key"]="****"


    return cfg
# -----------------------------
# Q4 Redis Counter Service
# -----------------------------


@app.post("/hit/{key}")
async def hit(key: str):

    count = redis_client.incr(key)

    return {
        "key": key,
        "count": count
    }



@app.get("/count/{key}")
async def count(key: str):

    value = redis_client.get(key)

    return {
        "key": key,
        "count": int(value) if value else 0
    }



# Q4 health check
# (kept Redis validation here)

@app.get("/redis-health")
async def redis_health():

    try:

        redis_client.ping()

        return {
            "status":"ok",
            "redis":"up"
        }

    except Exception:

        return {
            "status":"error",
            "redis":"down"
        }



# -----------------------------
# Q5 Analytics Endpoint
# -----------------------------

API_KEY = "ak_bjhm2nqfl5b8yf7w5357wlsm"



@app.post("/analytics")
async def analytics(
    request: Request,
    x_api_key: str = Header(None)
):

    if x_api_key != API_KEY:

        raise HTTPException(
            status_code=401,
            detail="Unauthorized"
        )


    body = await request.json()

    events = body.get(
        "events",
        []
    )


    total_events = len(events)

    users = set()

    revenue = 0.0

    user_totals = defaultdict(float)


    for event in events:

        user = event.get("user")

        amount = event.get(
            "amount",
            0
        )


        users.add(user)


        if amount > 0:

            revenue += amount

            user_totals[user] += amount



    top_user = None

    if user_totals:

        top_user = max(
            user_totals,
            key=user_totals.get
        )



    return {

        "email": config.EMAIL,

        "total_events": total_events,

        "unique_users": len(users),

        "revenue": revenue,

        "top_user": top_user

    }




# -----------------------------
# Q6 Observability
# -----------------------------


@app.get("/work")
async def work(
    n: int = 1
):

    return {

        "email": config.EMAIL,

        "done": n

    }




@app.get("/metrics")
async def metrics():

    return Response(

        content=generate_latest(),

        media_type="text/plain; version=0.0.4"

    )




@app.get("/healthz")
async def healthz():

    uptime = time.time() - START_TIME


    return {

        "status":"ok",

        "uptime_s":float(uptime)

    }




@app.get("/logs/tail")
async def logs_tail(
    limit:int = 10
):

    return list(logs_queue)[-limit:]




# -----------------------------
# Q9 Orders
# -----------------------------


@app.post("/orders")
async def create_order(
    request: Request
):

    idem = request.headers.get(
        "Idempotency-Key"
    )


    if idem:

        existing = redis_client.get(
            f"idem:{idem}"
        )

        if existing:

            return {
                "id": existing
            }



    order_id = str(uuid.uuid4())


    if idem:

        redis_client.setex(
            f"idem:{idem}",
            3600,
            order_id
        )


    return JSONResponse(

        status_code=201,

        content={
            "id":order_id
        }

    )




@app.get("/orders")
async def get_orders(
    limit:int=10,
    cursor:str=None
):

    total = getattr(
        config,
        "Q9_TOTAL_ORDERS",
        50
    )


    items = [

        {
            "id":i
        }

        for i in range(
            1,
            total+1
        )

    ]


    start = int(cursor) if cursor else 0


    page = items[
        start:start+limit
    ]


    next_cursor = None


    if start+limit < len(items):

        next_cursor = str(
            start+limit
        )


    return {

        "items":page,

        "next_cursor":next_cursor

    }





# -----------------------------
# Q10 Ping
# -----------------------------


@app.get("/ping")
async def ping(
    request:Request
):

    return {

        "email":config.EMAIL,

        "request_id":
            request.headers.get(
                "X-Request-ID",
                ""
            )

    }