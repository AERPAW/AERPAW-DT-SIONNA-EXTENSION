"""
This testing script should be run locally from inside the aerpaw33 server
When running, make sure that the port 8000 is exposed in the docker compose
Otherwise, you'll get connection refused errors
"""

import requests

BASE_URL = "http://127.0.0.1:8000"

# Creating a scene
res = requests.post(f"{BASE_URL}/scenes")
data = res.json()
scene_id = data["scene_id"]
print(f"Scene Created with ID: {scene_id}")

# Getting the scene information
res = requests.get(f"{BASE_URL}/scenes/{scene_id}")
data = res.json()
origin = data["coordinate_reference"]
print(f"Using origin: {origin}")

# Creating a transmitter and receiver
transmitter_payload = {
    "name": "tx",
    "position": {
        "lat": origin["lat"],
        "lon": origin["lon"],
        "alt": origin["alt"]
    },
    "signal_power": 2.0
}

tx_res = requests.post(f"{BASE_URL}/scenes/{scene_id}/transmitters", json=transmitter_payload)
assert tx_res.status_code == 201

print(tx_res.json())

# Creating 4 receivers with slight variations in lat/lon
lat_lon_diff = [
    [0.0005, 0.0005], 
    [0.0005, -0.0005], 
    [-0.0005, 0.0005], 
    [-0.0005, -0.0005]
]

for i, diff in enumerate(lat_lon_diff):
    receiver_payload = {
        "name": f"rx_{i}",
        "position": {
            "lat": origin["lat"] + diff[0],
            "lon": origin["lon"] + diff[1],
            "alt": origin["alt"] - 30  # 30 meters under the transmitter
        }
    }

    rx_res = requests.post(f"{BASE_URL}/scenes/{scene_id}/receivers", json=receiver_payload)
    assert rx_res.status_code == 201
    print(f"Successfully created RX at: {rx_res.json()['position']}")

# Querying paths, should output a render
request_params = {
    "max_depth": 2,
    "num_samples": 10000
}
path_res = requests.post(f"{BASE_URL}/scenes/{scene_id}/simulation/paths", json=request_params)
print(path_res.json())
