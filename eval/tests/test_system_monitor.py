import unittest
import pandas as pd
from eval.src.system_monitor import SystemMonitor

class TestSystemMonitor(unittest.TestCase):
    
    def setUp(self):
        """
        Setup method to initialize common resources for the tests.
        """
        # Mock configuration for metrics
        self.config_file = 'test_config.json'
        with open(self.config_file, 'w') as f:
            f.write('{"metrics": ["suggestion_approval_rate"]}')

        # Initialize MetricCalculator with the test configuration
        self.calculator = SystemMonitor(self.config_file)
    
    def test_suggestion_approval_rate_all_accepted_with_modifications(self):
        """
        Test case where all accepted rows have non-null modified_fields.
        Expecting suggestion approval rate to be 100%.
        """
        # Mock dataframe where all accepted rows have modified_fields
        data = {
            'status': ['accepted', 'accepted', 'accepted'],
            'modified_fields': ['mod1', 'mod2', 'mod3']
        }
        issues_df = pd.DataFrame(data)
        
        # Calculate metrics
        self.calculator.calculate_metrics(issues_df)
        
        # Assert that suggestion approval rate is 100%
        self.assertEqual(self.calculator.get_suggestion_approval_rate(), 100.0)
    
    def test_suggestion_approval_rate_some_accepted_with_modifications(self):
        """
        Test case where only some accepted rows have non-null modified_fields.
        Expecting suggestion approval rate to be less than 100%.
        """
        # Mock dataframe with mixed modified_fields
        data = {
            'status': ['accepted', 'accepted', 'accepted', 'dismissed'],
            'modified_fields': ['mod1', None, 'mod3', None]
        }
        issues_df = pd.DataFrame(data)
        
        # Calculate metrics
        self.calculator.calculate_metrics(issues_df)
        
        # 2 out of 3 accepted rows have modified fields -> 66.67% approval rate
        self.assertAlmostEqual(self.calculator.get_suggestion_approval_rate(), (2/3) * 100, places=2)
    
    def test_suggestion_approval_rate_no_modifications(self):
        """
        Test case where no accepted rows have non-null modified_fields.
        Expecting suggestion approval rate to be 0%.
        """
        # Mock dataframe where none of the accepted rows have modified_fields
        data = {
            'status': ['accepted', 'accepted', 'dismissed'],
            'modified_fields': [None, None, None]
        }
        issues_df = pd.DataFrame(data)
        
        # Calculate metrics
        self.calculator.calculate_metrics(issues_df)
        
        # Assert that suggestion approval rate is 0%
        self.assertEqual(self.calculator.get_suggestion_approval_rate(), 0.0)
    
    def test_suggestion_approval_rate_no_accepted_rows(self):
        """
        Test case where there are no accepted rows.
        Expecting suggestion approval rate to be 0%.
        """
        # Mock dataframe with no accepted rows
        data = {
            'status': ['dismissed', 'dismissed'],
            'modified_fields': [None, None]
        }
        issues_df = pd.DataFrame(data)
        
        # Calculate metrics
        self.calculator.calculate_metrics(issues_df)
        
        # Assert that suggestion approval rate is 0%
        self.assertEqual(self.calculator.get_suggestion_approval_rate(), 0.0)

    def tearDown(self):
        """
        Clean up any resources after the tests.
        """
        import os
        os.remove(self.config_file)  # Remove the test config file

# Run the tests
if __name__ == '__main__':
    unittest.main()
