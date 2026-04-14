#!/usr/bin/env python3
import argparse
import json
import time
import urllib.request


def request_json(method: str, url: str, body=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def avg(values):
    return sum(values) / len(values) if values else 0.0


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark Sionna API latency with scene updates per iteration."
    )
    parser.add_argument("--server-url", default="http://127.0.0.1:8000")
    parser.add_argument("--scene-path", default=None)
    parser.add_argument("--iterations", type=int, default=20)
    parser.add_argument("--max-depth", type=int, default=3)
    parser.add_argument("--num-samples", type=int, default=100000)
    parser.add_argument("--warmup", type=int, default=2)
    args = parser.parse_args()

    base = args.server_url.rstrip("/")
    create_payload = {}
    if args.scene_path:
        create_payload["scene_path"] = args.scene_path

    scene = request_json("POST", f"{base}/scenes", create_payload)
    scene_id = scene["scene_id"]

    tx_base = {"lat": 48.1371, "lon": 11.5754, "alt": 25.0}
    rx_base = {"lat": 48.1372, "lon": 11.5755, "alt": 1.5}

    request_json(
        "POST",
        f"{base}/scenes/{scene_id}/transmitters",
        {"name": "tx0", "position": tx_base, "signal_power": 0.0},
    )
    request_json(
        "POST",
        f"{base}/scenes/{scene_id}/receivers",
        {"name": "rx0", "position": rx_base},
    )

    for _ in range(max(0, args.warmup)):
        request_json(
            "POST",
            f"{base}/scenes/{scene_id}/simulation/paths",
            {"max_depth": args.max_depth, "num_samples": args.num_samples},
        )
        request_json("GET", f"{base}/scenes/{scene_id}/simulation/cir")

    path_ms = []
    cir_ms = []
    api_path_ms = []
    api_cir_ms = []

    for i in range(args.iterations):
        # Move RX slightly every iteration so path results are recomputed.
        rx_lat = rx_base["lat"] + (i + 1) * 1e-6
        request_json(
            "PUT",
            f"{base}/scenes/{scene_id}/receivers/rx0",
            {
                "position": {"lat": rx_lat, "lon": rx_base["lon"], "alt": rx_base["alt"]},
                "velocity": {"x": 0.0, "y": 0.0, "z": 0.0},
            },
        )

        t0 = time.perf_counter()
        path_result = request_json(
            "POST",
            f"{base}/scenes/{scene_id}/simulation/paths",
            {"max_depth": args.max_depth, "num_samples": args.num_samples},
        )
        path_ms.append((time.perf_counter() - t0) * 1000.0)
        api_path_ms.append(path_result.get("computation_time", 0))

        t0 = time.perf_counter()
        cir_result = request_json("GET", f"{base}/scenes/{scene_id}/simulation/cir")
        cir_ms.append((time.perf_counter() - t0) * 1000.0)
        api_cir_ms.append(cir_result.get("computation_time", 0))

    summary = {
        "serverUrl": base,
        "sceneId": scene_id,
        "scenePath": args.scene_path,
        "iterations": args.iterations,
        "maxDepth": args.max_depth,
        "numSamples": args.num_samples,
        "avgPathsMs": round(avg(path_ms), 2),
        "avgCirResMs": round(avg(cir_ms), 2),
        "avgApiPathsComputeMs": round(avg(api_path_ms), 2),
        "avgApiCirComputeMs": round(avg(api_cir_ms), 2),
        "pathSamplesMs": [round(v, 2) for v in path_ms],
        "cirSamplesMs": [round(v, 2) for v in cir_ms],
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
