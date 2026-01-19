from sionna.rt import PlanarArray
from typing import Optional
from enum import Enum


class AntennaType(Enum):
    """
    Type of Antenna (transmitter and receiver)
        Used in setting arrays, transmitter/receiver characteristics
    """

    Transmitter = "tx"
    Receiver = "rx"

    @classmethod
    def to_enum(cls, s: str):
        if s == "tx":
            return AntennaType.Transmitter
        elif s == "rx":
            return AntennaType.Receiver
        else:
            raise Exception(f"Invalid input for Antenna {s}, must be 'tx' or 'rx")


class RadiationPattern(Enum):
    """radiation patterns available in sionna"""

    ISO = "iso"
    DIPOLE = "dipole"
    DIRECTIONAL = "tr38901"


class PolarizationType(Enum):
    """Type of Polarization available"""

    VERTICAL = "V"
    HORIZONTAL = "H"
    SLANT = "VH"
    CROSS = "cross"


class AntennaArrayType():
    def __init__(self, 
                 antenna_type: AntennaType, 
                 num_rows: Optional[int] = None, 
                 num_cols: Optional[int] = None, 
                 h_space: Optional[float] = None, 
                 v_space: Optional[float] = None, 
                 pattern: Optional[RadiationPattern] = None, 
                 polarization: Optional[PolarizationType] = None,
                 planar_array: Optional[PlanarArray] = None):
        self.antenna_type = antenna_type
        if planar_array is None:
            self.planar_array = PlanarArray(num_rows=num_rows, num_cols=num_cols,
                                            horizontal_spacing=h_space,
                                            vertical_spacing=v_space,
                                            pattern=pattern.value,
                                            polarization=polarization.value)
        else:
            self.planar_array = planar_array
        

    def to_sionna(self):
        return self.planar_array


    @classmethod
    def from_sionna(cls, antenna_type: str, planar_array: PlanarArray):
        return AntennaArrayType(antenna_type=AntennaType.to_enum(s=antenna_type), 
                                planar_array=planar_array)
    

