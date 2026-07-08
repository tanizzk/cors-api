from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

import uuid
import time

app = FastAPI()

ALLOWED_ORIGIN = "https://dash-sa5phz.example.com"

app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.perf_counter()

        response = await call_next(request)

        elapsed = time.perf_counter() - start

        response.headers["X-Request-ID"] = str(uuid.uuid4())
        response.headers["X-Process-Time"] = str(elapsed)

        return response


app.add_middleware(TimingMiddleware)


@app.get("/stats")
async def stats(values: str = Query(...)):
    numbers = [int(v.strip()) for v in values.split(",")]

    return {
        "email": "23f3004469@ds.study.iitm.ac.in",
        "count": len(numbers),
        "sum": sum(numbers),
        "min": min(numbers),
        "max": max(numbers),
        "mean": sum(numbers) / len(numbers)
    }