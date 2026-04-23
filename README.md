# aerpaw_sionna_test

## Deploy/Refresh on AERPAW Server
This container was specifically designed to run on the AERPAW Servers and communicate with AERPAW's Channel Emulator (CHEM) through an AD interface.

To set up this repository on an AERPAW server, or refresh it from this index, follow these steps:
1. Ensure you have git large file storage by running `git lfs install`
2. Clone the main branch of the repository
3. Run the start script `./start.sh`. This will automatically set up the AD interface and spin up the docker container
4. By default, this deploys on the Lake Wheeler environment described by `lake-wheeler-scene.xml` and the referenced meshes

## GPU Run (Proper Sionna Scene)

The default scene path in compose points to Sionna's built-in Munich scene:

- `/usr/local/lib/python3.11/dist-packages/sionna/rt/scenes/munich/munich.xml`

Start with GPU enabled:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build -d
```

Run latency benchmark:

```bash
docker compose exec -T sionna-api python /app/test/gpu_latency_benchmark.py \
  --iterations 20 \
  --max-depth 3 \
  --num-samples 100000
```

Optional custom scene:

```bash
docker compose exec -T sionna-api python /app/test/gpu_latency_benchmark.py \
  --scene-path /path/to/scene.xml
```

## Bare-Metal GPU Run

Start API on host GPU:

```bash
./scripts/run_baremetal_gpu.sh
```

In another terminal, run benchmark:

```bash
./scripts/bench_latency.sh
```
