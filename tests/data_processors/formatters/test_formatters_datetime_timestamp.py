import unittest
import pandas as pd
import numpy as np
from datetime import datetime

from sdgx.data_models.metadata import Metadata
from sdgx.data_processors.formatters.datetime import DatetimeFormatter


class TestDatetimeFormatterWithTimestamp(unittest.TestCase):
    def setUp(self):
        self.formatter = DatetimeFormatter()
        self.dates = [
            datetime(2023, 1, 1),
            datetime(2023, 1, 2),
            datetime(2023, 1, 1),
            datetime(2023, 1, 2)
        ]
        self.timestamps = [datetime.timestamp(d) for d in self.dates]
        self.data = pd.DataFrame({
            'date1': self.timestamps,
            'date2': self.timestamps,
            'date3': [
                datetime.timestamp(datetime(2023, 1, 1)),
                datetime.timestamp(datetime(2023, 1, 2)),
                datetime.timestamp(datetime(2023, 2, 1)),
                datetime.timestamp(datetime(2023, 2, 2))
            ]
        })
        self.metadata = Metadata(
            datetime_columns=['date1', 'date2', 'date3'],
            datetime_format={
                'date1': '%Y-%m-%d',
                'date2': '%Y-%m-%d',
                'date3': '%Y-%m-%d'
            }
        )
        self.formatter.fit(self.metadata)

    def test_convert_timestamp_input(self):
        """Test that convert handles timestamp input correctly"""
        # Convert should keep timestamps as is
        converted = self.formatter.convert(self.data)
        pd.testing.assert_frame_equal(converted, self.data)

    def test_reverse_convert_timestamp_input(self):
        """Test that reverse_convert correctly formats timestamps to datetime strings"""
        # First convert (should keep timestamps)
        converted = self.formatter.convert(self.data)
        
        # Then reverse convert to get datetime strings
        result = self.formatter.reverse_convert(converted)
        
        expected = pd.DataFrame({
            'date1': ['2023-01-01', '2023-01-02', '2023-01-01', '2023-01-02'],
            'date2': ['2023-01-01', '2023-01-02', '2023-01-01', '2023-01-02'],
            'date3': ['2023-01-01', '2023-01-02', '2023-02-01', '2023-02-02']
        })
        
        pd.testing.assert_frame_equal(result, expected)

    def test_mixed_input(self):
        """Test that formatter handles mixed input (timestamps and strings) correctly"""
        # Create mixed input with both timestamps and formatted strings
        mixed_data = self.data.copy()
        mixed_data.loc[0, 'date1'] = '2023-01-01'  # Replace first row with formatted string
        
        # Convert should handle both formats
        converted = self.formatter.convert(mixed_data)
        
        # First row should match timestamp of 2023-01-01
        expected_timestamp = datetime.timestamp(datetime(2023, 1, 1))
        self.assertAlmostEqual(converted.loc[0, 'date1'], expected_timestamp)
        
        # Other rows should remain unchanged
        for i in range(1, len(self.data)):
            self.assertAlmostEqual(converted.loc[i, 'date1'], self.data.loc[i, 'date1'])


if __name__ == '__main__':
    unittest.main()