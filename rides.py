""" Main file for automatic driver assignments.

Usage:
    python rides.py
"""

from cfg.config import GLOBALS, GROUPING_THRESHOLD, SERVICE_ACCT_FILE
import lib
import os
import sys
import cfg.map


def show_usage() -> None:
    """ Show usage of rides.py
    """
    print('USAGE:')
    print('python rides.py <--friday | --sunday> <--clear | --no-clear> [[FLAG] ...]')
    print()
    print('FLAG')
    print('    --help                Shows usage')
    print('    --debug               Prints out debug statements while running')
    print('    --no-fetch            Prevents new sheet data from being fetched')
    print('    --no-update           Prevents the output sheet from being updated')
    print('    --rotate              Previous assignments are cleared and drivers are rotated based on date last driven')
    print('    --edit                Previous assignments are retained and new assignments are appended')
    print('    --friday              Assigns rides for Friday College Life')
    print('    --sunday              Assigns rides for Sunday service')
    print('    --threshold=<num>     Sets how many open spots a driver must have to spontaneously pick up at a neighboring location. The default is 2.')
    print()


def main(fetch: bool, update: bool, rotate: bool, edit: bool, friday: bool, debug: bool) -> None:
    """ Assign riders to drivers, updating the sheet if specified
    """
    # Fetch data from sheets
    if fetch:
        lib.update_pickles()

    # Print input
    if debug:
        lib.print_pickles()
    
    (drivers, riders) = lib.get_cached_input()
    lib.clean_data(drivers, riders)

    # Do requested preprocessing
    if rotate or edit:
        prev_out = lib.get_cached_output()
        if rotate:
            # Rotate drivers by last date driven
            lib.rotate_drivers(drivers, lib.get_prev_driver_phones(prev_out))
            lib.update_drivers_locally(drivers)
        elif edit:
            #TODO: Load previous output into assignments
            pass

    # Update map of locations
    cfg.map.update_map(drivers, riders, debug)

    # Execute the assignment algorithm
    if friday:
        out = lib.assign_friday(drivers, riders, debug)
    else:
        out = lib.assign_sunday(drivers, riders, debug)
    
    # Print output
    if debug:
        print('Assignments output')
        print(out)

    lib.write_assignments(out, update)


if __name__ == '__main__':
    execute = True
    update = True
    fetch = True
    debug = False
    rotate = False
    edit = False
    friday = False
    sunday = False

    for argv in sys.argv[1:]:
        if argv == '--help':
            execute = False
        elif argv == '--debug':
            debug = True
        elif argv == '--no-fetch':
            fetch = False
        elif argv == '--no-update':
            update = False
        elif argv == '--rotate':
            rotate = True
        elif argv == '--edit':
            edit = True
        elif argv == '--friday':
            friday = True
        elif argv == '--sunday':
            sunday = True
        elif argv.find('--threshold') != -1:
            try:
                GLOBALS[GROUPING_THRESHOLD] = int(argv.split('=').pop())
            except:
                execute = False
    
    valid_day = friday != sunday
    valid_clear_opt = not (rotate and edit)
    api_reqs_fulfilled = os.path.exists(SERVICE_ACCT_FILE) or not (update or fetch) 
    execute = execute and valid_day and valid_clear_opt and api_reqs_fulfilled

    if execute:
        main(fetch, update, rotate, edit, friday, debug)
    elif not api_reqs_fulfilled:
        print(f'${SERVICE_ACCT_FILE} not found.')
        print('Make sure service_account.json is in the cfg directory.')
        print("Contact Eric Pham if you don't have it.")
    else:
        show_usage()
