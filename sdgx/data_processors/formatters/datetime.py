from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any, Dict

import numpy as np
import pandas as pd

from sdgx.data_models.metadata import Metadata
from sdgx.data_processors.extension import hookimpl
from sdgx.data_processors.formatters.base import Formatter
from sdgx.utils import logger


class DatetimeFormatter(Formatter):
    """
    A class for formatting datetime columns in a pandas DataFrame.

    DatetimeFormatter is designed to handle the conversion of datetime columns to timestamp format and vice versa.
    It uses metadata to identify datetime columns and their corresponding datetime formats.

    Attributes:
        datetime_columns (list): List of column names that are of datetime type.
        datetime_formats (dict): Dictionary with column names as keys and datetime formats as values.
        dead_columns (list): List of column names that are no longer needed or to be removed.
        fitted (bool): Indicates whether the formatter has been fitted.

    Methods:
        fit(metadata: Metadata | None = None, **kwargs: dict[str, Any]): Fits the formatter by recording the datetime columns and their formats.
        convert(raw_data: pd.DataFrame) -> pd.DataFrame: Converts datetime columns in raw_data to timestamp format.
        reverse_convert(processed_data: pd.DataFrame) -> pd.DataFrame: Converts timestamp columns in processed_data back to datetime format.
    """

    datetime_columns: list
    """
    List to store the columns that are of datetime type.
    """

    datetime_formats: Dict
    """
    Dictionary to store the datetime formats for each column, with default value as an empty string.
    """

    dead_columns: list
    """
    List to store columns that are no longer needed or to be removed.
    """

    def __init__(self):
        self.fitted = False
        self.datetime_columns = []
        self.datetime_formats = defaultdict(str)
        self.dead_columns = []

    def fit(self, metadata: Metadata | None = None, **kwargs: dict[str, Any]):
        """
        Fit method for datetime formatter, the datetime column and datetime format need to be recorded.

        If there is a column without format, the default format will be used for output (this may cause some problems).

        Formatter need to use metadata to record which columns belong to datetime type, and convert timestamp back to datetime type during post-processing.
        """

        # get from metadata
        self.datetime_formats = metadata.get("datetime_format")
        datetime_columns = []
        dead_columns = []
        # Check datetime_formats and columns
        # exclude columns without format as there is huge risk of handling errors
        meta_datetime_columns = metadata.get("datetime_columns")
        for each_col in meta_datetime_columns:
            if each_col in self.datetime_formats.keys():
                datetime_columns.append(each_col)
            else:
                dead_columns.append(each_col)
                logger.warning(
                    f"Column {each_col} has no datetime_format, DatetimeFormatter will REMOVE this column！"
                )

        # Remove successful formatted datetime columns from metadata.discrete_columns
        if not (set(datetime_columns) - set(metadata.discrete_columns)):
            metadata.change_column_type(datetime_columns, "discrete", "datetime")
        # Remove dead_columns from metadata
        metadata.remove_column(dead_columns)

        self.datetime_columns = datetime_columns
        self.dead_columns = dead_columns

        logger.info("DatetimeFormatter Fitted.")
        self.fitted = True
        return

    def convert(self, raw_data: pd.DataFrame) -> pd.DataFrame:
        """
        Convert method to convert datetime samples into timestamp.

        Args:
            - raw_data (pd.DataFrame): Unprocessed table data
        """
        if len(self.datetime_columns) == 0:
            logger.info(
                "Converting data using DatetimeFormatter... Finished (No datetime columns)."
            )
            return raw_data

        # remove the column without format
        for each_col in self.dead_columns:
            raw_data = self.remove_columns(raw_data, [each_col])
            logger.warning(f"Column {each_col} was removed because lack of format info.")

        logger.info("Converting data using DatetimeFormatter...")

        res_data = self.convert_datetime_columns(
            self.datetime_columns, self.datetime_formats, raw_data
        )

        logger.info("Converting data using DatetimeFormatter... Finished.")

        return res_data

    @staticmethod
    def convert_datetime_columns(datetime_column_list, datetime_formats, processed_data):
        """
        Convert datetime columns in processed_data from string to timestamp (int)

        Args:
            - datetime_column_list (list): List of columns that are date time type
            - processed_data (pd.DataFrame): Processed table data

        Returns:
            - result_data (pd.DataFrame): Processed table data with datetime columns converted to timestamp
        """

        def datetime_formatter(each_value, datetime_format):
            """
            Convert input to timestamp value. Handles both string and datetime inputs.
            """
            try:
                if pd.isna(each_value):
                    return np.nan
                
                if isinstance(each_value, (pd.Timestamp, datetime)):
                    return datetime.timestamp(each_value)
                
                # Try parsing as string
                datetime_obj = datetime.strptime(str(each_value), datetime_format)
                return datetime.timestamp(datetime_obj)
            except Exception as e:
                logger.warning(
                    f"Error converting to timestamp: {e}, value will be set as NaN"
                )
                logger.warning(f"Input parameters: ({str(each_value)}, {datetime_format})")
                logger.warning(f"Input type: ({type(each_value)}, {type(datetime_format)})")
                return np.nan

        # Make a copy of processed_data to avoid modifying the original data
        result_data: pd.DataFrame = processed_data.copy()

        # Convert each datetime column in datetime_column_list to timestamp
        for column in datetime_column_list:
            # Convert datetime to timestamp (float)
            result_data[column] = result_data[column].apply(
                datetime_formatter, datetime_format=datetime_formats[column]
            )
            # Don't fill NaN values - let them propagate through the pipeline
            # This ensures invalid dates remain invalid
        return result_data

    def reverse_convert(self, processed_data: pd.DataFrame) -> pd.DataFrame:
        """
        reverse_convert method for datetime formatter.

        Does not require any action.
        """

        if len(self.datetime_columns) == 0:
            logger.info("Data reverse-converted by DatetimeFormatter (No datetime columns).")
            return processed_data

        logger.info("Data reverse-converting by DatetimeFormatter...")

        logger.info(f"parameters : {self.datetime_columns}, {self.datetime_formats}")

        result_data = self.convert_timestamp_to_datetime(
            self.datetime_columns, self.datetime_formats, processed_data
        )

        logger.info("Data reverse-converted by DatetimeFormatter... Finished.")

        return result_data

    @staticmethod
    def convert_timestamp_to_datetime(timestamp_column_list, format_dict, processed_data):
        """
        Convert timestamp columns to datetime format in a DataFrame.

        Parameters:
            - timestamp_column_list (list): List of column names in the DataFrame which are of timestamp type.
            - datetime_column_dict (dict): Dictionary with column names as keys and datetime format as values.
            - processed_data (pd.DataFrame): DataFrame containing the processed data.

        Returns:
            - result_data (pd.DataFrame): DataFrame with timestamp columns converted to datetime format.

        TODO:
            if the value <0, the result will be `No Datetime`, try to fix it.
        """

        def column_timestamp_formatter(each_stamp: float, timestamp_format: str) -> str:
            """
            Convert timestamp to datetime string with proper error handling.
            """
            try:
                if pd.isna(each_stamp):
                    return "No Datetime"
                
                # Ensure timestamp is valid (not negative or too large)
                if not (0 <= each_stamp <= 253402300799):  # Max valid timestamp
                    return "No Datetime"
                
                return datetime.fromtimestamp(each_stamp).strftime(timestamp_format)
            except Exception as e:
                logger.debug(f"Error converting timestamp to str: {e}")
                return "No Datetime"

        # Copy the processed data to result_data
        result_data = processed_data.copy()

        # Iterate over each column in the timestamp_column_list
        for column in timestamp_column_list:
            # Check if the column is in the DataFrame
            if column in result_data.columns:
                # Convert the timestamp to datetime format using the format provided in datetime_column_dict
                result_data[column] = result_data[column].apply(
                    column_timestamp_formatter, timestamp_format=format_dict[column]
                )
            else:
                logger.error(f"Column {column} not in processed data's column list!")

        return result_data


@hookimpl
def register(manager):
    manager.register("DatetimeFormatter", DatetimeFormatter)
