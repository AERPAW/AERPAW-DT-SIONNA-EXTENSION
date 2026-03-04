import math
import os
from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class AntennaType(Enum):
    """
    Type of Antenna (transmitter and receiver)
        Used in setting arrays, transmitter/receiver characteristics
    """

    Transmitter = "tx"
    Receiver = "rx"


class RadiationPattern(Enum):
    """radiation patterns available in sionna"""

    ISO = "iso"
    DIPOLE = "dipole"
    DIRECTIONAL = "tr38901"


class PolarizationType(Enum):
    """Type of Polarization available"""

    VERTICAL = "V"
    HORIZONTAL = "H"
    CROSS = "cross"


@dataclass(frozen=True)
class CoordinateReference:
    lat: float
    lon: float
    alt: float


class CoordinateConverter:
    """WGS84 converter between geodetic (lat/lon/alt) and local ENU coordinates."""

    _WGS84_A = 6378137.0
    _WGS84_F = 1.0 / 298.257223563
    _WGS84_E2 = _WGS84_F * (2.0 - _WGS84_F)

    def __init__(self, reference: CoordinateReference):
        self.reference = reference
        self._ref_lat_rad = math.radians(reference.lat)
        self._ref_lon_rad = math.radians(reference.lon)
        self._ref_ecef = self._geodetic_to_ecef(
            reference.lat, reference.lon, reference.alt
        )

    @classmethod
    def from_env(cls) -> "CoordinateConverter":
        return cls(load_coordinate_reference_from_env())

    def lat_lon_alt_to_local(
        self, lat: float, lon: float, alt: float
    ) -> Tuple[float, float, float]:
        """Convert geodetic coordinate to local ENU tuple (x=east, y=north, z=up)."""
        x, y, z = self._geodetic_to_ecef(lat, lon, alt)
        xr, yr, zr = self._ref_ecef
        dx, dy, dz = x - xr, y - yr, z - zr

        sin_lat0 = math.sin(self._ref_lat_rad)
        cos_lat0 = math.cos(self._ref_lat_rad)
        sin_lon0 = math.sin(self._ref_lon_rad)
        cos_lon0 = math.cos(self._ref_lon_rad)

        east = -sin_lon0 * dx + cos_lon0 * dy
        north = (
            -sin_lat0 * cos_lon0 * dx
            - sin_lat0 * sin_lon0 * dy
            + cos_lat0 * dz
        )
        up = cos_lat0 * cos_lon0 * dx + cos_lat0 * sin_lon0 * dy + sin_lat0 * dz
        return (east, north, up)

    def local_to_lat_lon_alt(
        self, x: float, y: float, z: float
    ) -> Tuple[float, float, float]:
        """Convert local ENU tuple (x=east, y=north, z=up) to geodetic coordinate."""
        sin_lat0 = math.sin(self._ref_lat_rad)
        cos_lat0 = math.cos(self._ref_lat_rad)
        sin_lon0 = math.sin(self._ref_lon_rad)
        cos_lon0 = math.cos(self._ref_lon_rad)

        dx = -sin_lon0 * x - sin_lat0 * cos_lon0 * y + cos_lat0 * cos_lon0 * z
        dy = cos_lon0 * x - sin_lat0 * sin_lon0 * y + cos_lat0 * sin_lon0 * z
        dz = cos_lat0 * y + sin_lat0 * z

        xr, yr, zr = self._ref_ecef
        return self._ecef_to_geodetic(xr + dx, yr + dy, zr + dz)

    def _geodetic_to_ecef(
        self, lat_deg: float, lon_deg: float, alt: float
    ) -> Tuple[float, float, float]:
        lat = math.radians(lat_deg)
        lon = math.radians(lon_deg)
        sin_lat = math.sin(lat)
        cos_lat = math.cos(lat)
        sin_lon = math.sin(lon)
        cos_lon = math.cos(lon)

        n = self._WGS84_A / math.sqrt(1.0 - self._WGS84_E2 * sin_lat * sin_lat)
        x = (n + alt) * cos_lat * cos_lon
        y = (n + alt) * cos_lat * sin_lon
        z = (n * (1.0 - self._WGS84_E2) + alt) * sin_lat
        return (x, y, z)

    def _ecef_to_geodetic(
        self, x: float, y: float, z: float
    ) -> Tuple[float, float, float]:
        b = self._WGS84_A * (1.0 - self._WGS84_F)
        ep2 = (self._WGS84_A * self._WGS84_A - b * b) / (b * b)
        p = math.sqrt(x * x + y * y)
        lon = math.atan2(y, x)
        theta = math.atan2(z * self._WGS84_A, p * b)

        sin_theta = math.sin(theta)
        cos_theta = math.cos(theta)
        lat = math.atan2(
            z + ep2 * b * sin_theta * sin_theta * sin_theta,
            p - self._WGS84_E2 * self._WGS84_A * cos_theta * cos_theta * cos_theta,
        )

        sin_lat = math.sin(lat)
        n = self._WGS84_A / math.sqrt(1.0 - self._WGS84_E2 * sin_lat * sin_lat)
        alt = p / math.cos(lat) - n

        return (math.degrees(lat), math.degrees(lon), alt)


def load_coordinate_reference_from_env() -> CoordinateReference:
    """
    Load local-coordinate origin from environment.

    Defaults to (0, 0, 0) so conversions are deterministic even when unset.
    """

    return CoordinateReference(
        lat=float(os.getenv("SIONNA_COORD_REF_LAT", "0.0")),
        lon=float(os.getenv("SIONNA_COORD_REF_LON", "0.0")),
        alt=float(os.getenv("SIONNA_COORD_REF_ALT", "0.0")),
    )
