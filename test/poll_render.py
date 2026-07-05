#!/usr/bin/env python3
"""Poll a running Sionna RT server and save a render of every scene each second.

Saves each frame to <out>/<scene_id>/<timestamp>.png (never overwrites).

    python poll_render.py                       # localhost:8000, every 1s
    python poll_render.py --url http://host:8000 --interval 2
    python poll_render.py --scene <id>          # only this scene
"""
import os
import sys
import json
import time
import argparse
import datetime as dt
from urllib import request, parse, error

# Default create-scene body (aerpaw). Only used with --create.
AERPAW_BODY = {
    "scene_config": "aerpaw",
    "scene_origin": {"lat": 35.72750947, "lon": -78.69595819, "alt": 112.0},
    "scene_offset": {"x": -3.7, "y": 3.4, "z": 0.0},
    "scale": 1.0,
}


def _get(url, timeout=120):
    with request.urlopen(url, timeout=timeout) as r:
        return r.read(), r.headers.get("Content-Type", "")


def _post_json(url, body, timeout=300):
    data = json.dumps(body).encode()
    req = request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def list_scenes(base):
    raw, _ = _get(f"{base}/scenes")
    return json.loads(raw.decode())


def render_scene(base, scene_id, params):
    q = parse.urlencode(params)
    return _get(f"{base}/scenes/{scene_id}/render?{q}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default="http://localhost:8000", help="Server base URL")
    ap.add_argument("--interval", type=float, default=1.0, help="Seconds between polls")
    ap.add_argument("--out", default="renders_live", help="Output directory")
    ap.add_argument("--scene", action="append", dest="scenes", help="Specific scene id (repeatable). Default: all")
    ap.add_argument("--create", action="store_true", help="Create an aerpaw scene first and poll it")
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--num-samples", type=int, default=96)
    ap.add_argument("--max-depth", type=int, default=3)
    ap.add_argument("--view-from", default="north", choices=["north", "south"])
    ap.add_argument("--no-paths", action="store_true", help="Do not overlay rays")
    args = ap.parse_args()

    base = args.url.rstrip("/")
    os.makedirs(args.out, exist_ok=True)

    fixed_scenes = list(args.scenes) if args.scenes else None
    if args.create:
        try:
            resp = _post_json(f"{base}/scenes", AERPAW_BODY)
            sid = resp["scene_id"]
            print(f"Created scene {sid}")
            fixed_scenes = (fixed_scenes or []) + [sid]
        except error.URLError as e:
            print(f"Failed to create scene: {e}", file=sys.stderr)
            return 1

    render_params = {
        "width": args.width, "height": args.height, "num_samples": args.num_samples,
        "max_depth": args.max_depth, "view_from": args.view_from,
        "show_paths": str(not args.no_paths).lower(),
    }

    print(f"Polling {base} every {args.interval}s -> {args.out}/  (Ctrl-C to stop)")
    while True:
        t0 = time.time()
        try:
            scenes = fixed_scenes if fixed_scenes else list_scenes(base)
        except error.URLError as e:
            print(f"[{dt.datetime.now():%H:%M:%S}] cannot reach server: {e}")
            time.sleep(args.interval)
            continue

        if not scenes:
            print(f"[{dt.datetime.now():%H:%M:%S}] no scenes available")

        for sid in scenes:
            stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            try:
                png, ctype = render_scene(base, sid, render_params)
            except error.HTTPError as e:
                print(f"[{stamp}] {sid[:8]}: HTTP {e.code} ({e.reason})")
                continue
            except error.URLError as e:
                print(f"[{stamp}] {sid[:8]}: {e}")
                continue

            if "image" not in ctype:
                print(f"[{stamp}] {sid[:8]}: unexpected content-type {ctype!r}")
                continue

            scene_dir = os.path.join(args.out, sid)
            os.makedirs(scene_dir, exist_ok=True)
            path = os.path.join(scene_dir, f"{stamp}.png")
            with open(path, "wb") as f:
                f.write(png)
            print(f"[{stamp}] {sid[:8]}: saved {path} ({len(png)} bytes)")

        time.sleep(max(0.0, args.interval - (time.time() - t0)))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nStopped.")
