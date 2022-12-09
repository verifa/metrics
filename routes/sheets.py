"""Google sheets related functions and classes"""

import logging
import os

import pandas as pd
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class GoogleSheets:
    """
    GoogleSheets data class

    Note:
    Uses a Google service account to authenticate.
    Make sure your service account user has been given read access to your sheet.
    """

    SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

    credentials: Credentials
    spreadsheet_id: str

    def __init__(self, credentials_path: str, spreadsheet_id: str) -> None:
        self.credentials = service_account.Credentials.from_service_account_file(credentials_path, scopes=self.SCOPES)
        self.spreadsheet_id = spreadsheet_id

    def get_all(self) -> pd.DataFrame:
        """
        Fetches all data from the spreadsheet as DataFrames
        Each worksheet in the spreadsheet results in one DataFrame
        """
        spreadsheet = None
        try:
            service = build("sheets", "v4", credentials=self.credentials)
            spreadsheet = service.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()
            if not spreadsheet:
                logging.warning(f"spreadsheet empty")
        except HttpError as err:
            logging.error(err)
            return []
        for worksheet in spreadsheet.get("sheets", []):
            sheet_title = worksheet.get("properties", {}).get("title", "")
            yield self.get_range(sheet_title)

    def get_range(self, range: str) -> pd.DataFrame:
        """
        Fetches values in the given range, e.g. "Sheet1!A2:B7"
        Values are returned as a DataFrame
        If range is the worksheet title, return all values of that worksheet
        """
        values = None
        try:
            service = build("sheets", "v4", credentials=self.credentials)
            result = service.spreadsheets().values().get(spreadsheetId=self.spreadsheet_id, range=range).execute()
            values = result.get("values", [])
            if not values:
                logging.warning(f"no data found in {range}")
        except HttpError as err:
            logging.error(err)
            return []
        return pd.DataFrame(values)


def main():
    sheet = GoogleSheets(
        credentials_path=os.environ.get("METRICS_GSHEET_CREDS"),
        spreadsheet_id=os.environ.get("METRICS_GSHEET_SHEET_ID"),
    )

    range = sheet.get_range("Costs!A1:B5")
    print(range)

    all_dataframes = sheet.get_all()
    for dataframe in all_dataframes:
        print("----")
        print(dataframe)


if __name__ == "__main__":
    main()
