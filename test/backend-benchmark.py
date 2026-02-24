import time
import random
import requests
import numpy as np
import matplotlib.pyplot as plt


BASE_URL = "http://127.0.0.1:8000"

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
    for i in range(iterations):
        setup_time = 0
        computation_time = 0
        for rx in range(num_rx):
            payload = {
                "name": f"rx{rx}",
                "position": {
                    "x": random.random() * 100,
                    "y": random.random() * 100,
                    "z": random.random() * 20 + 50
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
                    "x": random.random() * 100,
                    "y": random.random() * 100,
                    "z": random.random() * 20 + 50
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

        # Computing CIR
        response = requests.get(f"{BASE_URL}/simulation/cir")
        computation_time += response.elapsed.total_seconds()

        setup_times.append(int(setup_time * 1000))
        computation_times.append(int(computation_time * 1000))

    return np.median(setup_times), np.median(computation_times)


if __name__ == '__main__':
    # Test parameters
    n_rx = 2
    n_tx = 2
    n_samples = 100000
    depth = 2
    iter = 5
    try:
        test_add_base_devices(num_rx=n_rx, num_tx=n_tx)
    except Exception as e:
        pass

    setup_times = []
    computation_times = []
    for i in range(7):
        stime, ctime = backend_benchmark(num_rx=n_rx, 
                                        num_tx=n_tx, 
                                        num_samples=(10 ** (i + 1)), 
                                        max_depth=depth, 
                                        iterations=iter)
        setup_times.append(stime)
        computation_times.append(ctime)
    
    plt.plot(setup_times, color="blue", label="Setup Time (ms)")
    plt.plot(computation_times, color="green", label="Computation Time (ms)")
    plt.legend(loc="best")
    plt.xlabel("Log Samples")
    plt.ylabel("Time (ms)")
    plt.title(f"Response Times for {n_rx} rx, {n_tx} tx, max depth of {depth}")
    plt.show()

