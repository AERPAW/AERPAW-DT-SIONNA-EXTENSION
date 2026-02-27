from typing import Dict, List, Optional, Tuple

from sionna_wrapper import SionnaFactory
from utils import AntennaArrayType, AntennaType, PolarizationType, RadiationPattern

engine_factory = SionnaFactory()
engines = {}

"""
Eventually we're going to need the backend to be able to 
handle multiple scene instances at once. This means that 
we need to keep some state about the scene in the backend.

In that case we probably need a route to generate a new
scene, and then when we want to query any parameters from
that specific scene we provide the id of our request inside
that http request

For now though, maybe we can just make it work with a single
scene instance, so all the queries are directed to the same
scene in the Sionna backend instead of having multiple scene
instances. Maybe this framework works if we use multiple 
# instances of the engine class for each of the different scenes?

Let's try to treat instances of the Sionna class as separate
scenes, and keep some of the state inside that class
"""


"""
All of these methods should have id parameters ideally
"""

def initialize(id: Optional[int] = 0, scene_path: Optional[str] = None) -> None:
    """Initialize the simulation engine with a scene."""
    engines[id] = SionnaFactory.init_engine()


def shutdown() -> None:
    """Shutdown and clean up the simulation engines[0]."""
    engines[0].reset()


def get_scene_info() -> Dict:
    """Get information about the current scene."""
    return engines[0].get_scene_info()


def get_reference_frame() -> Dict:
    """Get information about the Sionna reference frame"""
    return engines[0].get_reference_frame()


def reset_scene() -> None:
    """Reset the scene to initial state."""
    engines[0].reset()


def add_transmitter(
    name: str,
    position: Tuple[float, float, float],
    signal_power: float,
    velocity: Optional[Tuple[float, float, float]] = (0.0, 0.0, 0.0),
    orientation: Optional[Tuple[float, float, float]] = None,
) -> Dict:
    """Add a transmitter to the scene."""
    orientation_result = engines[0].add_transmitter(name, position, signal_power, velocity, orientation)
    result = {"name": name, "position": position, "signal_power": signal_power, 
              "velocity": velocity, "orientation": orientation_result}
    return result


def update_transmitter(
    name: str, 
    position: Optional[Tuple[float, float, float]],
    signal_power: Optional[float],
    velocity: Optional[Tuple[float, float, float]],
    orientation: Optional[Tuple[float, float, float]],
) -> Dict:
    """Update the position of an existing transmitter."""
    engines[0].update_tx(name, position, signal_power, velocity, orientation)
    return {"name": name, "position": position, "signal_power": signal_power,
            "velocity": velocity, "orientation": orientation}


def get_transmitters() -> List[str]:
    """Get list of all transmitter names."""
    return list(engines[0].transmitters.keys())


def add_receiver(
    name: str,
    position: Tuple[float, float, float],
    velocity: Tuple[float, float, float],
    orientation: Optional[Tuple[float, float, float]] = None,
) -> Dict:
    """Add a receiver to the scene."""
    orientation_result = engines[0].add_receiver(name, position, velocity, orientation)
    result = {"name": name, "position": position,
              "velocity": velocity, "orientation": orientation_result}
    return result


def update_receiver(name: str, 
                    position: Tuple[float, float, float],
                    velocity: Tuple[float, float, float],
                    orientation: Tuple[float, float, float],
) -> Dict:
    """Update the position of an existing receiver."""
    engines[0].update_rx(name, position, velocity, orientation)
    return {"name": name, "position": position,
            "velocity": velocity, "orientation": orientation}


def get_receivers() -> List[str]:
    """Get list of all receiver names."""
    return list(engines[0].receivers.keys())


def set_array(
    ant_type: str,
    num_rows_cols: Tuple[int, int],
    vertical_horizontal_spacing: Tuple[float, float],
    pattern: str,
    polarization: str,
) -> Dict:
    """
    Set antenna array configuration for transmitter or receiver.

    Args:
        ant_type: Antenna type ('tx' or 'rx')
        num_rows_cols: Tuple of (num_rows, num_cols)
        vertical_horizontal_spacing: Tuple of (vertical_spacing, horizontal_spacing)
        pattern: Radiation pattern ('iso', 'dipole', or 'tr38901')
        polarization: Polarization type ('V', 'H', or 'cross')

    Returns:
        Dictionary with array configuration details
    """
    # Convert string to enum
    try:
        antenna_enum = AntennaType(ant_type)
    except ValueError:
        raise ValueError(f"Invalid antenna type: {ant_type}. Must be 'tx' or 'rx'")

    # Validate pattern
    try:
        RadiationPattern(pattern)
    except ValueError:
        raise ValueError(
            f"Invalid pattern: {pattern}. Must be 'iso', 'dipole', or 'tr38901'"
        )

    # Validate polarization
    try:
        PolarizationType(polarization)
    except ValueError:
        raise ValueError(
            f"Invalid polarization: {polarization}. Must be 'V', 'H', or 'cross'"
        )

    num_rows, num_cols = num_rows_cols
    vertical_spacing, horizontal_spacing = vertical_horizontal_spacing

    engines[0].set_array(
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


def compute_paths(max_depth: int = 3, num_samples: int = 10e5) -> Dict:
    """Compute propagation paths between transmitters and receivers."""
    return engines[0].compute_paths(max_depth, num_samples)


def get_cir() -> Dict:
    """Get the Channel Impulse Response."""
    return engines[0].get_channel_impulse_response()
