#!/usr/bin/env python3

import sys
import csv
import json
import time
import argparse
from urllib import request, error

TOWER = {"lat": 35.72750947, "lon": -78.69595819, "alt": 124.0}
DEFAULT_RX = {"lat": 35.7274373, "lon": -78.6962452, "alt": 115.19}


def _req(url, body=None, method="GET", timeout=300):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    r = request.Request(url, data=data, headers=headers, method=method)
    with request.urlopen(r, timeout=timeout) as resp:
        raw = resp.read()
    return json.loads(raw.decode()) if raw else None


def load_waypoints(path, max_frames):
    with open(path) as f:
        rows = [{"lat": float(r["Lat"]), "lon": float(r["Lng"]), "alt": float(r["Alt"])}
                for r in csv.DictReader(f)]
    stride = max(1, len(rows) // max_frames) if max_frames else 1
    return rows[::stride]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default="http://localhost:8000")
    ap.add_argument("--scene", help="Existing scene id. Default: create an aerpaw scene")
    ap.add_argument("--csv", help="Vehicle log CSV; fly the RX along it")
    ap.add_argument("--rx", nargs=3, type=float, metavar=("LAT", "LON", "ALT"),
                    help="Static RX waypoint (alt in HAE). Ignored when --csv is given")
    ap.add_argument("--tx-name", default="lw1_tower")
    ap.add_argument("--rx-name", default="rover")
    ap.add_argument("--signal-power", type=float, default=30.0)
    ap.add_argument("--interval", type=float, default=1.0, help="Seconds between RX moves")
    ap.add_argument("--max-frames", type=int, default=150, help="Downsample log to N steps (0 = all)")
    ap.add_argument("--loop", action="store_true", help="Repeat the track forever")
    args = ap.parse_args()

    base = args.url.rstrip("/")
    waypoints = load_waypoints(args.csv, args.max_frames) if args.csv else [
        {"lat": args.rx[0], "lon": args.rx[1], "alt": args.rx[2]} if args.rx else DEFAULT_RX
    ]

    sid = args.scene
    if not sid:
        sid = _req(f"{base}/scenes", {"scene_config": "aerpaw"}, "POST")["scene_id"]
        print(f"Created scene: {sid}")
    else:
        print(f"Using scene: {sid}")

    try:
        _req(f"{base}/scenes/{sid}/transmitters",
             {"name": args.tx_name, "position": TOWER, "signal_power": args.signal_power}, "POST")
        print(f"Added TX {args.tx_name} at {TOWER}")
    except error.HTTPError:
        print(f"TX {args.tx_name} exists; leaving as is")

    try:
        _req(f"{base}/scenes/{sid}/receivers",
             {"name": args.rx_name, "position": waypoints[0]}, "POST")
        print(f"Added RX {args.rx_name} at {waypoints[0]}")
    except error.HTTPError:
        print(f"RX {args.rx_name} exists; will update")

    print(f"\nScene ready: {sid}")
    print(f"Render it with:\n  python test/poll_render.py --scene {sid} --out test/renders_live\n")

    if len(waypoints) == 1:
        return sid

    print(f"Flying RX along {len(waypoints)} waypoints (Ctrl-C to stop)")
    while True:
        for i, wp in enumerate(waypoints):
            t0 = time.time()
            try:
                _req(f"{base}/scenes/{sid}/receivers/{args.rx_name}", {"position": wp}, "PUT")
                print(f"[{i + 1}/{len(waypoints)}] RX -> {wp['lat']:.6f} {wp['lon']:.6f} {wp['alt']:.1f}")
            except error.HTTPError as e:
                print(f"[{i + 1}] update failed: HTTP {e.code}")
            time.sleep(max(0.0, args.interval - (time.time() - t0)))
        if not args.loop:
            break
    return sid


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
    except error.HTTPError as e:
        print(f"HTTP {e.code} ({e.reason}): {e.read().decode(errors='ignore')}", file=sys.stderr)
        sys.exit(1)
    except error.URLError as e:
        print(f"Cannot reach server: {e}", file=sys.stderr)
        sys.exit(1)
