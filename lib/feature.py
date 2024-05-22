"""Contains complex operations directly associated with what the user wants to accomplish.
"""

from cfg.config import *
import lib.assignments as core
import lib.rides_data as data
import lib.setup as setup
import lib.stat as stat
import pandas as pd


def rotate_drivers(drivers_df: pd.DataFrame):
    setup.mark_unused_drivers(drivers_df)
    drivers_df.sort_values(by=DRIVER_TIMESTAMP_HDR, inplace=True, ascending=False)
    data.update_drivers_locally(drivers_df)


def assign_sunday(drivers_df: pd.DataFrame, riders_df: pd.DataFrame) -> pd.DataFrame:
    """Assigns Sunday rides.
    """
    (drivers, riders) = setup.filter_sunday(drivers_df, riders_df)
    (drivers1, riders1, drivers2, riders2) = setup.split_sunday_services(drivers, riders)

    assignments1 = core.organize(drivers1, riders1)
    assignments2 = core.organize(drivers2, riders2)
    out = pd.concat([assignments1, assignments2])
    stat.print_unassigned_riders(out)
    stat.print_unused_drivers(out, drivers)
    return out


def assign_friday(drivers_df: pd.DataFrame, riders_df: pd.DataFrame) -> pd.DataFrame:
    """Assigns Friday rides.
    """
    (drivers, riders) = setup.filter_friday(drivers_df, riders_df)
    (drivers1, riders1, drivers2, riders2) = setup.split_friday_late_cars(drivers, riders)

    assignments1 = core.organize(drivers1, riders1)
    assignments2 = core.organize(drivers2, riders2)
    out = pd.concat([assignments1, assignments2])
    stat.print_unassigned_riders(out)
    stat.print_unused_drivers(out, drivers)
    return out