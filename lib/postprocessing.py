"""Implements all the postprocessing functionality for the results.
"""

from cfg.config import *
import logging
import numpy as np
import pandas as pd


def print_unassigned_riders(out: pd.DataFrame) -> None:
    for o_idx in out.index:
        if type(out.at[o_idx, OUTPUT_DRIVER_NAME_HDR]) is not str:
            logging.warn(f'Rider not assigned: [{out.at[o_idx, RIDER_NAME_HDR]}]')


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


def clean_output(out: pd.DataFrame) -> pd.DataFrame:
    """Filters out the unneeded columns and and validates the data before writing.
    """
    return _format_output(out)


def _format_output(out: pd.DataFrame) -> pd.DataFrame:
    """Organizes the output to order by driver. Removes redundant driver details. Also spaces out driver groups.
    """
    if len(out) == 0:
        return
    
    out.sort_values(by=[DRIVER_GROUP_HDR, OUTPUT_DRIVER_NAME_HDR, RIDER_LOCATION_HDR], inplace=True)
    out.reset_index(inplace=True, drop=True)

    driver_cnt = 1
    unassigned_cnt = 0
    total_capacity = int(out.at[0, OUTPUT_DRIVER_CAPACITY_HDR])
    for idx in range(1, len(out)):
        if out.at[idx, OUTPUT_DRIVER_NAME_HDR] is not np.nan and out.at[idx, OUTPUT_DRIVER_NAME_HDR] != out.at[idx - 1, OUTPUT_DRIVER_NAME_HDR]:
            total_capacity += int(out.at[idx, OUTPUT_DRIVER_CAPACITY_HDR])
            driver_cnt += 1
        
        if out.at[idx, OUTPUT_DRIVER_NAME_HDR] is np.nan:
            unassigned_cnt += 1

    if unassigned_cnt > 0:
        driver_cnt += 1
 
    # Append enough rows to space out drivers
    total_rows = total_capacity + driver_cnt + unassigned_cnt
    new_out = pd.DataFrame({OUTPUT_DRIVER_NAME_HDR: [''] * total_rows,
                            OUTPUT_DRIVER_CAPACITY_HDR: [''] * total_rows,
                            RIDER_NAME_HDR: [''] * total_rows,
                            RIDER_PHONE_HDR: [''] * total_rows,
                            RIDER_LOCATION_HDR: [''] * total_rows,
                            RIDER_NOTES_HDR: [''] * total_rows
                            })

    # Edge case for 1st rider
    _copy_output_row(new_out, out, 1, 0)
    prev_driver_name = out.at[0, OUTPUT_DRIVER_NAME_HDR]
    curr_driver_capacity = int(out.at[0, OUTPUT_DRIVER_CAPACITY_HDR]) if out.at[0, OUTPUT_DRIVER_CAPACITY_HDR] is not np.nan else 0
    new_idx = 2
    new_driver_idx = 1

    for old_idx in range(1, len(out)):

        # Handle formatting for a new driver
        curr_driver_name = out.at[old_idx, OUTPUT_DRIVER_NAME_HDR] 
        is_next_driver = prev_driver_name is not np.nan and prev_driver_name != curr_driver_name
        if is_next_driver:
            prev_driver_name = curr_driver_name
            new_driver_idx += curr_driver_capacity + 1
            curr_driver_capacity = int(out.at[old_idx, OUTPUT_DRIVER_CAPACITY_HDR]) if out.at[old_idx, OUTPUT_DRIVER_CAPACITY_HDR] is not np.nan else 0
            new_idx = new_driver_idx

        if curr_driver_name is np.nan:
            # No driver assigned
            out.at[old_idx, OUTPUT_DRIVER_NAME_HDR] = '?'
            out.at[old_idx, OUTPUT_DRIVER_CAPACITY_HDR] = '?'
            logging.debug(f'_format_output --- {out.at[old_idx, RIDER_NAME_HDR]} has no driver')
        elif not is_next_driver:
            # Remove redundant driver details.
            out.at[old_idx, OUTPUT_DRIVER_NAME_HDR] = ''
            out.at[old_idx, OUTPUT_DRIVER_CAPACITY_HDR] = ''

        _copy_output_row(new_out, out, new_idx, old_idx)
        new_idx += 1
    
    return new_out

        
def _copy_output_row(dst: pd.DataFrame, src: pd.DataFrame, dst_idx: int, src_idx: int):
    dst.at[dst_idx, OUTPUT_DRIVER_NAME_HDR] = src.at[src_idx, OUTPUT_DRIVER_NAME_HDR]
    dst.at[dst_idx, OUTPUT_DRIVER_CAPACITY_HDR] = src.at[src_idx, OUTPUT_DRIVER_CAPACITY_HDR]
    dst.at[dst_idx, RIDER_NAME_HDR] = src.at[src_idx, RIDER_NAME_HDR]
    dst.at[dst_idx, RIDER_PHONE_HDR] = src.at[src_idx, RIDER_PHONE_HDR]
    dst.at[dst_idx, RIDER_LOCATION_HDR] = src.at[src_idx, RIDER_LOCATION_HDR]
    dst.at[dst_idx, RIDER_NOTES_HDR] = src.at[src_idx, RIDER_NOTES_HDR]