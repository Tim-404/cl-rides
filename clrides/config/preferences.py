"""
"""

import csv
import pathlib
import typing

from . import DATAPATH
from .campus_map import CampusMap


CAMPUS_MAP = CampusMap()


class Preferences:
    """
    """
    _path_drivers = DATAPATH / "driver_preferences.csv"

    _preference_keys = ("phone", "location", "service")

    def __init__(
        self, locations: typing.Dict[str, int],
        *, path_drivers: typing.Union[str, pathlib.Path] = _path_drivers
    ):
        self._path_drivers = pathlib.Path(path_drivers)

        self._campus_map = CampusMap()

        with open(self.path_drivers, "r", encoding="utf-8") as file:
            self._drivers = {
                x[0]: dict(zip(self._preference_keys, x[1:])) for x in csv.reader(file)
            }

        self._locations = {
            v["phone"]: locations.get(v["loc"], 0) for v in self.drivers.values()
        }
        self._services = {
            v["phone"]: v["service"] for v in self.drivers.values()
        }

    @property
    def path_drivers(self) -> pathlib.Path:
        """
        """
        return self._path_drivers

    @property
    def drivers(self) -> typing.Dict[str, typing.Dict[str, str]]:
        """
        """
        return self._drivers

    @property
    def locations(self) -> typing.Dict[str, str]:
        """
        """
        return self._locations

    @property
    def services(self) -> typing.Dict[str, str]:
        """
        """
        return self._services
