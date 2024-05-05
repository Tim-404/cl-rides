from cfg.config import *
import logging
import os


def load_map():
    """Loads map.txt into a dictionary of bitmaps for the hardcoded locations.
    """
    if os.path.isfile(MAP_FILE):
        map_file = MAP_FILE
    else:
        logging.warning(f'{os.path.basename(MAP_FILE)} not found. Location optimizations are ignored.')
        return
    
    if ARGS[PARAM_DAY] == ARG_FRIDAY:
        if os.path.isfile(CAMPUS_FILE):
            with open(CAMPUS_FILE) as campus:
                for place in campus:
                    place = place.strip().lower()
                    CAMPUS_LOCS.add(place)
        else:
            logging.warning(f'{os.path.basename(CAMPUS_FILE)} not found. Friday campus riders are not filtered.')

    cnt = 0
    with open(map_file, 'r') as map:
        loc = 0b1
        for line in map:
            if (line.startswith('#')):
                continue
            places = line.split(',')
            places = [place.strip().lower() for place in places]
            for place in places:
                if ARGS[PARAM_DAY] == ARG_FRIDAY and place in CAMPUS_LOCS:
                    place = CAMPUS.strip().lower()
                if place not in LOC_MAP:
                    LOC_MAP[place] = LOC_NONE
                LOC_MAP[place] |= loc
            loc <<= 1
            cnt += 1

    logging.info(f'{os.path.basename(map_file)} loaded with size={cnt}')


def load_driver_prefs():
    """Loads the preferred locations of drivers.
    """
    try:
        cnt = 0
        with open(DRIVER_PREFS_FILE, 'r') as prefs:
            for pref in prefs:
                pref = pref.split(',')
                phone = pref[1].strip()
                loc = pref[2].strip().lower()
                service = pref[3].strip()
                if loc != '' and loc in LOC_MAP:
                    DRIVER_LOC_PREFS[phone] = LOC_MAP.get(loc, LOC_NONE)
                if service != '':
                    DRIVER_SERVICE_PREFS[phone] = service
                cnt += 1
        logging.info(f'Loaded {cnt} driver preferences')
    except:
        logging.warning(f'{os.path.basename(DRIVER_PREFS_FILE)} not found. No driver preferences.')


def create_pickles():
    """Create cache files in pickle directory.
    """
    if (not os.path.isdir(DATA_PATH)):
        os.makedirs(DATA_PATH)
    import pandas as pd
    if (not os.path.exists(os.path.join(DATA_PATH, PERMANENT_SHEET_KEY))):
        pd.DataFrame().to_pickle(os.path.join(DATA_PATH, PERMANENT_SHEET_KEY))
    if (not os.path.exists(os.path.join(DATA_PATH, WEEKLY_SHEET_KEY))):
        pd.DataFrame().to_pickle(os.path.join(DATA_PATH, WEEKLY_SHEET_KEY))
    if (not os.path.exists(os.path.join(DATA_PATH, DRIVER_SHEET_KEY))):
        pd.DataFrame().to_pickle(os.path.join(DATA_PATH, DRIVER_SHEET_KEY))
    if (not os.path.exists(os.path.join(DATA_PATH, OUTPUT_SHEET_KEY))):
        pd.DataFrame().to_pickle(os.path.join(DATA_PATH, OUTPUT_SHEET_KEY))


def load(args: dict):
    ARGS.update(args)
    load_map()
    load_driver_prefs()
    create_pickles()