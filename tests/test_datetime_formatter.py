import pandas as pd
import pytest
from datetime import datetime

from sdgx.data_processors.formatters.datetime import DatetimeFormatter
from sdgx.data_models.metadata import Metadata

def test_datetime_formatter_with_various_inputs():
    # Create test data with various datetime formats
    data = {
        'date1': ['1990-01-01', '1992-05-15', '1988-03-22'],
        'date2': ['2023-12-01 10:30:00', '2023-12-02 11:45:00', '2023-12-03 12:15:00'],
        'date3': [pd.Timestamp('2023-01-01'), pd.Timestamp('2023-02-01'), pd.Timestamp('2023-03-01')],
        'date4': [datetime(2023,1,1), datetime(2023,2,1), datetime(2023,3,1)]
    }
    df = pd.DataFrame(data)
    
    # Create metadata
    metadata = Metadata()
    metadata.datetime_columns = ['date1', 'date2', 'date3', 'date4']
    metadata.datetime_format = {
        'date1': '%Y-%m-%d',
        'date2': '%Y-%m-%d %H:%M:%S',
        'date3': '%Y-%m-%d',
        'date4': '%Y-%m-%d'
    }
    
    # Initialize formatter
    formatter = DatetimeFormatter()
    formatter.fit(metadata)
    
    # Convert
    converted_df = formatter.convert(df)
    
    # Check that all values are numeric timestamps
    for col in metadata.datetime_columns:
        assert converted_df[col].dtype == float
        assert not converted_df[col].isna().any()
    
    # Reverse convert
    reverted_df = formatter.reverse_convert(converted_df)
    
    # Check that all values are valid datetime strings
    for col in metadata.datetime_columns:
        assert not (reverted_df[col] == "No Datetime").any()
        # Try parsing each value
        for val in reverted_df[col]:
            datetime.strptime(val, metadata.datetime_format[col])

def test_datetime_formatter_with_invalid_inputs():
    # Create test data with invalid datetime values
    data = {
        'date1': ['invalid', '1992-05-15', None],
        'date2': ['2023-13-01', '2023-12-02 11:45:00', float('nan')],  # Invalid month 13
    }
    df = pd.DataFrame(data)
    
    # Create metadata
    metadata = Metadata()
    metadata.datetime_columns = ['date1', 'date2']
    metadata.datetime_format = {
        'date1': '%Y-%m-%d',
        'date2': '%Y-%m-%d %H:%M:%S',
    }
    
    # Initialize formatter
    formatter = DatetimeFormatter()
    formatter.fit(metadata)
    
    # Convert
    converted_df = formatter.convert(df)
    
    # Check that invalid values are converted to NaN
    assert converted_df['date1'].isna().sum() == 2  # 'invalid' and None
    assert converted_df['date2'].isna().sum() == 2  # Invalid date and NaN
    
    # Reverse convert
    reverted_df = formatter.reverse_convert(converted_df)
    
    # Check that NaN values are converted to "No Datetime"
    assert (reverted_df['date1'] == "No Datetime").sum() == 2
    assert (reverted_df['date2'] == "No Datetime").sum() == 2