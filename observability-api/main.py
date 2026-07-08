from fastapi import FastAPI, Request, Query
from fastapi.responses import PlainTextResponse
from prometheus_client import Counter, generate_latest
import time
import uuid
import json
from collections import deque
from datetime import datetime


app = FastAPI()


EMAIL = "23f3004469@ds.study.iitm.ac.in"


# -------------------------
# Metrics
# -------------------------

REQUEST_COUNTER = Counter(
    "http_requests_total",
    "Total HTTP requests"
)


# -------------------------
# Startup time
# -------------------------

START_TIME = time.time()


# -------------------------
# In-memory structured logs
# -------------------------

logs = deque(maxlen=100)


def add_log(path, request_id):
    entry = {
        "level": "INFO",
        "ts": datetime.utcnow().isoformat(),
        "path": path,
        "request_id": request_id
    }

    logs.append(entry)


# -------------------------
# Middleware
# -------------------------

@app.middleware("http")
async def logging_middleware(request: Request, call_next):

    request_id = str(uuid.uuid4())

    REQUEST_COUNTER.inc()

    response = await call_next(request)

    add_log(
        request.url.path,
        request_id
    )

    response.headers["X-Request-ID"] = request_id

    return response



# -------------------------
# Work endpoint
# -------------------------

@app.get("/work")
def work(n: int = Query(...)):

    for _ in range(n):
        pass

    return {
        "email": EMAIL,
        "done": n
    }



# -------------------------
# Prometheus metrics
# -------------------------

@app.get("/metrics")
def metrics():

    return PlainTextResponse(
        generate_latest(),
        media_type="text/plain"
    )



# -------------------------
# Health
# -------------------------

@app.get("/healthz")
def healthz():

    return {
        "status": "ok",
        "uptime_s": time.time() - START_TIME
    }



# -------------------------
# Logs
# -------------------------

@app.get("/logs/tail")
def logs_tail(limit: int = 10):

    return list(logs)[-limit:]