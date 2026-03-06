import time
import random
import requests
import numpy as np
import matplotlib.pyplot as plt


BASE_URL = "http://127.0.0.1:8000"
ORIGIN_SCENE = [2021, 1974, 123]  # Relative position of LW1


def test_running():
    response = requests.get(f"{BASE_URL}/")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"


def test_add_base_devices(num_rx, num_tx):
    # Adding base transmitters and receivers
    for rx in range(num_rx):
        payload = {
            "name": f"rx{rx}",
            "position": {
                "x": 0.0,
                "y": 0.0,
                "z": 0.0
            },
            "velocity": {
                "x": 0.0,
                "y": 0.0,
                "z": 0.0
            }
        }
        response = requests.post(f"{BASE_URL}/receivers", json=payload)
        assert response.status_code == 201

    for tx in range(num_tx):
        payload = {
            "name": f"tx{tx}",
            "position": {
                "x": 0.0,
                "y": 0.0,
                "z": 0.0
            },
            "velocity": {
                "x": 0.0,
                "y": 0.0,
                "z": 0.0
            },
            "signal_power": 2.0
        }
        requests.post(f"{BASE_URL}/transmitters", json=payload)
        assert response.status_code == 201


def backend_benchmark(num_rx, num_tx, num_samples, max_depth, iterations):
    # Testing the process of RX+TX movement / CIR query

    setup_times = []
    computation_times = []
    num_paths = []
    for i in range(iterations):
        setup_time = 0
        computation_time = 0
        for rx in range(num_rx):
            payload = {
                "name": f"rx{rx}",
                "position": {
                    "x": ORIGIN_SCENE[0] + random.random() * 100,
                    "y": ORIGIN_SCENE[1] + random.random() * 100,
                    "z": ORIGIN_SCENE[2] + random.random() * 20
                },
                "velocity": {
                    "x": 0,
                    "y": 0,
                    "z": 0
                },
                "orientation": {
                    "x": 0.0,
                    "y": 0.0,
                    "z": 0.0
                }
            }
            response = requests.put(f"{BASE_URL}/receivers/rx{rx}", json=payload)
            setup_time += response.elapsed.total_seconds()
        
        for tx in range(num_tx):
            payload = {
                "name": f"tx{tx}",
                "position": {
                    "x": ORIGIN_SCENE[0] + random.random() * 100,
                    "y": ORIGIN_SCENE[1] + random.random() * 100,
                    "z": ORIGIN_SCENE[2] + random.random() * 20
                },
                "velocity": {
                    "x": 0,
                    "y": 0,
                    "z": 0
                }
            }
            response = requests.put(f"{BASE_URL}/transmitters/tx{tx}", json=payload)
            setup_time += response.elapsed.total_seconds()
        
        # Computing Paths
        payload = {
            "max_depth": max_depth,
            "num_samples": num_samples
        }
        response = requests.post(f"{BASE_URL}/simulation/paths", json=payload)
        computation_time += response.elapsed.total_seconds()
        num_paths.append(response.json()["path_count"])

        # Computing CIR
        response = requests.get(f"{BASE_URL}/simulation/cir")
        computation_time += response.elapsed.total_seconds()

        setup_times.append(int(setup_time * 1000))
        computation_times.append(int(computation_time * 1000))

    return computation_times, num_paths


if __name__ == '__main__':
    # Test parameters
    n_rx = 5
    n_tx = 5
    depth = 3
    iter = 20
    try:
        test_add_base_devices(num_rx=n_rx, num_tx=n_tx)
    except Exception as e:
        pass

    # We max out at 10^7 samples
    total_paths = []
    computation_times = []
    for i in range(6):
        ctime, num_paths = backend_benchmark(num_rx=n_rx, 
                                        num_tx=n_tx, 
                                        num_samples=(10 ** (i + 1)), 
                                        max_depth=depth, 
                                        iterations=iter)
        computation_times.append(ctime)
        total_paths.append(num_paths)
    
    fig, axs = plt.subplots(1, 3, figsize=(12, 4))

    bp0 = axs[0].boxplot(computation_times, label="Computation Time (ms)")
    for median in bp0['medians']:
        x = median.get_xdata()
        y = median.get_ydata()[0]
        axs[0].text(np.mean(x), y, f'{y:.0f}', fontsize=6,
                ha='left', va='center', 
                color='white', fontweight='bold', 
                bbox=dict(facecolor='red', edgecolor='none', boxstyle='round'))
    axs[0].legend(loc="best")
    axs[0].set_xlabel("Log Samples")
    axs[0].set_ylabel("Time (ms)")

    bp1 = axs[1].boxplot(total_paths, label="Path Count")
    for median in bp1['medians']:
        x = median.get_xdata()
        y = median.get_ydata()[0]
        axs[1].text(np.mean(x), y, f'{y:.0f}', fontsize=6,
                ha='left', va='center', 
                color='white', fontweight='bold', 
                bbox=dict(facecolor='red', edgecolor='none', boxstyle='round'))
    axs[1].legend(loc="best")
    axs[1].set_xlabel("Log Samples")
    axs[1].set_ylabel("Path Count")
    plt.title(f"Data for {iter} iterations, {n_rx} rx, {n_tx} tx, max depth of {depth}", loc="center")

    gpu_memory = [1128, 1128, 1128, 1128, 1160, 1418]
    gpu_memory_3x3 = [1160, 1160, 1160, 1162, 1226, 1546]
    gpu_memory_depth3 = [1128, 1128, 1128, 1194, 1484, 1612]
    gpu_memory_5x5 = [1192, 1192, 1194, 1196, 1324, 2572]
    axs[2].plot(range(1, 7), gpu_memory_5x5, color="green", label="GPU Memory (Mbs)")
    axs[2].set_xlabel("Log Samples")
    axs[2].set_ylabel("GPU Memory (Mbs)")
    axs[2].legend(loc="best")

    plt.show()

