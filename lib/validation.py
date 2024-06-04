"""Implements data standardization and validation.
"""

from cfg.config import *
import pandas as pd


def standardize_permanent_responses(riders_df: pd.DataFrame):
    """Standardize the permanent responses for Friday and Sunday rides.
    """
    for idx in riders_df.index:
        response = riders_df.at[idx, PERMANENT_RIDER_FRIDAY_HDR]
        riders_df.at[idx, PERMANENT_RIDER_FRIDAY_HDR] = RIDE_THERE_KEYWORD if PERMANENT_RIDE_THERE_KEYWORD in response.lower() else ''
        response = riders_df.at[idx, PERMANENT_RIDER_SUNDAY_HDR]
        riders_df.at[idx, PERMANENT_RIDER_SUNDAY_HDR] = RIDE_THERE_KEYWORD if PERMANENT_RIDE_THERE_KEYWORD in response.lower() else ''


def standardize_weekly_responses(riders_df: pd.DataFrame):
    """Standardize the weekly responses for Friday and Sunday rides.
    """
    for idx in riders_df.index:
        response = riders_df.at[idx, WEEKLY_RIDER_FRIDAY_HDR]
        riders_df.at[idx, WEEKLY_RIDER_FRIDAY_HDR] = RIDE_THERE_KEYWORD if WEEKLY_RIDE_THERE_KEYWORD in response.lower() else ''
        response = riders_df.at[idx, WEEKLY_RIDER_SUNDAY_HDR]
        riders_df.at[idx, WEEKLY_RIDER_SUNDAY_HDR] = RIDE_THERE_KEYWORD if WEEKLY_RIDE_THERE_KEYWORD in response.lower() else ''


def clean_data(drivers_df: pd.DataFrame, riders_df: pd.DataFrame):
    """Filters out the unneeded columns and and validates the data before assigning.
    """
    _enforce_types(drivers_df, riders_df)


def _enforce_types(drivers_df: pd.DataFrame, riders_df: pd.DataFrame):
    """Recovers proper datatypes, allows type specific operations in the future
    """
    drivers_df[DRIVER_TIMESTAMP_HDR] = pd.to_datetime(drivers_df[DRIVER_TIMESTAMP_HDR])
    drivers_df[DRIVER_CAPACITY_HDR]  = drivers_df[DRIVER_CAPACITY_HDR].astype(int)
    drivers_df[DRIVER_PHONE_HDR]     = drivers_df[DRIVER_PHONE_HDR].astype(str)
    drivers_df[DRIVER_PREF_LOC_HDR]  = drivers_df[DRIVER_PREF_LOC_HDR].astype(str)
    drivers_df[DRIVER_NOTES_HDR]     = drivers_df[DRIVER_NOTES_HDR].astype(str)

    riders_df[RIDER_TIMESTAMP_HDR] = pd.to_datetime(riders_df[RIDER_TIMESTAMP_HDR])
    riders_df[RIDER_PHONE_HDR]     = riders_df[RIDER_PHONE_HDR].astype(str)