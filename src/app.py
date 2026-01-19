from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status

import main
from schemas import *


"""
Add routes for removing receivers and transmitters
by their unique name

Change update routes to be more general, and allow them
to update all characteristics of a transmitter/receiver

There are currently some weird errors with adding the transmitter
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting Sionna simulation...")
    try:
        main.initialize()
    except Exception as e:
        print(f"Failed to initialize: {e}")
        raise
    yield
    print("Shutting down...")
    main.shutdown()


app = FastAPI(
    title="Sionna RT API",
    description="API for ray tracing simulation using Sionna",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/", response_model=StatusResponse, tags=["Health"])
def root():
    return StatusResponse(status="running")


@app.get("/scene", response_model=SceneInfoResponse, tags=["Scene"])
def get_scene():
    try:
        return main.get_scene_info()
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve scene info: {str(e)}",
        )


@app.post("/scene/reset", response_model=MessageResponse, tags=["Scene"])
def reset_scene():
    try:
        main.reset_scene()
        return MessageResponse(message="Scene reset successfully")
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset scene: {str(e)}",
        )


@app.post(
    "/transmitters",
    response_model=DeviceResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Transmitters"],
)
def add_tx(device: TransmitterCreate):
    """Add a new transmitter to the scene"""
    try:
        print(device.name)
        print(device.position.to_tuple())
        print(device.signal_power)
        print(device.velocity.to_tuple())
        result = main.add_transmitter(
            device.name,
            device.position.to_tuple(),
            device.signal_power,
            device.velocity.to_tuple(),
            device.orientation.to_tuple() if device.orientation else None,
        )
        return DeviceResponse(
            name=result["name"],
            position=Position.from_tuple(pos=result["position"]),
            signal_power=result["signal_power"],
            velocity=Position.from_tuple(pos=result["velocity"]),
            orientation=Position.from_tuple(result["orientation"]),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid transmitter data: {str(e)}",
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add transmitter: {str(e)}",
        )


@app.get("/transmitters", response_model=List[str], tags=["Transmitters"])
def list_tx():
    """List all transmitters in the scene"""
    try:
        return main.get_transmitters()
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve transmitters: {str(e)}",
        )


@app.put("/transmitters/{name}", response_model=DeviceResponse, tags=["Transmitters"])
def update_tx(name: str, update_data: DeviceUpdate):
    """Update transmitter position"""
    try:
        result = main.update_transmitter_position(name, update_data.position.to_tuple())
        return DeviceResponse(
            name=result["name"], position=Position.from_tuple(result["position"])
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transmitter '{name}' not found",
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update transmitter: {str(e)}",
        )


@app.post(
    "/receivers",
    response_model=DeviceResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Receivers"],
)
def add_rx(device: ReceiverCreate):
    """Add a new receiver to the scene"""
    try:
        result = main.add_receiver(
            device.name,
            device.position.to_tuple(),
            device.orientation.to_tuple() if device.orientation else None,
        )
        return DeviceResponse(
            name=result["name"],
            position=Position.from_tuple(result["position"]),
            orientation=(
                Position.from_tuple(result["orientation"])
                if result.get("orientation")
                else None
            ),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid receiver data: {str(e)}",
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add receiver: {str(e)}",
        )


@app.get("/receivers", response_model=List[str], tags=["Receivers"])
def list_rx():
    """List all receivers in the scene"""
    try:
        return main.get_receivers()
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve receivers: {str(e)}",
        )


@app.put("/receivers/{name}", response_model=DeviceResponse, tags=["Receivers"])
def update_rx(name: str, update_data: DeviceUpdate):
    """Update receiver position"""
    try:
        result = main.update_receiver_position(name, update_data.position.to_tuple())
        return DeviceResponse(
            name=result["name"], position=Position.from_tuple(result["position"])
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Receiver '{name}' not found"
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update receiver: {str(e)}",
        )


@app.post(
    "/simulation/paths", response_model=PathComputationResponse, tags=["Simulation"]
)
def compute_paths(params: PathComputationRequest):
    try:
        result = main.compute_paths(params.max_depth)
        return PathComputationResponse(
            path_count=result["path_count"], max_depth=result["max_depth"]
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid path computation parameters: {str(e)}",
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compute paths: {str(e)}",
        )



@app.get("/simulation/cir", response_model=CirResponse)
def get_cir():
    """Retrieve the Channel Impulse Response (CIR)"""
    try:
        result = main.get_cir()
        return CirResponse(
            delays=result["delays"],
            gains=CirGains(**result["gains"]),
            shape=CirShape(**result["shape"]),
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve CIR: {str(e)}",
        )
