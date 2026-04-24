#!/bin/bash

IP_ADDRESS=192.168.60.105/20

# Ensuring OVS and NIC are active
sudo ip link set br-AD up
sudo ip link set enp23s0f0 up

# Starting the container and waiting
sudo docker compose up -d --build --force-recreate
sleep 3

# Removing any old links
sudo ovs-docker del-port br-AD eth-AD-srv aerpaw-sionna-api 2>/dev/null

# Injecting the new OVS interface
sudo ovs-docker add-port br-AD eth-AD-srv aerpaw-sionna-api --ipaddress=$IP_ADDRESS

echo "Container started on $IP_ADDRESS"
