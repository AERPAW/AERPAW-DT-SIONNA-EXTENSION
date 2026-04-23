# aerpaw_sionna_test

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
