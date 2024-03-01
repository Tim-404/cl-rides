"""
"""

import argparse
import logging
import pathlib
import sys

from .config.campus_map import CampusMap
from .config.ignore import Ignore
from .config.preferences import Preferences
from .rides import Rides


logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(module)s[%(lineno)d] - %(message)s",
    level=logging.DEBUG
)


def get_parser(
    *, distance_default: int = 2, distance_max: int = 10,
    vacancy_default: int = 2, vacancy_max: int = 10
) -> argparse.ArgumentParser:
    """
    """
    parser = argparse.ArgumentParser(
        prog=pathlib.Path(__file__).parent.name, description=__doc__,
        epilog="LBCSD | M Matthew 28:18-20 | V Acts 1:8 | P Matthew 22:37-40"
    )

    parser.add_argument(
        "day", choices=["friday", "sunday"],
        help="sets the day for rides ('friday': College Life; 'sunday': Church Service)"
    )
    parser.add_argument(
        "--service", default=2, choices=[1, 2],
        help="sets the primary Sunday Church Service (1: First Service; 2: Second Service)"
    )
    parser.add_argument(
        "--rotate", action="store_true",
        help="rotate drivers based on the date they last drove"
    )
    parser.add_argument(
        "--weekly", action="store_true",
        help="reference only weekly ride sign-ups for generating assignments"
    )
    parser.add_argument(
        "--download", action=argparse.BooleanOptionalAction, default=True,
        help="whether to download Google Sheets data"
    )
    parser.add_argument(
        "--upload", action=argparse.BooleanOptionalAction, default=True,
        help="whether to upload output to Google Sheets"
    )
    parser.add_argument(
        "--distance", type=int, default=distance_default, choices=range(1, distance_max),
        help="set the maximum distance a driver can be from a location to be considered for pickup"
    )
    parser.add_argument(
        "--vacancy", type=int, default=vacancy_default, choices=range(1, vacancy_max),
        help="set the number of open spots a driver must have to be considered for pickup"
    )
    parser.add_argument(
        "--verbosity", default="DEBUG", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="set logging verbosity"
    )

    return parser


def main():
    """
    """
    parser = get_parser()
    args = parser.parse_args()
    logging.debug(args)

    rides = Rides()
    if args["download"]:
        rides.write_cache()

    for key, value in rides.read_cache().items():
        logging.debug("%s:\n%s", key, value.to_string())

    drivers = rides.cached_input("drivers")
    if drivers.empty:
        logging.error("Empty drivers DataFrame")
        sys.exit(1)

    riders = rides.cached_input("riders")
    if riders.empty:
        logging.error("Empty riders DataFrame")
        sys.exit(1)

    campus_map = CampusMap(args["day"])
    logging.debug("Campus Locations: %s", campus_map.campus)
    logging.debug("Map Locations: %s", campus_map.locations)

    ignore = Ignore()
    logging.debug("Ignore Drivers: %s", ignore.drivers)
    logging.debug("Ignore Riders: %s", ignore.riders)

    preferences = Preferences(campus_map.locations)
    logging.debug("Driver Preferences: %s", preferences.drivers)
    logging.debug("Driver Preferences (Locations): %s", preferences.locations)
    logging.debug("Driver Preferences (Services): %s", preferences.services)
