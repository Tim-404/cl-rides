"""Implements all the logic for the assigning drivers and riders.
Includes group optimization for common pickup locations.
"""

from cfg.config import *
import lib.postprocessing as post
import lib.preprocessing as prep
import logging
import pandas as pd


def assign(drivers_df: pd.DataFrame, riders_df: pd.DataFrame) -> pd.DataFrame:
    """Assigns rider to drivers in the returned dataframe.
    """
    riders_df.sort_values(by=RIDER_LOCATION_HDR, inplace=True, key=lambda col: col.apply(lambda loc: LOC_MAP.get(loc.strip().lower(), LOC_NONE)))
    out = pd.concat([pd.DataFrame(columns=[OUTPUT_DRIVER_NAME_HDR, OUTPUT_DRIVER_PHONE_HDR, OUTPUT_DRIVER_CAPACITY_HDR, DRIVER_GROUP_HDR]), riders_df[[RIDER_NAME_HDR, RIDER_PHONE_HDR, RIDER_LOCATION_HDR, RIDER_NOTES_HDR]]], axis='columns')

    logging.debug('assign --- Drivers')
    logging.debug(drivers_df)
    logging.debug('assign --- Riders')
    logging.debug(riders_df)
    logging.debug('assign --- Assigning started')

    # Assign drivers with preferences first
    for r_idx in out.index:
        rider_loc = LOC_MAP.get(out.at[r_idx, RIDER_LOCATION_HDR].strip().lower(), LOC_NONE)

        if rider_loc == LOC_NONE:
            continue

        # Check if a driver prefers to pick up there.
        for d_idx, driver in drivers_df.iterrows():
            if _prefers_there(drivers_df, d_idx, rider_loc):
                _add_rider(out, r_idx, drivers_df, d_idx)
                is_matched = True
                break

    for r_idx in out.index:
        # Check if already assigned to a driver with a preference
        if type(out.at[r_idx, OUTPUT_DRIVER_NAME_HDR]) is str:
            continue

        rider_loc = LOC_MAP.get(out.at[r_idx, RIDER_LOCATION_HDR].strip().lower(), LOC_NONE)

        if rider_loc == LOC_NONE:
            continue

        is_matched = False

        # Check if a driver is already there.
        for d_idx, driver in drivers_df.iterrows():
            if _is_there(drivers_df, d_idx, rider_loc):
                _add_rider(out, r_idx, drivers_df, d_idx)
                is_matched = True
                break

        if is_matched:
            continue

        # Check if there is a driver up to DISTANCE_THRESHOLD.
        for dist in range(1, ARGS[PARAM_DISTANCE] + 1):
            for d_idx, driver in drivers_df.iterrows():
                if _is_nearby_dist(drivers_df, d_idx, rider_loc, dist):
                    _add_rider(out, r_idx, drivers_df, d_idx)
                    is_matched = True
                    break

            if is_matched:
                break

        if is_matched:
            continue

        # Check if any driver is open.
        for d_idx, driver in drivers_df.iterrows():
            if _is_unused(drivers_df, d_idx):
                _add_rider(out, r_idx, drivers_df, d_idx)
                is_matched = True
                break

        if is_matched:
            continue

        # Find any driver with space and with the lightest route.
        open_driver_idx = -1
        open_driver_found = False
        for d_idx, driver in drivers_df.iterrows():
            if _has_opening(drivers_df, d_idx):
                if not open_driver_found or (_route_len(driver[DRIVER_ROUTE_HDR]) < _route_len(drivers_df.at[open_driver_idx, DRIVER_ROUTE_HDR])):
                    open_driver_idx = d_idx
                open_driver_found = True
        if open_driver_found:
            _add_rider(out, r_idx, drivers_df, open_driver_idx)
            is_matched = True

    return out


def assign_v2(drivers_df: pd.DataFrame, riders_df: pd.DataFrame, rider_map: dict[int, list[int]]) -> pd.DataFrame:
    """Assigns rider to drivers in the returned dataframe, uses a secondary map to help optimize assignments.
    """
    out = pd.concat([pd.DataFrame(columns=[OUTPUT_DRIVER_NAME_HDR, OUTPUT_DRIVER_PHONE_HDR, OUTPUT_DRIVER_CAPACITY_HDR, DRIVER_GROUP_HDR]), riders_df[[RIDER_NAME_HDR, RIDER_PHONE_HDR, RIDER_LOCATION_HDR, RIDER_NOTES_HDR]]], axis='columns')

    logging.debug('assign_v2 --- Drivers')
    logging.debug(drivers_df)
    logging.debug('assign_v2 --- Riders')
    logging.debug(riders_df)
    logging.debug('assign_v2 --- Assigning started')

    # Assign drivers with preferences first
    for d_idx in drivers_df.index:
        loc = drivers_df.at[d_idx, TMP_DRIVER_PREF_LOC]
        if loc == LOC_NONE or rider_map.get(loc, []) == []:
            continue

        while _has_opening(drivers_df, d_idx) and len(rider_map[loc]) > 0:
            r_idx = rider_map[loc].pop()
            _add_rider(out, r_idx, drivers_df, d_idx)

    # Assign cars that are partly full where leftover capacity matches location
    for dist in range(1, ARGS[PARAM_DISTANCE]):
        for d_idx in drivers_df.index:
            if not _is_unused(drivers_df, d_idx):
                continue
            if not _has_opening(drivers_df, d_idx):
                continue

            for loc in rider_map:
                is_matched = False
                if _is_nearby_dist(drivers_df, d_idx, loc, dist) and _is_matching(drivers_df, d_idx, rider_map[loc]):
                    # Assign perfect match
                    is_matched = True
                    while len(rider_map[loc]) > 0:
                        r_idx = rider_map[loc].pop()
                        _add_rider(out, r_idx, drivers_df, d_idx)
                if is_matched:
                    break

    # Assign cars that are empty where capacity matches location
    for d_idx in drivers_df.index:
        if not _is_unused(drivers_df, d_idx):
            continue
        
        # Find match with empty car
        for loc in rider_map:
            is_matched = False
            if _is_matching(drivers_df, d_idx, rider_map[loc]):
                # Assign perfect match
                is_matched = True
                while len(rider_map[loc]) > 0:
                    r_idx = rider_map[loc].pop()
                    _add_rider(out, r_idx, drivers_df, d_idx)
            if is_matched:
                break

    # Assign at locations that are greater than capacity, as long as leftover is greater than OVERFLOW_BOUND
    # Essentially, splits up riders in a single location among multiple cars
    MIN_GROUP_SZ = 2
    for d_idx in drivers_df.index:
        if not _has_opening(drivers_df, d_idx):
            continue

        for loc in rider_map:
            is_matched = False
            if len(rider_map[loc]) - drivers_df.at[d_idx, DRIVER_OPENINGS_HDR] >= MIN_GROUP_SZ:
                # Fill up car
                is_matched = True
                while len(rider_map[loc]) > 0 and _has_opening(drivers_df, d_idx):
                    r_idx = rider_map[loc].pop()
                    _add_rider(out, r_idx, drivers_df, d_idx)
            if is_matched:
                break

    # Assign cars that are empty where capacity matches location (step 3)
    for d_idx in drivers_df.index:
        if not _is_unused(drivers_df, d_idx):
            continue
        
        # Find match with empty car
        for loc in rider_map:
            is_matched = False
            if _is_matching(drivers_df, d_idx, rider_map[loc]):
                # Assign perfect match
                is_matched = True
                while len(rider_map[loc]) > 0:
                    r_idx = rider_map[loc].pop()
                    _add_rider(out, r_idx, drivers_df, d_idx)
            if is_matched:
                break

    # Assign at locations within dist
    for d_idx in drivers_df.index:
        if _is_unused(drivers_df, d_idx):
            for loc in rider_map:
                is_matched = False
                if len(rider_map[loc]) > 0:
                    is_matched = True
                    while len(rider_map[loc]) > 0 and _has_opening(drivers_df, d_idx):
                        r_idx = rider_map[loc].pop()
                        _add_rider(out, r_idx, drivers_df, d_idx)
                if is_matched:
                    break

        for dist in range(0, ARGS[PARAM_DISTANCE] + 1):
            if not _has_opening(drivers_df, d_idx):
                break

            for loc in rider_map:
                if len(rider_map[loc]) == 0:
                    continue

                oflow = len(rider_map[loc]) - drivers_df.at[d_idx, DRIVER_OPENINGS_HDR]
                if _is_nearby_dist(drivers_df, d_idx, loc, dist) and (oflow >= MIN_GROUP_SZ or oflow <= 0):
                    while len(rider_map[loc]) > 0 and _has_opening(drivers_df, d_idx):
                        r_idx = rider_map[loc].pop()
                        _add_rider(out, r_idx, drivers_df, d_idx)
                
                if not _has_opening(drivers_df, d_idx):
                    break

    # Assign remaining riders, last resort
    for loc in rider_map:
        for r_idx in rider_map[loc]:
            # Find any driver with space and with the lightest route.
            open_driver_idx = -1
            open_driver_found = False
            cost = 100 # arbitrarily high, but > MAP_WIDTH + 10 is good
            for d_idx in drivers_df.index:
                if _has_opening(drivers_df, d_idx):
                    new_cost = _route_cost(drivers_df.at[d_idx, DRIVER_ROUTE_HDR], loc)
                    if not open_driver_found or (new_cost < cost):
                        open_driver_found = True
                        open_driver_idx = d_idx
                        cost = new_cost
            if open_driver_found:
                _add_rider(out, r_idx, drivers_df, open_driver_idx)
                is_matched = True
    
    return out


def organize(drivers_df: pd.DataFrame, riders_df: pd.DataFrame) -> pd.DataFrame:
    prep.add_assignment_vars(drivers_df)
    prep.prioritize_drivers_with_preferences(drivers_df, riders_df)
    rider_map = prep.create_rider_map(riders_df)
    drivers = prep.fetch_necessary_drivers(drivers_df, len(riders_df))
    # out = assign(drivers, riders_df)
    out = assign_v2(drivers, riders_df, rider_map)
    return out


def assign_sunday(drivers_df: pd.DataFrame, riders_df: pd.DataFrame) -> pd.DataFrame:
    """Assigns Sunday rides.
    """
    (drivers, riders) = prep.filter_sunday(drivers_df, riders_df)
    (drivers1, riders1, drivers2, riders2) = prep.split_sunday_services(drivers, riders)

    assignments1 = organize(drivers1, riders1)
    assignments2 = organize(drivers2, riders2)
    out = pd.concat([assignments1, assignments2])
    post.print_unassigned_riders(out)
    post.print_unused_drivers(out, drivers)
    return out


def assign_friday(drivers_df: pd.DataFrame, riders_df: pd.DataFrame) -> pd.DataFrame:
    """Assigns Friday rides.
    """
    (drivers, riders) = prep.filter_friday(drivers_df, riders_df)
    (drivers1, riders1, drivers2, riders2) = prep.split_friday_late_cars(drivers, riders)

    assignments1 = organize(drivers1, riders1)
    assignments2 = organize(drivers2, riders2)
    out = pd.concat([assignments1, assignments2])
    post.print_unassigned_riders(out)
    post.print_unused_drivers(out, drivers)
    return out


def _add_rider(out: pd.DataFrame, r_idx: int, drivers_df: pd.DataFrame, d_idx: int):
    """Assigns rider to driver and updates driver openings and locations.
    """
    out.at[r_idx, OUTPUT_DRIVER_NAME_HDR] = drivers_df.at[d_idx, DRIVER_NAME_HDR]
    out.at[r_idx, OUTPUT_DRIVER_PHONE_HDR] = drivers_df.at[d_idx, DRIVER_PHONE_HDR]
    out.at[r_idx, OUTPUT_DRIVER_CAPACITY_HDR] = drivers_df.at[d_idx, DRIVER_CAPACITY_HDR].astype(str)
    out.at[r_idx, DRIVER_GROUP_HDR] = drivers_df.at[d_idx, DRIVER_GROUP_HDR]
    rider_loc = LOC_MAP.get(out.at[r_idx, RIDER_LOCATION_HDR].strip().lower(), LOC_NONE)
    drivers_df.at[d_idx, DRIVER_OPENINGS_HDR] -= 1
    drivers_df.at[d_idx, DRIVER_ROUTE_HDR] |= rider_loc


def _is_nearby_dist(drivers_df: pd.DataFrame, d_idx: int, rider_loc: int, dist: int) -> bool:
    """Checks if driver has no assignments or is already picking up at the same area as the rider.
    """
    return _has_opening(drivers_df, d_idx) and (_is_intersecting(drivers_df, d_idx, rider_loc << dist) or _is_intersecting(drivers_df, d_idx, rider_loc >> dist))


def _is_there(drivers_df: pd.DataFrame, d_idx: int, rider_loc: int) -> bool:
    """Checks if driver is already picking up at the same college as the rider.
    """
    return _has_opening(drivers_df, d_idx) and _is_intersecting(drivers_df, d_idx, rider_loc)


def _prefers_there(drivers_df: pd.DataFrame, d_idx: int, rider_loc: int) -> bool:
    """Checks if driver is already picking up at the same college as the rider.
    """
    return _has_opening(drivers_df, d_idx) and (drivers_df.at[d_idx, TMP_DRIVER_PREF_LOC] & rider_loc) != 0


def _is_unused(drivers_df: pd.DataFrame, d_idx: int) -> bool:
    """Checks if driver has space to take a rider.
    """
    return drivers_df.at[d_idx, DRIVER_ROUTE_HDR] == 0


def _has_opening(drivers_df: pd.DataFrame, d_idx: int) -> bool:
    """Checks if driver has space to take a rider.
    """
    return drivers_df.at[d_idx, DRIVER_OPENINGS_HDR] > 0


def _is_matching(drivers_df: pd.DataFrame, d_idx: int, rider_loc: list[int]) -> bool:
    """Checks if the spaces in a car matches the number of riders at a location.
    """
    return drivers_df.at[d_idx, DRIVER_OPENINGS_HDR] == len(rider_loc)


def _is_intersecting(drivers_df: pd.DataFrame, d_idx: int, rider_loc: int) -> bool:
    """Checks if a driver route intersects with a rider's location.
    """
    driver_loc = drivers_df.at[d_idx, DRIVER_ROUTE_HDR]
    return (driver_loc & rider_loc) != 0


def _route_cost(route: int, new_loc: int) -> int:
    return _route_len(route) + _route_dist(route, new_loc)

def _route_dist(route: int, new_loc: int) -> int:
    """Returns how far a rider is from a driver route.
    """

    # force cast numpy.int64 => int
    route = int(route)

    for dist in range(0, MAX_ROUTE_DIST):
        tmp = (new_loc << dist) | (new_loc >> dist)
        if (route & tmp) != 0:
            return dist
    return MAX_ROUTE_DIST

def _route_len(route: int) -> int:
    """Returns the number of locations a driver is picking up from.
    """
    cnt = 0
    while route != 0:
        route &= route - 1
        cnt += 1
    return cnt