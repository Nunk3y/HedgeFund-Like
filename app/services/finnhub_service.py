from __future__ import annotations

import datetime as dt
import time
from typing import Any

import requests

BASE = "https://finnhub.io/api/v1"


def get_json(endpoint: str, params: dict, api_key: str) -> Any:
    params = dict(params)
    params["token"] = api_key
    response = requests.get(f"{BASE}{endpoint}", params=params, timeout=30)
    if response.status_code != 200:
        raise RuntimeError(f"Finnhub HTTP {response.status_code}: {response.text[:500]}")
    return response.json()


def flatten(prefix: str, obj: Any) -> list[tuple[str, Any]]:
    rows: list[tuple[str, Any]] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = f"{prefix}.{k}" if prefix else str(k)
            if isinstance(v, (dict, list)):
                rows.extend(flatten(key, v))
            else:
                rows.append((key, v))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            key = f"{prefix}.{i}" if prefix else str(i)
            if isinstance(v, (dict, list)):
                rows.extend(flatten(key, v))
            else:
                rows.append((key, v))
    else:
        rows.append((prefix, obj))
    return rows


def refresh_finnhub_rows(ticker: str, api_key: str) -> list[dict]:
    ticker = ticker.upper().strip()
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    rows: list[dict] = []

    endpoints = [
        ("quote", "/quote", {"symbol": ticker}),
        ("profile2", "/stock/profile2", {"symbol": ticker}),
        ("metric", "/stock/metric", {"symbol": ticker, "metric": "all"}),
    ]

    for endpoint_name, path, params in endpoints:
        try:
            data = get_json(path, params, api_key)
            if not data:
                rows.append(make_row(ticker, now, endpoint_name, "EMPTY_RESPONSE", "", "MISSING", "Empty response", ""))
            else:
                for field, value in flatten("", data):
                    raw_field = field if endpoint_name != "metric" else field
                    rows.append(make_row(ticker, now, endpoint_name, raw_field, value, "OK", "", ""))
        except Exception as exc:
            rows.append(make_row(ticker, now, endpoint_name, "REQUEST_ERROR", "", "ERROR", str(exc), ""))
        time.sleep(0.15)

    return rows


def make_row(ticker: str, now: str, endpoint: str, field: str, value, status: str, err: str, notes: str) -> dict:
    return {
        "Ticker": ticker,
        "Timestamp": now,
        "Source": "FINNHUB",
        "Endpoint / Metric": endpoint,
        "Raw Field": field,
        "Raw Value": "" if value is None else value,
        "Period": "",
        "Fiscal Year": "",
        "Status": status,
        "Error Message": err,
        "Notes": notes,
        "CIK": "",
        "SEC Concept": "",
        "Unit": "",
        "Form": "",
        "Filed": "",
        "Period Start": "",
        "Period End": "",
        "Frame": "",
        "Accession": "",
    }
