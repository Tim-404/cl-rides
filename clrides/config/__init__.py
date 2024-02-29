"""
.. py:data:: DATAPATH

    :type: pathlib.Path

    The absolute path to the directory containing configuration files for the application.
"""

import pathlib


DATAPATH = pathlib.Path(__file__).parent / "data"
