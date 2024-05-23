"""Contains all helper functions for printing statistics.
"""

from cfg.config import *
import logging
import pandas as pd

def print_cnt_drivers_labeled_ignore(drivers_df: pd.DataFrame):
    cnt_drivers_labeled_ignore = len(drivers_df[drivers_df[DRIVER_NOTES_HDR].str.lower().str.contains(IGNORE_KEYWORD)].index)
    logging.info(f'{cnt_drivers_labeled_ignore} drivers labeled "ignore"')


def print_cnt_riders_labeled_ignore(riders_df: pd.DataFrame):
    cnt_riders_labeled_ignore = len(riders_df[riders_df[RIDER_NOTES_HDR].str.lower().str.contains(IGNORE_KEYWORD)].index)
    logging.info(f'{cnt_riders_labeled_ignore} riders labeled "ignore"')


def print_unassigned_riders(out: pd.DataFrame) -> None:
    for o_idx in out.index:
        if type(out.at[o_idx, OUTPUT_DRIVER_NAME_HDR]) is not str:
            logging.warn(f'No driver for [{out.at[o_idx, RIDER_NAME_HDR]}]')

    # Count picked up riders
    cnt_riders_picked_up = 0
    for r_idx in out.index:
        if type(out.at[r_idx, OUTPUT_DRIVER_NAME_HDR]) is str:
            cnt_riders_picked_up += 1
    logging.info(f'Picking up {cnt_riders_picked_up}/{len(out.index)} riders')


def print_unused_drivers(out: pd.DataFrame, drivers: pd.DataFrame) -> None:
    for d_idx in drivers.index:
        driver_num = drivers.at[d_idx, DRIVER_PHONE_HDR]
        is_available = True
        for o_idx in out.index:
            if out.at[o_idx, OUTPUT_DRIVER_PHONE_HDR] == driver_num:
                is_available = False
                break
        if is_available:
            logging.info(f'Driver still available: [{drivers.at[d_idx, DRIVER_NAME_HDR]}]')