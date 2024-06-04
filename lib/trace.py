"""Contains all helper functions for printing statistics.
"""

from cfg.config import *
import json
import logging
import pandas as pd
import pickle


def dbg_pickles():
    """Print the riders and drivers in the pickle files.

    There is no call to the Google Sheets API, so the printed data is from the last call to update_pickles.
    """
    if logging.getLevelName(ARGS[PARAM_LOG]) > logging.DEBUG:
        return

    with open(os.path.join(CFG_PATH, SHEET_IDS_FILE)) as gid_json:
        keys = json.load(gid_json).keys()

    for key in keys:
        with open(os.path.join(DATA_PATH, key), 'rb') as pickle_file:
            records = pickle.load(pickle_file)
            df = pd.DataFrame(records)
            logging.debug(f'Printing {key}')
            print(df)


def info_cnt_drivers_ignored(drivers_df: pd.DataFrame):
    cnt_drivers_labeled_ignore = len(drivers_df[drivers_df[DRIVER_NOTES_HDR].str.lower().str.contains(IGNORE_KEYWORD)].index)
    logging.info(f'{cnt_drivers_labeled_ignore} drivers labeled "ignore"')


def info_cnt_riders_ignored(riders_df: pd.DataFrame):
    cnt_riders_labeled_ignore = len(riders_df[riders_df[RIDER_NOTES_HDR].str.lower().str.contains(IGNORE_KEYWORD)].index)
    logging.info(f'{cnt_riders_labeled_ignore} riders labeled "ignore"')


def warn_rider_no_phone(riders_df_no_phone: pd.DataFrame):
    if len(riders_df_no_phone.index) > 0 and logging.getLevelName(ARGS[PARAM_LOG]) <= logging.WARN:
        logging.warn('Riders missing phone numbers, ignoring:')
        print(riders_df_no_phone[[RIDER_NAME_HDR]])


def warn_rider_dup_phone(riders_df_dup_phone: pd.DataFrame):
    if len(riders_df_dup_phone.index) > 0 and logging.getLevelName(ARGS[PARAM_LOG]) <= logging.WARN:
        logging.warn('Riders sharing phone numbers, keeping last:')
        print(riders_df_dup_phone[[RIDER_NAME_HDR, RIDER_PHONE_HDR]])


def dbg_available_drivers(drivers_df: pd.DataFrame):
    if logging.getLevelName(ARGS[PARAM_LOG]) <= logging.DEBUG:
        logging.debug("Drivers available:")
        print(drivers_df[[DRIVER_NAME_HDR, DRIVER_PHONE_HDR, DRIVER_OPENINGS_HDR]])
    

def dbg_used_drivers(drivers_df: pd.DataFrame):
    if logging.getLevelName(ARGS[PARAM_LOG]) <= logging.DEBUG:
        logging.debug("Drivers used:")
        print(drivers_df[[DRIVER_NAME_HDR, DRIVER_PHONE_HDR]])


def info_unassigned_riders(out: pd.DataFrame) -> None:
    for o_idx in out.index:
        if type(out.at[o_idx, OUTPUT_DRIVER_NAME_HDR]) is not str:
            logging.warn(f'No driver for [{out.at[o_idx, RIDER_NAME_HDR]}]')

    # Count picked up riders
    cnt_riders_picked_up = 0
    for r_idx in out.index:
        if type(out.at[r_idx, OUTPUT_DRIVER_NAME_HDR]) is str:
            cnt_riders_picked_up += 1
    logging.info(f'Picking up {cnt_riders_picked_up}/{len(out.index)} riders')


def info_unused_drivers(out: pd.DataFrame, drivers: pd.DataFrame) -> None:
    for d_idx in drivers.index:
        driver_num = drivers.at[d_idx, DRIVER_PHONE_HDR]
        is_available = True
        for o_idx in out.index:
            if out.at[o_idx, OUTPUT_DRIVER_PHONE_HDR] == driver_num:
                is_available = False
                break
        if is_available:
            logging.info(f'Driver still available: [{drivers.at[d_idx, DRIVER_NAME_HDR]}]')