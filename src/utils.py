from enum import Enum
from typing import Dict, Final, List, Optional, Tuple

import numpy as np
from pyproj import Transformer
from pyproj.enums import TransformDirection
from sionna.rt import PlanarArray

# Default geo origin (deg/deg/m HAE). The altitude is the HAE that maps to
# scene z=0 (ground)
ORIGIN_LAT_LON: Final[Dict[str, float]] = {
    "lat": 35.72750947,
    "lon": -78.69595819,
    "alt": 112.0,
}
# Default scene XYZ offset (scene units) applied after the ENU -> scale step.
SIONNA_OFFSET: Final[List[float]] = [118.1, -123.4, 0.0]
SIONNA_SCALE: Final[float] = 1.0


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


class AntennaArrayType:
    def __init__(
        self,
        antenna_type: AntennaType,
        num_rows: Optional[int] = None,
        num_cols: Optional[int] = None,
        h_space: Optional[float] = None,
        v_space: Optional[float] = None,
        pattern: Optional[RadiationPattern] = None,
        polarization: Optional[PolarizationType] = None,
        planar_array: Optional[PlanarArray] = None,
    ):
        self.antenna_type = antenna_type
        if planar_array is None:
            self.planar_array = PlanarArray(
                num_rows=num_rows,
                num_cols=num_cols,
                horizontal_spacing=h_space,
                vertical_spacing=v_space,
                pattern=pattern.value,
                polarization=polarization.value,
            )
        else:
            self.planar_array = planar_array

    def to_sionna(self):
        return self.planar_array

    @classmethod
    def from_sionna(cls, antenna_type: str, planar_array: PlanarArray):
        return AntennaArrayType(
            antenna_type=AntennaType.to_enum(s=antenna_type), planar_array=planar_array
        )


class CoordinateConverter:
    """Geodetic (lat/lon/alt) <-> local Sionna scene coordinates.
    """

    def __init__(
        self,
        reference_origin: Optional[Dict[str, float]] = None,
        offset: Optional[List[float]] = None,
        scale: float = SIONNA_SCALE,
    ):
        self.origin = reference_origin or ORIGIN_LAT_LON
        self.offset = np.asarray(
            offset if offset is not None else SIONNA_OFFSET, dtype=float
        )
        self.scale = float(scale)
        self._build_transformer()

    def _build_transformer(self) -> None:
        pipeline = (
            f"+proj=pipeline "
            f"+step +proj=unitconvert +xy_in=deg +z_in=m +xy_out=rad +z_out=m "
            f"+step +proj=cart +ellps=WGS84 "
            f"+step +proj=topocentric +ellps=WGS84 "
            f"+lon_0={self.origin['lon']} +lat_0={self.origin['lat']} +h_0={self.origin['alt']}"
        )
        self.transformer = Transformer.from_pipeline(pipeline)

    def update_reference_origin(self, origin: Dict[str, float]) -> Dict[str, float]:
        self.origin = origin
        self._build_transformer()
        return self.origin

    def get_origin(self) -> Dict[str, float]:
        return self.origin

    def get_offset(self) -> List[float]:
        return self.offset.tolist()

    def get_scale(self) -> float:
        return self.scale

    def lat_lon_alt_to_local(
        self, lat: float, lon: float, alt: float
    ) -> Tuple[float, float, float]:
        """Convert geodetic coordinate to local scene (x=east, y=north, z=up)."""
        east, north, up = self.transformer.transform(
            lon, lat, alt, direction=TransformDirection.FORWARD
        )
        x = east * self.scale + self.offset[0]
        y = north * self.scale + self.offset[1]
        z = up * self.scale + self.offset[2]
        return (float(x), float(y), float(z))

    def local_to_lat_lon_alt(
        self, x: float, y: float, z: float
    ) -> Tuple[float, float, float]:
        east = (x - self.offset[0]) / self.scale
        north = (y - self.offset[1]) / self.scale
        up = (z - self.offset[2]) / self.scale
        lon, lat, alt = self.transformer.transform(
            east, north, up, direction=TransformDirection.INVERSE
        )
        return (lat, lon, alt)
