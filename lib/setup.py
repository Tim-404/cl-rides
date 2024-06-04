"""Includes setup routines necessary to run the assignment algorithm.
"""

from cfg.config import *
import lib.rides_data as data
import lib.trace as trace
import logging
import pandas as pd
from sqlite3 import Timestamp


#############################################################################
##                                 COMMON                                  ##
#############################################################################
def mark_unused_drivers(drivers_df: pd.DataFrame):
    """Set timestamps of drivers that were not used the previous week.
    """
    prev_out = data.get_cached_output()
    driver_nums = _get_prev_driver_phones(prev_out)

    now = Timestamp.now()
    for idx in drivers_df.index:
        driver_phone = drivers_df.at[idx, DRIVER_PHONE_HDR]
        if driver_phone not in driver_nums:
            drivers_df.at[idx, DRIVER_TIMESTAMP_HDR] = now

    logging.info('Rotating drivers')


def _get_prev_driver_phones(prev_out: pd.DataFrame) -> set:
    """Returns all the phone numbers of the drivers from the previous grouping.
    """
    phone_nums = set()
    if len(prev_out.index) > 0:
        for phone in prev_out[OUTPUT_DRIVER_PHONE_HDR]:
            phone_nums.add(str(phone))
    return phone_nums


def prioritize_drivers_with_preferences(drivers_df: pd.DataFrame, riders_df: pd.DataFrame):
    _mark_drivers_with_preferences(drivers_df, riders_df)
    drivers_df.sort_values(by=DRIVER_TIMESTAMP_HDR, inplace=True, ascending=False)


def _mark_drivers_with_preferences(drivers_df: pd.DataFrame, riders_df: pd.DataFrame):
    """Set timestamp of drivers with location preferences, if those preferences will be useful.
    """
    # First, count how many riders are at each location
    loc_freq = {}
    for loc in LOC_MAP:
        loc_freq[LOC_MAP.get(loc, LOC_NONE)] = 0
    for loc in riders_df[RIDER_LOCATION_HDR]:
        loc = loc.strip().lower()
        loc_bit = LOC_MAP.get(loc, LOC_NONE)
        loc_freq[loc_bit] = loc_freq.get(loc_bit, 0) + 1

    # Then, if a driver prefers that location, mark their timestamp to sort them to the top
    now = Timestamp.now() + pd.Timedelta(seconds=1)

    for idx in drivers_df.index:
        driver_loc_bit = drivers_df.at[idx, TMP_DRIVER_PREF_LOC]
        if driver_loc_bit != LOC_NONE and loc_freq[driver_loc_bit] > 0:
            loc_freq[driver_loc_bit] -= drivers_df.at[idx, DRIVER_CAPACITY_HDR]
            drivers_df.at[idx, DRIVER_TIMESTAMP_HDR] = now


def fetch_necessary_drivers(drivers_df: pd.DataFrame, cnt_riders: int) -> pd.DataFrame:
    """Reduces the list of drivers to the minimum necessary to offer rides.
    """
    trace.dbg_available_drivers(drivers_df)
    driver_cnt = _find_driver_cnt(drivers_df, cnt_riders)
    drivers = drivers_df.copy()[:driver_cnt]
    drivers.sort_values(by=DRIVER_CAPACITY_HDR, ascending=False, inplace=True)
    trace.dbg_used_drivers(drivers_df)
    return drivers


def _find_driver_cnt(drivers_df: pd.DataFrame, cnt_riders: int) -> int:
    """Determines how many drivers are needed to give rides to all the riders.
    """
    cnt = 0
    for _, idx in enumerate(drivers_df.index):
        if cnt_riders > 0:
            cnt_riders -= drivers_df.at[idx, DRIVER_CAPACITY_HDR]
            cnt += 1
        else:
            break
    return cnt


def add_assignment_vars(drivers_df: pd.DataFrame):
    """Adds temporary columns to the dataframes for calculating assignments.
    """
    drivers_df[DRIVER_OPENINGS_HDR] = drivers_df[DRIVER_CAPACITY_HDR]
    drivers_df[DRIVER_ROUTE_HDR] = LOC_NONE
    drivers_df[TMP_DRIVER_PREF_LOC] = LOC_NONE

    # Load driver location preferences
    cnt_pref = 0
    for idx in drivers_df.index:
        loc = drivers_df.at[idx, DRIVER_PREF_LOC_HDR].strip().lower()
        if loc != '' and loc in LOC_MAP:
            drivers_df.at[idx, TMP_DRIVER_PREF_LOC] = LOC_MAP.get(loc, LOC_NONE)
            cnt_pref += 1
    logging.debug(f'Loaded {cnt_pref} driver location preferences')


def create_rider_map(riders_df: pd.DataFrame):
    """Creates a dictionary of locations to a list of riders.
    """
    rider_map = {
        LOC_NONE: []
    }

    for loc in LOC_MAP:
        rider_map[LOC_MAP.get(loc, LOC_NONE)] = []

    for r_idx in riders_df.index:
        loc = riders_df.at[r_idx, RIDER_LOCATION_HDR].strip().lower()
        loc_msk = LOC_MAP.get(loc, LOC_NONE)
        rider_map[loc_msk].append(r_idx)
    
    return rider_map


def _ignore_drivers(drivers_df: pd.DataFrame):
    remove = drivers_df[drivers_df[DRIVER_NOTES_HDR].str.lower().str.contains(IGNORE_KEYWORD)]
    logging.info(f'Ignoring {len(remove.index)} drivers')
    drivers_df.drop(remove.index, inplace=True)


def _ignore_riders(riders_df: pd.DataFrame):
    remove = riders_df[riders_df[RIDER_NOTES_HDR].str.lower().str.contains(IGNORE_KEYWORD)]
    logging.info(f'Ignoring {len(remove.index)} riders')
    riders_df.drop(remove.index, inplace=True)


###########################################################################
###                             FRIDAY SETUP                            ###
###########################################################################
def filter_friday(drivers_df: pd.DataFrame, riders_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Filters out riders who will get a ride from Peterson.
    """
    trace.info_cnt_drivers_ignored(drivers_df)
    trace.info_cnt_riders_ignored(riders_df)

    drivers = drivers_df.copy()[drivers_df[DRIVER_AVAILABILITY_HDR].str.contains(DRIVER_FRIDAY_KEYWORD)]
    _ignore_drivers(drivers)

    _mark_late_friday_riders(riders_df)
    riders = riders_df.copy()[riders_df[RIDER_FRIDAY_HDR] == RIDE_THERE_KEYWORD]
    _ignore_riders(riders)
    num_riders = len(riders.index)
    riders = riders[~riders[RIDER_LOCATION_HDR].str.strip().str.lower().isin(CAMPUS_LOCS)]  # ~ negates isin(), removes campus ppl
    num_on_campus = num_riders - len(riders.index)
    logging.info(f"Skipping {num_on_campus} on-campus riders, they need rides from Peterson.")

    return (drivers, riders)


def _mark_late_friday_riders(riders_df: pd.DataFrame):
    """Marks late CL riders by assigning them to the CAMPUS location.
    Assumes that they are late because of a class.
    """
    for idx in riders_df.index:
        note = riders_df.at[idx, RIDER_NOTES_HDR].lower()
        if 'late' in note or '6' in note or '7' in note:
            riders_df.at[idx, RIDER_LOCATION_HDR] = CAMPUS


def split_friday_late_cars(drivers_df: pd.DataFrame, riders_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Separates rides for late riders. Also designates drivers for the late riders.
    """
    riders1 = riders_df[~riders_df[RIDER_LOCATION_HDR].str.contains(CAMPUS)].copy()
    riders2 = riders_df[riders_df[RIDER_LOCATION_HDR].str.contains(CAMPUS)].copy()

    late_driver_cnt = _find_driver_cnt(drivers_df, len(riders2))
    drivers1 = drivers_df[late_driver_cnt:].copy()
    drivers2 = drivers_df[:late_driver_cnt].copy()

    drivers1[DRIVER_GROUP_HDR] = 1
    drivers2[DRIVER_GROUP_HDR] = 2

    return (drivers1, riders1, drivers2, riders2)



###########################################################################
###                             SUNDAY SETUP                            ###
###########################################################################
def filter_sunday(drivers_df: pd.DataFrame, riders_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Filters riders that will attend Sunday service.
    """
    trace.info_cnt_drivers_ignored(drivers_df)
    trace.info_cnt_riders_ignored(riders_df)
    
    drivers = drivers_df.copy()[drivers_df[DRIVER_AVAILABILITY_HDR].str.contains(DRIVER_SUNDAY_KEYWORD)]
    _ignore_drivers(drivers)

    riders = riders_df.copy()[riders_df[RIDER_SUNDAY_HDR] == RIDE_THERE_KEYWORD]
    _ignore_riders(riders)
    return (drivers, riders)


def split_sunday_services(drivers_df: pd.DataFrame, riders_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Splits the lists into first and second service lists.
    @returns (drivers1, riders1, drivers2, riders2)
    """
    _add_service_vars(drivers_df, riders_df)
    drivers1 = drivers_df[drivers_df[DRIVER_GROUP_HDR] == ARG_FIRST_SERVICE].copy()
    drivers2 = drivers_df[drivers_df[DRIVER_GROUP_HDR] == ARG_SECOND_SERVICE].copy()
    riders1  = riders_df[riders_df[RIDER_SERVICE_HDR] == ARG_FIRST_SERVICE].copy()
    riders2  = riders_df[riders_df[RIDER_SERVICE_HDR] == ARG_SECOND_SERVICE].copy()
    return (drivers1, riders1, drivers2, riders2)


def _add_service_vars(drivers_df: pd.DataFrame, riders_df: pd.DataFrame):
    """Adds temporary columns to the dataframes for splitting between first and second service.
    """
    drivers_df[DRIVER_GROUP_HDR] = 0
    for idx in drivers_df.index:
        drivers_df.at[idx, DRIVER_GROUP_HDR] = _parse_service(drivers_df.at[idx, DRIVER_NOTES_HDR])

    riders_df[RIDER_SERVICE_HDR] = 0
    for idx in riders_df.index:
        riders_df.at[idx, RIDER_SERVICE_HDR] = _parse_service(riders_df.at[idx, RIDER_NOTES_HDR])


def _parse_service(s: str) -> str:
    """Returns the service that a rider will attend.
    If both services are mentioned, first service is used. This is an arbitrary choice that should be checked by the rides coordinator.
    If no service is mentioned, the rider is assigned to the default service.
    """
    if _requested_first_service(s):
        return ARG_FIRST_SERVICE
    elif _requested_second_service(s):
        return ARG_SECOND_SERVICE
    else:
        return ARGS[PARAM_SERVICE]


def _requested_first_service(s: str) -> bool:
    s = s.lower()
    return 'first' in s or '1st' in s or '8' in s


def _requested_second_service(s: str) -> bool:
    s = s.lower()
    return 'second' in s or '2nd' in s or '10' in s or '11' in s