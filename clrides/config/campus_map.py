"""
"""

import pathlib
import typing

from . import DATAPATH


class CampusMap:
    """
    """
    _path_map = DATAPATH / "map.txt"
    _path_campus = DATAPATH / "campus.txt"

    def __init__(
        self, day: typing.Literal["friday", "sunday"], *,
        path_map: typing.Union[str, pathlib.Path] = _path_map,
        path_campus: typing.Union[str, pathlib.Path] = _path_campus
    ):
        self._day = day

        self._path_map = pathlib.Path(path_map)
        self._path_campus = pathlib.Path(path_campus)

        with open(self.path_campus, "r", encoding="utf-8") as file:
            self._campus = {x.strip().lower() for x in file.readlines()}

        self._locations = {}
        with open(self.path_map, "r", encoding="utf-8") as file:
            loc = 1

            for line in file.readlines():
                if line.startswith("#"):
                    continue

                for place in (x.strip().lower() for x in line.split(",")):
                    if day == "friday" and place in self.campus:
                        place = "campus"
                    self._locations.setdefault(place, 0)
                    self._locations[place] |= loc

                loc <<= 1

    @property
    def path_map(self) -> pathlib.Path:
        """
        """
        return self._path_map

    @property
    def path_campus(self) -> pathlib.Path:
        """
        """
        return self._path_campus

    @property
    def campus(self) -> typing.Set[str]:
        """
        """
        return self._campus

    @property
    def locations(self) -> typing.Dict[str, int]:
        """
        """
        return self._locations
    