import os
import csv
import time
import glob
import subprocess

import numpy as np

from pyproj import Transformer
from pyproj.enums import TransformDirection

from sionna.rt import (
    load_scene,
    PlanarArray,
    Transmitter,
    Receiver,
    PathSolver,
    Camera,
)

SCENE_PATH = "data/sionna_export/aerpaw_sionna.xml"
OUTPUT_DIR = "renders"
FRAME_DIR = os.path.join(OUTPUT_DIR, "frames")
VIDEO_PATH = os.path.join(OUTPUT_DIR, "render.mp4")

# From experiment
WAYPOINTS_CSV = "2026-05-21_17_38_vehicle_log.csv"
MAX_FRAMES = 150          
FPS = 15                  # output video frame rate

GROUND_ALT_HAE = 112.0
SCENE_ORIGIN = {"lat": 35.72750947, "lon": -78.69595819, "alt": GROUND_ALT_HAE}
SCENE_OFFSET = np.array([118.1, -123.4, 0.0])

TOWER_XYZ = [float(SCENE_OFFSET[0]), float(SCENE_OFFSET[1]), 12.0]

DEVICE_DISPLAY_RADIUS = 2.0   # meters; default ~15 m on a 2 km scene (too big)

os.makedirs(FRAME_DIR, exist_ok=True)


def make_enu_meters_transformer(origin):
    pipeline = (
        "+proj=pipeline "
        "+step +proj=unitconvert +xy_in=deg +z_in=m +xy_out=rad +z_out=m "
        "+step +proj=cart +ellps=WGS84 "
        "+step +proj=topocentric +ellps=WGS84 "
        f"+lon_0={origin['lon']} +lat_0={origin['lat']} +h_0={origin['alt']}"
    )
    return Transformer.from_pipeline(pipeline)


def lla_to_scene(transformer, lat, lon, alt):
    """lat/lon/alt -> (x, y, z) in scene meters (ENU + SCENE_OFFSET)."""
    east, north, up = transformer.transform(
        lon, lat, alt, direction=TransformDirection.FORWARD
    )
    return (
        east + SCENE_OFFSET[0],
        north + SCENE_OFFSET[1],
        up + SCENE_OFFSET[2],
    )


def load_waypoints(path, max_frames):
    rows = []
    with open(path) as f:
        for r in csv.DictReader(f):
            rows.append((float(r["Lat"]), float(r["Lng"]), float(r["Alt"])))
    # Downsample
    stride = max(1, len(rows) // max_frames)
    sampled = rows[::stride]
    print(f"Loaded {len(rows)} log rows -> {len(sampled)} frames (stride {stride})")
    return sampled


def framing_camera(points, elevation_deg=28.0, dist_factor=2.2, min_dist=140.0):
    pts = np.asarray(points, dtype=float)
    pmin, pmax = pts.min(0), pts.max(0)
    mid = (pmin + pmax) / 2.0
    span = float(np.linalg.norm((pmax - pmin)[:2])) or min_dist
    dist = max(span * dist_factor, min_dist)
    elev = np.radians(elevation_deg)
    pos = [float(mid[0]), float(mid[1] + dist * np.cos(elev)), float(mid[2] + dist * np.sin(elev))]
    look = [float(mid[0]), float(mid[1]), float(mid[2])]
    return Camera(position=pos, look_at=look)


print(f"Loading scene: {SCENE_PATH}")
scene = load_scene(SCENE_PATH)

bbox = scene.mi_scene.bbox()
bmin, bmax = np.array(bbox.min), np.array(bbox.max)
print("Scene info:")
print(f"  bbox min   = {bmin}")
print(f"  bbox max   = {bmax}")
print(f"  extents(m) = {bmax - bmin}")
print(f"  center     = {(bmin + bmax) / 2.0}")
print(f"  objects    = {len(scene.objects)}")

array_kwargs = dict(
    num_rows=1, num_cols=1,
    vertical_spacing=0.5, horizontal_spacing=0.5,
    pattern="iso", polarization="V",
)
scene.tx_array = PlanarArray(**array_kwargs)
scene.rx_array = PlanarArray(**array_kwargs)

# TX = LW1 tower; RX = rover 
tx = Transmitter("tx", TOWER_XYZ)
rx = Receiver("rx", [0.0, 0.0, 5.0]) 
tx.display_radius = DEVICE_DISPLAY_RADIUS
rx.display_radius = DEVICE_DISPLAY_RADIUS
scene.add(tx)
scene.add(rx)

solver = PathSolver()

enu = make_enu_meters_transformer(SCENE_ORIGIN)
waypoints = load_waypoints(WAYPOINTS_CSV, MAX_FRAMES)
track_xyz = np.array([lla_to_scene(enu, la, lo, al) for la, lo, al in waypoints])
print(f"Track scene bounds: X{track_xyz[:,0].min():.0f}..{track_xyz[:,0].max():.0f} "
      f"Y{track_xyz[:,1].min():.0f}..{track_xyz[:,1].max():.0f} "
      f"Z{track_xyz[:,2].min():.0f}..{track_xyz[:,2].max():.0f}")
print(f"TX tower @ {TOWER_XYZ}")

camera = framing_camera(np.vstack([track_xyz, TOWER_XYZ]))

print("\nRendering frames...\n")
t_start = time.time()
for idx, pos in enumerate(track_xyz):
    rx.position = pos.tolist()
    paths = solver(scene=scene, max_depth=3, samples_per_src=100000)
    num_paths = int(paths.valid.numpy().sum())

    filepath = os.path.join(FRAME_DIR, f"frame_{idx:04d}.png")

    def _render(with_paths):
        scene.render_to_file(
            filename=filepath,
            camera=camera,
            paths=with_paths,
            resolution=[960, 720],
            num_samples=96,
            show_devices=True,
        )

    try:
        _render(paths)
    except Exception as exc: 
        print(f"  [warn] frame {idx}: ray overlay failed ({exc}); rendering without rays")
        _render(None)
    if idx % 10 == 0 or idx == len(track_xyz) - 1:
        print(f"[{idx + 1}/{len(track_xyz)}] rover={np.round(pos, 1)} paths={num_paths}")

print(f"\nRendered {len(track_xyz)} frames in {time.time() - t_start:.1f}s")

n_frames = len(glob.glob(os.path.join(FRAME_DIR, "frame_*.png")))
if n_frames == 0:
    raise SystemExit("No frames rendered; nothing to encode.")

cmd = [
    "ffmpeg", "-y",
    "-framerate", str(FPS),
    "-i", os.path.join(FRAME_DIR, "frame_%04d.png"),
    "-c:v", "libopenh264",
    "-b:v", "4M",
    "-pix_fmt", "yuv420p",
    "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
    VIDEO_PATH,
]
print(f"\nEncoding {n_frames} frames -> {VIDEO_PATH}")
subprocess.run(cmd, check=True)
print(f"Done: {VIDEO_PATH}")
