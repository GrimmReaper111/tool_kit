# Ping Tracer

A web-based, real-time, multi-device ping monitoring dashboard.

## Features

- Monitor up to 16 targets (IP addresses or hostnames) simultaneously.
- FastAPI backend with concurrent ping workers using `asyncio` and `ping3`.
- Live updates over WebSockets.
- Browser dashboard with Tailwind CSS + Chart.js.
- Per-device rolling chart (last 60 samples):
  - Latency (ms)
  - Packet loss (%)
- Background anomaly detection:
  - Latency spike: > 3 standard deviations over rolling baseline, or above custom threshold.
  - Packet loss critical: 3 consecutive failures.
  - Flatline/dropout: prolonged no-response.
- Visual anomaly flagging:
  - Card border and status badge color changes.
  - Anomaly history sidebar with timestamps.
- Session trace recording:
  - Each monitoring run stores full per-device samples in-memory for the active session.
  - Expand any device card to inspect the full session timeline.
  - Expanded chart supports horizontal and vertical navigation (scroll + pan/zoom).
  - Anomaly events are marked directly on graphs and preserved for the session.
- Start/Stop global control and editable target list.
- Light/Dark theme toggle.

## Project Structure

```
Ping tracer/
  backend/
    __init__.py
    main.py
    models.py
    monitor.py
  frontend/
    index.html
    assets/
      css/
        styles.css
      js/
        app.js
  requirements.txt
  run_app.bat
  README.md
```

## Setup

1. Open terminal in the `Ping tracer` folder.
2. Create and activate virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Install dependencies:

```powershell
pip install -r requirements.txt
```

## Run

```powershell
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Then open:

- `http://127.0.0.1:8000`

## Quick Start (Windows)

You can also run:

```powershell
.\run_app.bat
```

The batch file auto-opens your browser to `http://127.0.0.1:8000`.

## API

- `GET /api/monitor/state` - Get monitoring state.
- `POST /api/monitor/start` - Start monitoring.
  - Body:

```json
{
  "targets": ["8.8.8.8", "1.1.1.1"],
  "latency_threshold_ms": 200
}
```

- `POST /api/monitor/stop` - Stop monitoring.
- `WS /ws` - Live monitoring and anomaly stream.

## Notes

- ICMP behavior depends on OS permissions/firewall settings. If all pings fail for a valid host, run terminal with elevated privileges or allow ICMP where required.
- The dashboard deduplicates targets and enforces the max limit of 16.
- Baseline uses the latest 50 successful ping samples per target.
