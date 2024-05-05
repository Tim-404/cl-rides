"""Test script for sunday, no fetching or updating.
"""

import os
import sys
curr = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.dirname(curr))

import rides

args = {
    'day': 'sunday',
    'service': '2',
    'rotate': False,
    'weekly': False,
    'download': False,
    'upload': False,
    'distance': 2,
    'vacancy': 2,
    'log': 'info'
}

rides.main(args)