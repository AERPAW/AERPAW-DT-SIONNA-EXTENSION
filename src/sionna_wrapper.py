from typing import Dict, Optional, Tuple, Final

from utils import AntennaType, AntennaArrayType, RadiationPattern, PolarizationType

# Imports for the default scene object
import sys
sys.path.append("..")

try:
    import sionna.rt
    import mitsuba as mi
except ImportError as e:
    import os

    os.system("pip install sionna-rt")
    import sionna.rt

# Other imports
# %matplotlib inline
import matplotlib.pyplot as plt
import numpy as np

no_preview = True  # Toggle to False to use the preview widget

# Default values for scene parameters
SCENE: Final[str] = "../data/scenes/lake-wheeler-trees-segmented.xml"
TEMPERATURE: Final[float] = 300.0  # Temperaure in Kelvin
BANDWIDTH: Final[float] = 30.0  # Bandwidth in MHz
TX_ARRAY: Final[AntennaArrayType] = AntennaArrayType(AntennaType.Transmitter, 1, 1, 0.0, 0.0, RadiationPattern.ISO, PolarizationType.VERTICAL)
RX_ARRAY: Final[AntennaArrayType] = AntennaArrayType(AntennaType.Receiver, 1, 1, 0.0, 0.0, RadiationPattern.ISO, PolarizationType.VERTICAL)


# Import relevant components from Sionna RT
from sionna.rt import (
    Camera,
    PathSolver,
    PlanarArray,
    RadioMapSolver,
    Receiver,
    Transmitter,
    load_scene,
    subcarrier_frequencies,
)


class Sionna:
    """
    Let each instance of this class represent a separate
    scene in the backend.
    These should be created by an API route, and then queried
    based on some unique scene id by a multithreaded backend
    """
    def __init__(self, 
                 temperature: Optional[float] = TEMPERATURE,
                 bandwidth: Optional[float] = BANDWIDTH,
                 tx_array: Optional[AntennaArrayType] = TX_ARRAY,
                 rx_array: Optional[AntennaArrayType] = RX_ARRAY,
                 ):
        # Using hardcoded scene because there's only one Lake Wheeler Environment
        self.scene = load_scene(SCENE)

        # These parameters are stored inside the Sionna scene
        self.scene.temperature = temperature  # For thermal noise power
        self.scene.bandwidth = bandwidth  # For thermal noise power
        self.scene.tx_array = tx_array.planar_array
        self.scene.rx_array = rx_array.planar_array
        self.transmitters: Dict[str, sionna.rt.Transmitter] = {}
        self.receivers: Dict[str, sionna.rt.Receiver] = {}
        self._path_solver = None
        self._computed_paths = None

    def get_scene_info(self):
        if not self.scene:
            raise RuntimeError("No scene loaded")
        return {
            "object_count": len(self.scene.objects),
            "objects": list(self.scene.objects.keys()),
            "transmitter_count": len(self.transmitters),
            "receiver_count": len(self.receivers),
            "temperature": self.scene.temperature,
        }

    def add_transmitter(
        self,
        name: str,
        position: Tuple[float, float, float],
        signal_power: float,
        velocity: Optional[Tuple[float, float, float]] = (0, 0, 0),
        orientation: Tuple[float, float, float] = None,
    ) -> Tuple[Tuple[float, float, float], AntennaArrayType]:
        if not self.scene:
            raise RuntimeError("Scene not loaded")
        
        tx = sionna.rt.Transmitter(name=name, position=position, 
                                   power_dbm=signal_power, velocity=velocity)

        # Setting orientation
        if orientation is None:
            tx.look_at((position[0], position[1], position[2] - 1))  # Look down
        else:
            tx.orientation = mi.Point3f(orientation[0], orientation[1], orientation[2])

        self.scene.add(tx)
        self.transmitters[name] = tx

        o = tx.orientation
        return (o.x, o.y, o.z)


    def add_receiver(
        self,
        name: str,
        position: Tuple[float, float, float],
        orientation: Optional[Tuple[float, float, float]] = None,
    ) -> None:
        """Add a receiver to the scene."""
        if not self.scene:
            raise RuntimeError("Scene not loaded")

        if not self.scene.rx_array:
            print("Rx array not defined. Setting to default")
            self.set_array(AntennaType.Receiver)

        rx = sionna.rt.Receiver(name=name, position=position)
        if orientation:
            rx.orientation = orientation

        self.scene.add(rx)
        self.receivers[name] = rx

    def set_array(
        self,
        ant_type: AntennaType,
        num_rows: int = 1,
        num_cols: int = 1,
        vertical_spacing: float = 1.0,
        horizontal_spacing: float = 1.0,
        pattern: str = "tr38901",
        polarization: str = "V",
    ) -> None:
        """Sets antenna array"""
        if not self.scene:
            raise RuntimeError("Scene not loaded")

        if ant_type == AntennaType.Transmitter:
            self.scene.tx_array = PlanarArray(
                num_rows=num_rows,
                num_cols=num_cols,
                vertical_spacing=vertical_spacing,
                horizontal_spacing=horizontal_spacing,
                pattern=pattern,
                polarization=polarization,
            )
        elif ant_type == AntennaType.Receiver:
            self.scene.rx_array = PlanarArray(
                num_rows=num_rows,
                num_cols=num_cols,
                vertical_spacing=vertical_spacing,
                horizontal_spacing=horizontal_spacing,
                pattern=pattern,
                polarization=polarization,
            )

    def update_ant_position(
        self, ant_type: AntennaType, name: str, position: Tuple[float, float, float]
    ) -> None:
        """Update transmitter position."""

        if ant_type == AntennaType.Transmitter:
            if name not in self.transmitters:
                raise ValueError(f"Transmitter '{name}' not found")

            self.transmitters[name].position = position
        elif ant_type == AntennaType.Receiver:
            if name not in self.receivers:
                raise ValueError(f"Receiver '{name}' not found")

            self.receivers[name].position = position
        else:
            raise RuntimeError("Invalid Antenna Type")

    def compute_paths(self, max_depth: int = 3) -> Dict:
        """Compute propagation paths between transmitters and receivers."""
        if not self.scene:
            raise RuntimeError("Scene not loaded")

        if not self.transmitters or not self.receivers:
            raise RuntimeError("No transmitters or receivers in scene")

        # Initialize path solver
        self._path_solver = sionna.rt.PathSolver()

        # Compute paths
        self._computed_paths = self._path_solver(scene=self.scene, max_depth=max_depth)

        path_count = 0
        if (
            hasattr(self._computed_paths, "vertices")
            and self._computed_paths.vertices is not None
        ):
            # vertices shape is typically [batch, num_rx, num_tx, max_paths, max_depth, 3]
            path_count = int(np.prod(self._computed_paths.vertices.shape[:4]))

        return {
            "path_count": path_count,
            "max_depth": max_depth,
        }


    def get_channel_impulse_response(self) -> Dict:
        """Return Channel Impulse Response (CIR) from computed paths."""

        try:
            # Use the Paths.cir() method to get channel impulse response
            # Returns (a, tau) where:
            # a: complex path coefficients [num_rx, num_rx_ant, num_tx, num_tx_ant, num_paths, num_time_steps]
            # tau: path delays [num_rx, num_rx_ant, num_tx, num_tx_ant, num_paths]

            a, tau = self._computed_paths.cir(
                normalize_delays=True,  # Normalize first path to zero delay
                out_type="numpy",  # Get numpy arrays
            )

            # Convert to nested lists for JSON serialization
            delays = tau.tolist()

            # Handle complex gains - separate real and imaginary parts
            gains = {
                "real": a.real.tolist(),
                "imag": a.imag.tolist(),
                "magnitude": np.abs(a).tolist(),
                "phase": np.angle(a).tolist(),
            }

            # Also provide shape information for easier parsing
            return {
                "delays": delays,
                "gains": gains,
                "shape": {
                    "num_rx": int(a.shape[0]),
                    "num_rx_ant": int(a.shape[1]),
                    "num_tx": int(a.shape[2]),
                    "num_tx_ant": int(a.shape[3]),
                    "num_paths": int(a.shape[4]),
                    "num_time_steps": int(a.shape[5]),
                },
            }
        except Exception as e:
            import traceback

            raise RuntimeError(f"Failed to extract CIR: {e}\n{traceback.format_exc()}")


    def reset(self) -> None:
        """Reset the simulation state."""
        self.transmitters.clear()
        self.receivers.clear()
        self._path_solver = None
        self._computed_paths = None


class SionnaFactory():
    """
    Factory class for producing multiple Sionna
    engine instances
    """

    @classmethod
    def init_engine(cls, 
                    temperature: Optional[float] = TEMPERATURE,
                    bandwidth: Optional[float] = BANDWIDTH,
                    tx_array: Optional[AntennaArrayType] = TX_ARRAY,
                    rx_array: Optional[AntennaArrayType] = RX_ARRAY,
                    ):
        return Sionna(temperature=temperature, 
                      bandwidth=bandwidth, 
                      tx_array=tx_array, 
                      rx_array=rx_array)
