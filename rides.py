""" Main file for automatic driver assignments.
"""

import argparse
import cfg
from cfg.config import *
import lib.custom_log as my_logger
import lib.feature as feat
import lib.postprocessing as post
import lib.rides_data as data
import logging
import os


def main() -> None:
    """ Assign riders to drivers, updating the sheet if specified
    """

    my_logger.init()

    # Continue only if service_account.json exists for accessing the Google Sheets data
    api_reqs_fulfilled = os.path.exists(SERVICE_ACCT_FILE) or not (args[PARAM_DOWNLOAD] or args[PARAM_UPLOAD]) 
    if not api_reqs_fulfilled:
        logging.critical(f'${SERVICE_ACCT_FILE} not found.')
        logging.critical('Make sure service_account.json is in the cfg directory.')
        logging.critical("Contact Timothy Wu if you don't have it.")
        return

    cfg.init()

    # Fetch data from sheets
    if ARGS[PARAM_DOWNLOAD]:
        data.update_pickles()

    # Print input
    data.print_pickles()
    
    (drivers, riders) = data.get_cached_input()

    if len(riders.index) == 0:
        logging.error('No riders, aborting')
        return
    if len(drivers.index) == 0:
        logging.error('No drivers, aborting')
        return

    if ARGS[PARAM_ROTATE]:
        feat.rotate_drivers(drivers)

    # Execute the assignment algorithm
    if ARGS[PARAM_DAY] == ARG_FRIDAY:
        out = feat.assign_friday(drivers, riders)
    else:
        out = feat.assign_sunday(drivers, riders)
    
    # Print output
    out = post.clean_output(out)

    data.write_assignments(out, ARGS[PARAM_UPLOAD])


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument(f'--{PARAM_DAY}', required=True, choices=[ARG_FRIDAY, ARG_SUNDAY],
                        help=f'choose either \'{ARG_FRIDAY}\' for CL, or \'{ARG_SUNDAY}\' for church')
    parser.add_argument(f'--{PARAM_SERVICE}', default=ARG_SECOND_SERVICE, choices=[ARG_FIRST_SERVICE, ARG_SECOND_SERVICE],
                        help='select the main Sunday service (i.e. select 1st service during weeks with ACE classes)')
    parser.add_argument(f'--{PARAM_ROTATE}', action='store_true',
                        help='drivers are rotated based on date last driven')
    parser.add_argument(f'--{PARAM_DOWNLOAD}', action=argparse.BooleanOptionalAction, default=True,
                        help='choose whether to download Google Sheets data')
    parser.add_argument(f'--{PARAM_UPLOAD}', action=argparse.BooleanOptionalAction, default=True,
                        help='choose whether to upload output to Google Sheets')
    parser.add_argument(f'--{PARAM_JUST_WEEKLY}', action='store_true',
                        help='use only the weekly rides for for these assignments (i.e. holidays)')
    parser.add_argument(f'--{PARAM_DISTANCE}', type=int, default=2, choices=range(1, ARG_DISTANCE_MAX + 1),
                        help='set how many far a driver can be to pick up at a neighboring location before choosing a last resort driver')
    parser.add_argument(f'--{PARAM_GROUP_SZ}', type=int, default=1, choices=range(1, ARG_GROUP_SZ_MAX + 1),
                        help='set how many riders must be leftover at a location for a driver to pick up from there')
    parser.add_argument(f'--{PARAM_LOG}', type=str.upper, default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help='set a level of verbosity for logging')
    
    args = vars(parser.parse_args())
    ARGS.update(args)
    main()
