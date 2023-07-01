"""Implements all the logic for the assigning drivers and riders.
Includes group optimization for common pickup locations.
"""

from cfg.config import *
import lib.postprocessing as post
import lib.preprocessing as prep
from lib.rides_data import *
import pandas as pd


def assign(drivers_df: pd.DataFrame, riders_df: pd.DataFrame, debug: bool = True) -> pd.DataFrame:
    """Assigns rider to drivers in the returned dataframe, and updates driver timestamp for the last time they drove.

    PRECONDITION: add_temporaries must have been called on drivers_df.
    """
    riders_df.sort_values(by=RIDER_LOCATION_KEY, inplace=True, key=lambda col: col.apply(lambda loc: loc_map.get(loc, loc_map[ELSEWHERE])))
    out = pd.concat([pd.DataFrame(columns=[OUTPUT_DRIVER_NAME_KEY, OUTPUT_DRIVER_PHONE_KEY, OUTPUT_DRIVER_CAPACITY_KEY]), riders_df[[RIDER_NAME_KEY, RIDER_PHONE_KEY, RIDER_LOCATION_KEY, RIDER_NOTES_KEY]]], axis='columns')

    print("riders_df")
    print(riders_df)

    print("drivers_df")
    print(drivers_df)

    print('Out')
    print(out)

    if debug:
        print('Drivers')
        print(drivers_df)
        print('Riders')
        print(riders_df)
        print('Assigning started')

    for r_idx in out.index:
        rider_loc = loc_map.get(out.at[r_idx, RIDER_LOCATION_KEY], loc_map[ELSEWHERE])

        if rider_loc == loc_map[ELSEWHERE]:
            #TODO: do not assign for now
            if debug:
                print(f'\t{out.at[r_idx, RIDER_NAME_KEY]} is not from a prerecorded location, assigning skipped')
            continue

        is_matched = False

        # Check if a driver is already there.
        for d_idx, driver in drivers_df.iterrows():
            if _is_there_or_open(driver, rider_loc):
                _add_rider(out, r_idx, drivers_df, d_idx)
                is_matched = True
                break
            if _is_nearby_dist(driver, rider_loc, 1) and driver[DRIVER_OPENINGS_KEY] >= GLOBALS[GROUPING_THRESHOLD]:
                # If a driver is one spot away and are not going "out of their way", that driver will get assigned.
                _add_rider(out, r_idx, drivers_df, d_idx)
                is_matched = True
                break

        if is_matched:
            continue

        # Check if a driver route is one place away.
        for d_idx, driver in drivers_df.iterrows():
            if _is_nearby_dist(driver, rider_loc, 1):
                _add_rider(out, r_idx, drivers_df, d_idx)
                is_matched = True
                break

        if is_matched:
            continue

        # Check if a driver route is two places away.
        for d_idx, driver in drivers_df.iterrows():
            if _is_nearby_dist(driver, rider_loc, 2):
                _add_rider(out, r_idx, drivers_df, d_idx)
                is_matched = True
                break

        if is_matched:
            continue

        # Check if any driver is available.
        for d_idx, driver in drivers_df.iterrows():
            if _has_opening(driver):
                _add_rider(out, r_idx, drivers_df, d_idx)
                is_matched = True
                break

    print("out return val")
    print(out)

    return out


def organize(drivers_df: pd.DataFrame, riders_df: pd.DataFrame, debug: bool) -> pd.DataFrame:
    drivers = prep.prep_necessary_drivers(drivers_df, len(riders_df))
    out = assign(drivers, riders_df, True) # FIXME: temp debug
    post.alert_skipped_riders(out, debug)
    post.clean_output(out)
    if debug:
        print('Assigned Drivers')
        print(drivers)
    return out


def assign_sunday(drivers_df: pd.DataFrame, riders_df: pd.DataFrame, debug: bool) -> pd.DataFrame:
    """Assigns Sunday rides.
    """
    riders = prep.filter_sunday(riders_df)
    return organize(drivers_df, riders, debug)


def assign_friday(drivers_df: pd.DataFrame, riders_df: pd.DataFrame, debug: bool) -> pd.DataFrame:
    """Assigns Friday rides.
    """
    riders = prep.filter_friday(riders_df)
    return organize(drivers_df, riders, debug)


def _add_rider(out: pd.DataFrame, r_idx: int, drivers_df: pd.DataFrame, d_idx: int):
    """Assigns rider to driver and updates driver openings and locations.
    """
    out.at[r_idx, OUTPUT_DRIVER_NAME_KEY] = drivers_df.at[d_idx, DRIVER_NAME_KEY]
    out.at[r_idx, OUTPUT_DRIVER_PHONE_KEY] = drivers_df.at[d_idx, DRIVER_PHONE_KEY]
    out.at[r_idx, OUTPUT_DRIVER_CAPACITY_KEY] = '' #int(drivers_df.at[d_idx, DRIVER_CAPACITY_KEY])  # Chose not to include total seats
    rider_loc = loc_map.get(out.at[r_idx, RIDER_LOCATION_KEY], loc_map[ELSEWHERE])
    drivers_df.at[d_idx, DRIVER_OPENINGS_KEY] -= 1
    drivers_df.at[d_idx, DRIVER_ROUTE_KEY] |= rider_loc


def _is_nearby_dist(driver: pd.Series, rider_loc: int, dist: int) -> bool:
    """Checks if driver has no assignments or is already picking up at the same area as the rider.
    """
    return _has_opening(driver) and (_is_free(driver) or _is_intersecting(driver, rider_loc << dist) or _is_intersecting(driver, rider_loc >> dist))


def _is_there_or_open(driver: pd.Series, rider_loc: int) -> bool:
    """Checks if driver has no assignments or is already picking up at the same college as the rider.
    """
    return _has_opening(driver) and (_is_free(driver) or _is_intersecting(driver, rider_loc))


def _has_opening(driver: pd.Series) -> bool:
    """Checks if driver has space to take a rider.
    """
    return driver[DRIVER_OPENINGS_KEY] > 0


def _is_free(driver: pd.Series) -> bool:
    """Checks if driver is completely free (no riders assigned).
    """
    return driver[DRIVER_ROUTE_KEY] == DEFAULT_LOCS_CODE


def _is_intersecting(driver: pd.Series, rider_loc: int) -> bool:
    """Checks if a driver route intersects with a rider's location.
    """
    driver_loc = driver[DRIVER_ROUTE_KEY]
    return (driver_loc & rider_loc) != 0