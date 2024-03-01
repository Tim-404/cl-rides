"""
"""

import json
import os
import pathlib
import pickle
import typing

import gspread
import pandas as pd


class Rides:
    """
    """
    _path_sa = pathlib.Path(__file__).parent / "service_account.json"
    _path_sheetids = pathlib.Path(__file__).parent / "sheet_ids.json"
    _path_cache = pathlib.Path("pickle")

    _keys_cache = ("permanent", "weekly", "drivers", "out")

    def __init__(
        self, *,
        path_sa: typing.Union[str, pathlib.Path] = _path_sa,
        path_sheetids: typing.Union[str, pathlib.Path] = _path_sheetids,
        path_cache: typing.Union[str, pathlib.Path] = _path_cache
    ):
        self._path_sa = pathlib.Path(path_sa)
        self._path_sheetids = pathlib.Path(path_sheetids)
        self._path_cache = pathlib.Path(path_cache)

        self._client = gspread.service_account(filename=self.path_sa)

        with open(self.path_sheetids, "r", encoding="utf-8") as file:
            self._sheetids = json.load(file)

        if set(self._keys_cache) != set(self.sheetids):
            raise KeyError(self.path_sheetids)
        
        self.create_cache()

    @property
    def path_sa(self) -> pathlib.Path:
        """
        """
        return self._path_sa

    @property
    def path_sheetids(self) -> pathlib.Path:
        """
        """
        return self._path_sheetids

    @property
    def path_cache(self) -> pathlib.Path:
        """
        """
        return self._path_cache

    @property
    def client(self) -> gspread.Client:
        """
        """
        return self._client

    @property
    def sheetids(self) -> typing.Dict[str, str]:
        """
        """
        return self._sheetids

    @property
    def cache(self) -> typing.Dict[str, pathlib.Path]:
        """
        """
        return {k: self.path_cache / k for k in self.sheetids}

    def create_cache(self) -> None:
        """
        """
        if not self.path_cache.exists():
            os.makedirs(self.path_cache)

        for sheet_name in self.sheetids:
            if not (self.path_cache / sheet_name).exists():
                pd.DataFrame().to_pickle(self.path_cache / sheet_name)

    def write_cache(self) -> None:
        """
        """
        for sheet_name, sheet_id in self.sheetids.items():
            sheet = self.client.open_by_key(sheet_id).get_worksheet(0)
            records = sheet.get_all_records()

            with open(self.cache[sheet_name], "wb") as file:
                pickle.dump(records, file)

    def read_cache(self) -> typing.Dict[str, pd.DataFrame]:
        """
        """
        dataframes = {}

        for sheet_name in self.sheetids.items():
            with open(self.cache[sheet_name], "rb") as file:
                records = pickle.load(file)

            dataframes.setdefault(sheet_name, pd.DataFrame(records))

        return dataframes

    def cached_input(self, entity: typing.Literal["drivers", "riders"]) -> pd.DataFrame:
        """
        """
        cache = self.read_cache()

        if entity == "drivers":
            return cache["drivers"]

        # TODO: Refactor
        """
        prep.standardize_permanent_responses(permanent_riders)
        prep.standardize_weekly_responses(weekly_riders)
        
        # Reorder and rename columns before merging
        if len(weekly_riders.index) > 0:
            weekly_riders = weekly_riders[[WEEKLY_RIDER_TIMESTAMP_HDR, WEEKLY_RIDER_NAME_HDR, WEEKLY_RIDER_PHONE_HDR, WEEKLY_RIDER_LOCATION_HDR, WEEKLY_RIDER_FRIDAY_HDR, WEEKLY_RIDER_SUNDAY_HDR, WEEKLY_RIDER_NOTES_HDR]]
            weekly_riders.rename(columns={WEEKLY_RIDER_TIMESTAMP_HDR: RIDER_TIMESTAMP_HDR, WEEKLY_RIDER_NAME_HDR: RIDER_NAME_HDR, WEEKLY_RIDER_PHONE_HDR: RIDER_PHONE_HDR, WEEKLY_RIDER_LOCATION_HDR: RIDER_LOCATION_HDR, WEEKLY_RIDER_FRIDAY_HDR: RIDER_FRIDAY_HDR, WEEKLY_RIDER_SUNDAY_HDR: RIDER_SUNDAY_HDR, WEEKLY_RIDER_NOTES_HDR: RIDER_NOTES_HDR}, inplace=True)
            weekly_riders = weekly_riders[weekly_riders[RIDER_PHONE_HDR] != np.nan] # remove lines that have been deleted
        if len(permanent_riders.index) > 0:
            permanent_riders.rename(columns={PERMANENT_RIDER_TIMESTAMP_HDR: RIDER_TIMESTAMP_HDR, PERMANENT_RIDER_NAME_HDR: RIDER_NAME_HDR, PERMANENT_RIDER_PHONE_HDR: RIDER_PHONE_HDR, PERMANENT_RIDER_LOCATION_HDR: RIDER_LOCATION_HDR, PERMANENT_RIDER_FRIDAY_HDR: RIDER_FRIDAY_HDR, PERMANENT_RIDER_SUNDAY_HDR: RIDER_SUNDAY_HDR, PERMANENT_RIDER_NOTES_HDR: RIDER_NOTES_HDR}, inplace=True)
        if ARGS[PARAM_JUST_WEEKLY]:
            riders = weekly_riders
        else:
            riders = pd.concat([permanent_riders, weekly_riders])
        riders.reset_index(inplace=True, drop=True)
        """

    def cached_output(self) -> pd.DataFrame:
        """
        """
        return self.read_cache()["out"]

    def write(self, dataframe: pd.DataFrame, *, update: bool = True) -> None:
        """
        """
        dataframe.to_pickle(self.cache["out"])

        if not update:
            return

        sheet = self.client.open_by_key(self.sheetids("out")).get_worksheet(0)
        sheet.resize(rows=dataframe.size[0])
        sheet.update([dataframe.columns.values.tolist()] + dataframe.values.tolist())
