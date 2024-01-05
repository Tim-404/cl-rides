"""Implements all the logic for the assigning drivers and riders.
Includes group optimization for common pickup locations.
"""

from cfg.config import *
import lib.postprocessing as post
import lib.preprocessing as prep
from lib.rides_data import *
import pandas as pd


def assign(drivers_df: pd.DataFrame, riders_df: pd.DataFrame) -> pd.DataFrame:
    """Assigns rider to drivers in the returned dataframe.
    """
    prep.add_assignment_vars(drivers_df)
    riders_df.sort_values(by=RIDER_LOCATION_HDR, inplace=True, key=lambda col: col.apply(lambda loc: LOC_MAP.get(loc, LOC_MAP[LOC_KEY_ELSEWHERE])))
    out = pd.concat([pd.DataFrame(columns=[OUTPUT_DRIVER_NAME_HDR, OUTPUT_DRIVER_PHONE_HDR, OUTPUT_DRIVER_CAPACITY_HDR]), riders_df[[RIDER_NAME_HDR, RIDER_PHONE_HDR, RIDER_LOCATION_HDR, RIDER_NOTES_HDR]]], axis='columns')

    logging.debug('Drivers')
    logging.debug(drivers_df)
    logging.debug('Riders')
    logging.debug(riders_df)
    logging.debug('Assigning started')

    num_skipped = 0

    for r_idx in out.index:
        rider_loc = LOC_MAP.get(out.at[r_idx, RIDER_LOCATION_HDR], LOC_MAP[LOC_KEY_ELSEWHERE])

        if rider_loc == LOC_MAP[LOC_KEY_ELSEWHERE]:
            num_skipped += 1
            continue

        is_matched = False

        # Check if a driver prefers to pick up there.
        for d_idx, driver in drivers_df.iterrows():
            if _prefers_there(driver, rider_loc):
                _add_rider(out, r_idx, drivers_df, d_idx)
                is_matched = True
                break

        if is_matched:
            continue

        # Check if a driver is already there.
        for d_idx, driver in drivers_df.iterrows():
            if _is_there(driver, rider_loc):
                _add_rider(out, r_idx, drivers_df, d_idx)
                is_matched = True
                break

        if is_matched:
            continue

        # Check if there is a driver up to DISTANCE_THRESHOLD away with at list VACANCY_THRESHOLD spots.
        for dist in range(1, ARGS['distance'] + 1):
            for d_idx, driver in drivers_df.iterrows():
                if _is_nearby_dist(driver, rider_loc, dist) and driver[DRIVER_OPENINGS_HDR] >= ARGS['vacancy']:
                    _add_rider(out, r_idx, drivers_df, d_idx)
                    is_matched = True
                    break

            if is_matched:
                break

        if is_matched:
            continue

        # Check if there is a driver up to DISTANCE_THRESHOLD, ignoring VACANCY_THRESHOLD.
        for dist in range(1, ARGS['distance'] + 1):
            for d_idx, driver in drivers_df.iterrows():
                if _is_nearby_dist(driver, rider_loc, dist):
                    _add_rider(out, r_idx, drivers_df, d_idx)
                    is_matched = True
                    break

            if is_matched:
                break

        # Check if any driver if free that does not have a preferred location.
        for d_idx, driver in drivers_df.iterrows():
            if _is_free(driver) and _has_no_preference(driver):
                _add_rider(out, r_idx, drivers_df, d_idx)
                is_matched = True
                break

        if is_matched:
            continue

        # Find open driver with lightest route.
        open_driver_idx = -1
        open_driver_found = False
        for d_idx, driver in drivers_df.iterrows():
            if _has_opening(driver):
                if not open_driver_found or (_route_len(driver[DRIVER_ROUTE_HDR]) < _route_len(drivers_df.at[open_driver_idx, DRIVER_ROUTE_HDR])):
                    open_driver_idx = d_idx
                open_driver_found = True
        if open_driver_found:
            _add_rider(out, r_idx, drivers_df, open_driver_idx)
            is_matched = True
        
        if not is_matched:
            logging.warn(f'No driver available for {out.at[r_idx, RIDER_NAME_HDR]}')
    
    if num_skipped > 0:
        logging.warn(f'Skipped {num_skipped} riders, location ignored')

    return out


def organize(drivers_df: pd.DataFrame, riders_df: pd.DataFrame) -> pd.DataFrame:
    drivers = prep.fetch_necessary_drivers(drivers_df, len(riders_df))
    out = assign(drivers, riders_df)
    post.alert_skipped_riders(out)
    post.clean_output(out)
    logging.debug(f'Assigned Drivers\n{drivers}')
    return out


def assign_sunday(drivers_df: pd.DataFrame, riders_df: pd.DataFrame) -> pd.DataFrame:
    """Assigns Sunday rides.
    """
    (drivers, riders) = prep.filter_sunday(drivers_df, riders_df)
    (drivers1, riders1, drivers2, riders2) = prep.split_sunday_services(drivers, riders)

    assignments1 = organize(drivers1, riders1)
    assignments2 = organize(drivers2, riders2)

    return pd.concat([assignments1, assignments2])


def assign_friday(drivers_df: pd.DataFrame, riders_df: pd.DataFrame) -> pd.DataFrame:
    """Assigns Friday rides.
    """
    (drivers, riders) = prep.filter_friday(drivers_df, riders_df)
    return organize(drivers, riders)


def _add_rider(out: pd.DataFrame, r_idx: int, drivers_df: pd.DataFrame, d_idx: int):
    """Assigns rider to driver and updates driver openings and locations.
    """
    out.at[r_idx, OUTPUT_DRIVER_NAME_HDR] = drivers_df.at[d_idx, DRIVER_NAME_HDR]
    out.at[r_idx, OUTPUT_DRIVER_PHONE_HDR] = drivers_df.at[d_idx, DRIVER_PHONE_HDR]
    out.at[r_idx, OUTPUT_DRIVER_CAPACITY_HDR] = int(drivers_df.at[d_idx, DRIVER_CAPACITY_HDR])  # Chose not to include total seats
    rider_loc = LOC_MAP.get(out.at[r_idx, RIDER_LOCATION_HDR], LOC_MAP[LOC_KEY_ELSEWHERE])
    drivers_df.at[d_idx, DRIVER_OPENINGS_HDR] -= 1
    drivers_df.at[d_idx, DRIVER_ROUTE_HDR] |= rider_loc


def _is_nearby_dist(driver: pd.Series, rider_loc: int, dist: int) -> bool:
    """Checks if driver has no assignments or is already picking up at the same area as the rider.
    """
    return _has_opening(driver) and (_is_free(driver) or _is_intersecting(driver, rider_loc << dist) or _is_intersecting(driver, rider_loc >> dist))


def _is_there(driver: pd.Series, rider_loc: int) -> bool:
    """Checks if driver is already picking up at the same college as the rider.
    """
    return _has_opening(driver) and _is_intersecting(driver, rider_loc)


def _prefers_there(driver: pd.Series, rider_loc: int) -> bool:
    """Checks if driver is already picking up at the same college as the rider.
    """
    return _has_opening(driver) and (driver[DRIVER_PREF_LOC_HDR] & rider_loc) != 0


def _has_no_preference(driver: pd.Series) -> bool:
    """Checks if driver has a preference.
    """
    return driver[DRIVER_PREF_LOC_HDR] == 0


def _has_opening(driver: pd.Series) -> bool:
    """Checks if driver has space to take a rider.
    """
    return driver[DRIVER_OPENINGS_HDR] > 0


def _is_free(driver: pd.Series) -> bool:
    """Checks if driver is completely free (no riders assigned, no preferences).
    """
    return driver[DRIVER_ROUTE_HDR] == LOC_NONE and driver[DRIVER_PREF_LOC_HDR] == LOC_NONE


def _is_intersecting(driver: pd.Series, rider_loc: int) -> bool:
    """Checks if a driver route intersects with a rider's location.
    """
    driver_loc = driver[DRIVER_ROUTE_HDR]
    return (driver_loc & rider_loc) != 0


def _route_len(route: int) -> int:
    """Returns the number of locations a driver is picking up from.
    """
    cnt = 0
    while route != 0:
        route &= route - 1
        cnt += 1
    return cnt