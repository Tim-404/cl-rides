"""
"""

import csv
import pathlib
import typing

from . import DATAPATH


class Ignore:
    """
    """
    _path_drivers = DATAPATH / "ignore_drivers.txt"
    _path_riders = DATAPATH / "ignore_riders.txt"

    def __init__(
        self, *,
        path_drivers: typing.Union[str, pathlib.Path] = _path_drivers,
        path_riders: typing.Union[str, pathlib.Path] = _path_riders
    ):
        self._path_drivers = pathlib.Path(path_drivers)
        self._path_riders = pathlib.Path(path_riders)

        with open(self.path_drivers, "r", encoding="utf-8") as file:
            self._drivers = {x[0]: x[1] for x in csv.reader(file)}

        with open(self.path_riders, "r", encoding="utf-8") as file:
            self._riders = {x[0]: x[1] for x in csv.reader(file)}

    @property
    def path_drivers(self) -> pathlib.Path:
        """
        """
        return self._path_drivers

    @property
    def path_riders(self) -> pathlib.Path:
        """
        """
        return self._path_riders

    @property
    def drivers(self) -> typing.Dict[str, str]:
        """
        """
        return self._drivers

    @property
    def riders(self) -> typing.Dict[str, str]:
        """
        """
        return self._riders
