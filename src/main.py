import os
import time
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

from gpu_load_balancer import GpuLoadBalancerService
from sionna_wrapper import Sionna
from utils import (
    AntennaType,
    AntennaArrayType,
    PolarizationType,
    RadiationPattern,
)


class SceneNotFoundError(ValueError):
    """Raised when a scene id is not managed by the factory."""


class SionnaFactory:
    """Factory and registry for independent Sionna scene instances."""

    def __init__(self) -> None:
        self._instances: Dict[str, Sionna] = {}

    def create_scene(self) -> str:
        scene_id = str(uuid4())
        self._instances[scene_id] = Sionna()
        return scene_id

    def get_scene(self, scene_id: str) -> Sionna:
        engine = self._instances.get(scene_id)
        if engine is None:
            raise SceneNotFoundError(f"Scene '{scene_id}' not found")
        return engine

    def delete_scene(self, scene_id: str) -> None:
        self._instances.pop(scene_id, None)

    def shutdown(self) -> None:
        for engine in self._instances.values():
            engine.reset()
        self._instances.clear()


factory = SionnaFactory()
gpu_dispatcher: Optional[GpuLoadBalancerService] = None


def _configured_gpu_ids() -> List[str]:
    raw_gpu_ids = os.getenv("SIONNA_GPU_IDS", "0")
    parsed = [gpu.strip() for gpu in raw_gpu_ids.split(",") if gpu.strip()]
    return parsed or ["0"]


def _require_dispatcher() -> GpuLoadBalancerService:
    if gpu_dispatcher is None:
        raise RuntimeError("GPU load balancer is not initialized")
    return gpu_dispatcher


async def _dispatch(scene_id: str, fn, *args, **kwargs):
    return await _require_dispatcher().dispatch(scene_id, fn, *args, **kwargs)


async def initialize() -> None:
    """Initialize backend resources and GPU queue workers."""
    global gpu_dispatcher
    if gpu_dispatcher is not None:
        return

    gpu_dispatcher = GpuLoadBalancerService(gpu_ids=_configured_gpu_ids())
    await gpu_dispatcher.start()


async def shutdown() -> None:
    """Shutdown GPU workers and clean up all scene instances."""
    global gpu_dispatcher

    if gpu_dispatcher is not None:
        await gpu_dispatcher.shutdown()
        gpu_dispatcher = None

    factory.shutdown()


async def create_scene(scene_path: Optional[str] = None,
                       scene_origin: Optional[Dict[str, float]] = None,
                       temperature: Optional[float] = None,
                       bandwidth: Optional[float] = None,
                       tx_array: Optional[AntennaArrayType] = None,
                       rx_array: Optional[AntennaArrayType] = None) -> str:
    """Create, load, and register a new scene instance."""
    scene_id = factory.create_scene()
    engine = factory.get_scene(scene_id)
    try:
        await _dispatch(scene_id,
                        engine.initialize,
                        scene_path,
                        scene_origin,
                        temperature,
                        bandwidth,
                        tx_array,
                        rx_array)
    except Exception:
        factory.delete_scene(scene_id)
        raise
    return scene_id


async def get_scene_info(scene_id: str) -> Dict:
    """Get information about a specific scene."""
    engine = factory.get_scene(scene_id)
    return await _dispatch(scene_id, engine.get_scene_info)


async def reset_scene(scene_id: str) -> None:
    """Reset a specific scene to initial state."""
    engine = factory.get_scene(scene_id)
    await _dispatch(scene_id, engine.reset)


async def add_transmitter(
    scene_id: str,
    name: str,
    position: Tuple[float, float, float],
    signal_power: float,
    velocity: Optional[Tuple[float, float, float]] = (0.0, 0.0, 0.0),
    orientation: Optional[Tuple[float, float, float]] = None,
) -> Dict:
    """Add a transmitter to a specific scene."""
    engine = factory.get_scene(scene_id)

    def _add() -> Dict:
        orientation_result = engine.add_transmitter(name, position, signal_power,
                                                    velocity, orientation)
        return {"name": name, "position": position,
                "signal_power": signal_power, 
                "velocity": velocity, "orientation": orientation_result}

    return await _dispatch(scene_id, _add)


async def update_transmitter(
    scene_id: str, name: str, 
    position: Optional[Tuple[float, float, float]] = None,
    signal_power: Optional[float] = None,
    velocity: Optional[Tuple[float, float, float]] = None,
    orientation: Optional[Tuple[float, float, float]] = None,
) -> Dict:
    """Update the position of an existing transmitter in a scene."""
    engine = factory.get_scene(scene_id)

    def _update() -> Dict:
        engine.update_transmitter(name, position, signal_power, velocity, orientation)
        return {"name": name, "position": position,
                "signal_power": signal_power, 
                "velocity": velocity, "orientation": orientation}

    return await _dispatch(scene_id, _update)


async def get_transmitters(scene_id: str) -> List[str]:
    """Get list of all transmitter names in a scene."""
    engine = factory.get_scene(scene_id)
    return await _dispatch(scene_id, lambda: list(engine.transmitters.keys()))


async def add_receiver(
    scene_id: str,
    name: str,
    position: Tuple[float, float, float],
    velocity: Tuple[float, float, float],
    orientation: Optional[Tuple[float, float, float]] = None,
) -> Dict:
    """Add a receiver to a specific scene."""
    engine = factory.get_scene(scene_id)

    def _add() -> Dict:
        orientation_result = engine.add_receiver(name, position, velocity, orientation)
        return {"name": name, "position": position,
                "velocity": velocity, "orientation": orientation_result}

    return await _dispatch(scene_id, _add)


async def update_receiver(
    scene_id: str, name: str, 
    position: Optional[Tuple[float, float, float]] = None,
    velocity: Optional[Tuple[float, float, float]] = None,
    orientation: Optional[Tuple[float, float, float]] = None,
) -> Dict:
    """Update the position of an existing receiver in a scene."""
    engine = factory.get_scene(scene_id)

    def _update() -> Dict:
        engine.update_receiver(name, position, velocity, orientation)
        return {"name": name, "position": position,
                "velocity": velocity, "orientation": orientation}

    return await _dispatch(scene_id, _update)


async def get_receivers(scene_id: str) -> List[str]:
    """Get list of all receiver names in a scene."""
    engine = factory.get_scene(scene_id)
    return await _dispatch(scene_id, lambda: list(engine.receivers.keys()))


async def set_array(
    scene_id: str,
    ant_type: str,
    num_rows_cols: Tuple[int, int],
    vertical_horizontal_spacing: Tuple[float, float],
    pattern: str,
    polarization: str,
) -> Dict:
    """
    Set antenna array configuration for transmitter or receiver.

    Args:
        scene_id: Unique scene identifier.
        ant_type: Antenna type ('tx' or 'rx')
        num_rows_cols: Tuple of (num_rows, num_cols)
        vertical_horizontal_spacing: Tuple of (vertical_spacing, horizontal_spacing)
        pattern: Radiation pattern ('iso', 'dipole', or 'tr38901')
        polarization: Polarization type ('V', 'H', or 'cross')

    Returns:
        Dictionary with array configuration details
    """
    try:
        antenna_enum = AntennaType(ant_type)
    except ValueError:
        raise ValueError(f"Invalid antenna type: {ant_type}. Must be 'tx' or 'rx'")

    try:
        RadiationPattern(pattern)
    except ValueError:
        raise ValueError(
            f"Invalid pattern: {pattern}. Must be 'iso', 'dipole', or 'tr38901'"
        )

    try:
        PolarizationType(polarization)
    except ValueError:
        raise ValueError(
            f"Invalid polarization: {polarization}. Must be 'V', 'H', or 'cross'"
        )

    num_rows, num_cols = num_rows_cols
    vertical_spacing, horizontal_spacing = vertical_horizontal_spacing
    engine = factory.get_scene(scene_id)

    await _dispatch(
        scene_id,
        engine.set_array,
        antenna_enum,
        num_rows,
        num_cols,
        vertical_spacing,
        horizontal_spacing,
        pattern,
        polarization,
    )

    return {
        "antenna_type": ant_type,
        "num_rows": num_rows,
        "num_cols": num_cols,
        "vertical_spacing": vertical_spacing,
        "horizontal_spacing": horizontal_spacing,
        "pattern": pattern,
        "polarization": polarization,
    }


async def compute_paths(scene_id: str, max_depth: int = 3, num_samples: int = 1e5) -> Dict:
    """Compute propagation paths between transmitters and receivers in a scene."""
    engine = factory.get_scene(scene_id)
    start = time.time()
    result = await _dispatch(scene_id, engine.compute_paths, max_depth, num_samples)
    end = time.time()
    result["computation_time"] = int((end - start) * 1000)
    return result


async def get_cir(scene_id: str) -> Dict:
    """Get the Channel Impulse Response for a scene."""
    engine = factory.get_scene(scene_id)
    start = time.time()
    result = await _dispatch(scene_id, engine.get_channel_impulse_response)
    end = time.time()
    result["computation_time"] = int((end - start) * 1000)
    return result
