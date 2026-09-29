from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = REPO_ROOT / "data" / "logs.jsonl"
CONFIG_PATH = REPO_ROOT / "config" / "dashboard.yaml"


def _number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)
    return result.astimezone(timezone.utc)


def _percentile(values: list[float], percentile: int) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile / 100
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _status(value: float | None, operator: str, threshold: float) -> bool | None:
    if value is None:
        return None
    return value <= threshold if operator == "lte" else value >= threshold


def _series_by_minute(
    rows: list[dict], start: datetime, minutes: int, measure
) -> list[dict[str, float | str]]:
    buckets: dict[datetime, list[dict]] = defaultdict(list)
    for row in rows:
        timestamp = row.get("_timestamp")
        if isinstance(timestamp, datetime):
            buckets[timestamp.replace(second=0, microsecond=0)].append(row)

    series = []
    minute = start.replace(second=0, microsecond=0)
    last_minute = (start + timedelta(minutes=minutes)).replace(
        second=0, microsecond=0
    )
    bucket_count = int((last_minute - minute).total_seconds() // 60) + 1
    for offset in range(bucket_count):
        bucket_minute = minute + timedelta(minutes=offset)
        series.append(
            {
                "label": bucket_minute.strftime("%H:%M"),
                "value": float(measure(buckets.get(bucket_minute, []))),
            }
        )
    return series


def compute_dashboard_data(now: datetime | None = None) -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as handle:
        contract = yaml.safe_load(handle)["dashboard"]

    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    window_minutes = int(contract["time_range_minutes"])
    start = now - timedelta(minutes=window_minutes)
    records = []
    if LOG_PATH.exists():
        for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            timestamp = _timestamp(record.get("ts")) if isinstance(record, dict) else None
            if timestamp is not None and start <= timestamp <= now:
                record["_timestamp"] = timestamp
                records.append(record)

    requests = [row for row in records if row.get("event") == "request_received"]
    responses = [row for row in records if row.get("event") == "response_sent"]
    failures = [row for row in records if row.get("event") == "request_failed"]
    all_results = responses + failures

    latencies = [value for row in responses if (value := _number(row.get("latency_ms"))) is not None]
    ttft = [value for row in responses if (value := _number(row.get("ttft_ms"))) is not None]
    costs = [value for row in responses if (value := _number(row.get("cost_usd"))) is not None]
    tokens_in = [value for row in responses if (value := _number(row.get("tokens_in"))) is not None]
    tokens_out = [value for row in responses if (value := _number(row.get("tokens_out"))) is not None]
    qualities = [value for row in responses if (value := _number(row.get("quality_score"))) is not None]

    error_rate = len(failures) / len(requests) * 100 if requests else None
    retrieval_values = [row.get("tool_success") for row in all_results if isinstance(row.get("tool_success"), bool)]
    retrieval_success = (
        sum(retrieval_values) / len(retrieval_values) * 100
        if retrieval_values
        else None
    )
    error_types = Counter(
        str(row["error_type"])
        for row in failures
        if row.get("error_type") is not None
    )

    panels_by_id = {panel["id"]: panel for panel in contract["panels"]}

    def build_panel(panel_id: str, values: list[dict], series: list[dict], threshold_value: float | None):
        spec = panels_by_id[panel_id]
        threshold = spec["threshold"]
        status = _status(
            threshold_value,
            threshold["operator"],
            float(threshold["value"]),
        )
        return {
            "id": panel_id,
            "title": spec["title"],
            "unit": spec["unit"],
            "threshold": threshold,
            "status": status,
            "values": values,
            "series": series,
        }

    traffic_rate = len(requests) / window_minutes if requests else None
    panels = [
        build_panel(
            "latency",
            [
                {"label": "P50", "value": _percentile(latencies, 50)},
                {"label": "P95", "value": _percentile(latencies, 95)},
                {"label": "P99", "value": _percentile(latencies, 99)},
                {"label": "TTFT P95", "value": _percentile(ttft, 95)},
            ],
            _series_by_minute(
                responses,
                start,
                window_minutes,
                lambda bucket: _percentile(
                    [v for row in bucket if (v := _number(row.get("latency_ms"))) is not None],
                    95,
                ) or 0,
            ),
            _percentile(latencies, 95),
        ),
        build_panel(
            "traffic",
            [
                {"label": "Requests", "value": len(requests)},
                {"label": "Requests/min", "value": traffic_rate},
            ],
            _series_by_minute(requests, start, window_minutes, len),
            traffic_rate,
        ),
        build_panel(
            "errors",
            [
                {"label": "Error rate", "value": error_rate},
                {"label": "Failed", "value": len(failures)},
                {"label": "Retrieval success", "value": retrieval_success},
            ],
            _series_by_minute(
                requests,
                start,
                window_minutes,
                lambda bucket: (
                    len([r for r in failures if r.get("_timestamp").replace(second=0, microsecond=0) == bucket[0]["_timestamp"].replace(second=0, microsecond=0)])
                    / len(bucket)
                    * 100
                    if bucket
                    else 0
                ),
            ),
            error_rate,
        ),
        build_panel(
            "cost",
            [{"label": "Total cost", "value": sum(costs) if costs else None}],
            _series_by_minute(
                responses,
                start,
                window_minutes,
                lambda bucket: sum(
                    v for row in bucket if (v := _number(row.get("cost_usd"))) is not None
                ),
            ),
            sum(costs) if costs else None,
        ),
        build_panel(
            "tokens",
            [
                {"label": "Input", "value": sum(tokens_in) if tokens_in else None},
                {"label": "Output", "value": sum(tokens_out) if tokens_out else None},
            ],
            _series_by_minute(
                responses,
                start,
                window_minutes,
                lambda bucket: sum(
                    (_number(row.get("tokens_in")) or 0)
                    + (_number(row.get("tokens_out")) or 0)
                    for row in bucket
                ),
            ),
            (sum(tokens_in) + sum(tokens_out)) if tokens_in or tokens_out else None,
        ),
        build_panel(
            "quality",
            [{"label": "Mean score", "value": sum(qualities) / len(qualities) if qualities else None}],
            _series_by_minute(
                responses,
                start,
                window_minutes,
                lambda bucket: (
                    sum(values) / len(values)
                    if (values := [v for row in bucket if (v := _number(row.get("quality_score"))) is not None])
                    else 0
                ),
            ),
            sum(qualities) / len(qualities) if qualities else None,
        ),
    ]

    return {
        "title": contract["title"],
        "time_range_minutes": window_minutes,
        "refresh_seconds": int(contract["refresh_seconds"]),
        "updated_at": now.isoformat(timespec="seconds"),
        "source": "data/logs.jsonl",
        "records": len(records),
        "error_types": dict(error_types),
        "panels": panels,
    }


PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Day 13 Monitoring &amp; LLMOps</title>
<style>
:root{color-scheme:dark;--bg:#0b1020;--panel:#121a2d;--line:#26324b;--muted:#93a4c3;--text:#edf2ff;--accent:#64d7c4;--good:#36c98f;--bad:#ff7285;--warn:#f5c568}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 12% 0%,#162643 0,transparent 34%),var(--bg);color:var(--text);font:15px/1.45 system-ui,Segoe UI,sans-serif}
main{max-width:1360px;margin:0 auto;padding:36px 28px 48px}.top{display:flex;justify-content:space-between;align-items:end;gap:20px;margin-bottom:24px}.eyebrow{color:var(--accent);font-size:12px;font-weight:700;letter-spacing:.14em;text-transform:uppercase}h1{font-size:clamp(26px,4vw,40px);line-height:1.1;margin:8px 0}.meta{color:var(--muted);text-align:right;font-size:13px}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}.card{background:linear-gradient(155deg,rgba(25,36,61,.96),rgba(15,23,40,.97));border:1px solid var(--line);border-radius:18px;padding:20px;min-height:226px;box-shadow:0 14px 34px #0003}.cardhead{display:flex;justify-content:space-between;align-items:center;gap:12px}.card h2{font-size:17px;margin:0}.status{border-radius:999px;padding:4px 9px;font-size:11px;font-weight:700;background:#26324b;color:var(--muted)}.status.good{background:#123d37;color:#77edc0}.status.bad{background:#4d2432;color:#ff9aab}.status.nodata{background:#283147;color:#c1cbe0}.values{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-top:18px}.metric{background:#0c1425;border:1px solid #202c42;border-radius:12px;padding:10px 12px}.label{color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.06em}.value{font-size:21px;font-weight:700;margin-top:3px}.unit{font-size:11px;color:var(--muted);font-weight:500}.threshold{margin-top:15px;color:var(--muted);font-size:12px}.bars{height:38px;display:flex;align-items:end;gap:2px;margin-top:12px}.bar{flex:1;min-width:2px;background:linear-gradient(180deg,var(--accent),#3995bd);border-radius:3px 3px 0 0;opacity:.85}.detail{font-size:12px;color:#c5d0e5;margin-top:8px}.footer{margin-top:22px;color:var(--muted);font-size:12px;display:flex;justify-content:space-between}.error{color:var(--bad)}
@media(max-width:900px){.grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:620px){main{padding:24px 14px}.grid{grid-template-columns:1fr}.top{align-items:start;flex-direction:column}.meta{text-align:left}}
</style></head><body><main>
<header class="top"><div><div class="eyebrow">Observability · live dashboard</div><h1 id="title">Day 13 Monitoring &amp; LLMOps</h1><div class="meta" id="source">Structured logs · 6 panels</div></div><div class="meta"><div id="window">Last 60 minutes</div><div id="updated">Waiting for data…</div></div></header>
<section class="grid" id="panels" aria-live="polite"></section><footer class="footer"><span>Refresh: <b id="refresh">30</b>s · Thresholds from config/dashboard.yaml</span><span id="records">0 log records in range</span></footer>
</main><script>
const fmt=(x)=>x===null||x===undefined?"—":(Number.isInteger(x)?x.toLocaleString():Number(x).toLocaleString(undefined,{maximumFractionDigits:2}));
function render(data){document.getElementById('title').textContent=data.title;document.getElementById('window').textContent=`Last ${data.time_range_minutes} minutes`;document.getElementById('updated').textContent=`Updated ${new Date(data.updated_at).toLocaleTimeString()}`;document.getElementById('source').textContent=`Source: ${data.source} · 6 panels`;document.getElementById('refresh').textContent=data.refresh_seconds;document.getElementById('records').textContent=`${data.records.toLocaleString()} log records in range`;
const host=document.getElementById('panels');host.replaceChildren();for(const panel of data.panels){const card=document.createElement('article');card.className='card';const head=document.createElement('div');head.className='cardhead';const title=document.createElement('h2');title.textContent=panel.title;const status=document.createElement('span');status.className='status '+(panel.status===null?'nodata':panel.status?'good':'bad');status.textContent=panel.status===null?'NO DATA':panel.status?'WITHIN THRESHOLD':'THRESHOLD BREACHED';head.append(title,status);card.append(head);const values=document.createElement('div');values.className='values';for(const item of panel.values){const metric=document.createElement('div');metric.className='metric';const label=document.createElement('div');label.className='label';label.textContent=item.label;const value=document.createElement('div');value.className='value';value.textContent=fmt(item.value);const unit=document.createElement('span');unit.className='unit';unit.textContent=` ${panel.unit}`;value.append(unit);metric.append(label,value);values.append(metric)}card.append(values);const threshold=document.createElement('div');threshold.className='threshold';threshold.textContent=`Threshold: ${panel.threshold.aggregation} ${panel.threshold.operator==='lte'?'≤':'≥'} ${panel.threshold.value} ${panel.unit}`;card.append(threshold);const bars=document.createElement('div');bars.className='bars';const max=Math.max(1,...panel.series.map(x=>x.value||0));for(const point of panel.series){const bar=document.createElement('span');bar.className='bar';bar.style.height=`${Math.max(3,Math.min(100,(point.value||0)/max*100))}%`;bar.title=`${point.label}: ${fmt(point.value)}`;bars.append(bar)}card.append(bars);if(panel.id==='errors'){const detail=document.createElement('div');detail.className='detail';detail.textContent=`Error breakdown: ${Object.entries(data.error_types).map(([k,v])=>`${k} ${v}`).join(' · ')||'none'}`;card.append(detail)}host.append(card)}}
async function refresh(){try{const response=await fetch('/api/dashboard',{cache:'no-store'});if(!response.ok)throw new Error(`HTTP ${response.status}`);render(await response.json())}catch(error){document.getElementById('updated').textContent=`Dashboard refresh failed: ${error}`;document.getElementById('updated').className='error'}}refresh();setInterval(refresh,30000);
</script></body></html>"""


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        route = urlparse(self.path).path
        if route == "/api/dashboard":
            payload = json.dumps(compute_dashboard_data(), ensure_ascii=False).encode("utf-8")
            content_type = "application/json; charset=utf-8"
        elif route == "/":
            payload = PAGE.encode("utf-8")
            content_type = "text/html; charset=utf-8"
        else:
            self.send_error(404)
            return

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        print("dashboard:", format % args)


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve a six-panel dashboard from data/logs.jsonl")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), DashboardHandler)
    print(f"Dashboard: http://{args.host}:{args.port} (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping dashboard.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
