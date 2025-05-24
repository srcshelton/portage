import unittest
from unittest import mock
import os

# Updated import for resolver components
from portage.pym.portage_resolver import Package, find_best_match_for_name, display_package_resolution_warnings
# No longer need to import portage.config.core directly for mocking if patching the new path

# Define constants for problematic categories to ensure object identity if needed
CAT_LOW1 = "cat-low1"
CAT_LOW2 = "cat-low2"

class TestResolverCore(unittest.TestCase): # Consider renaming to TestPortageResolver

    def setUp(self):
        """Set up a common set of packages for testing."""
        self.packages_data = [
            # name, category, version, masked
            ("pkgA", "cat1", "1.0", False),
            ("pkgA", "cat1", "0.9", False),
            ("pkgA", "cat2", "1.0", False),
            ("pkgB", "cat1", "1.0", True),
            ("pkgC", "cat-low", "1.0", False),
            ("pkgD", "cat-normal", "1.0", False),
            ("pkgD", "cat-low", "1.0", False),
            ("pkgE", "cat-low", "1.0", True),
            ("pkgE", "cat-low", "1.1", False),
            ("pkgF", "cat-normal", "1.0", False),
            ("pkgG", CAT_LOW1, "1.0", False), 
            ("pkgG", CAT_LOW2, "1.0", False), 
            ("pkgH", "cat-normal", "1.0", True),
            ("pkgH", "cat-normal", "1.1", True),
            ("pkgI", "cat-normal", "1.0", False),
            ("pkgI", "cat-low", "1.1", False)
        ]
        self.all_packages = [Package(n, c, v, m) for n, c, v, m in self.packages_data]
        
        self.mock_default_low_prio_categories = ["cat-low", CAT_LOW1, CAT_LOW2]

    # --- Tests for find_best_match_for_name ---

    @mock.patch('portage._emerge.config.get_low_priority_categories') # Updated mock target
    def test_no_package_found(self, mock_get_low_prio):
        mock_get_low_prio.return_value = self.mock_default_low_prio_categories
        with self.assertRaisesRegex(ValueError, "No package found with name: nonExistent"):
            find_best_match_for_name("nonExistent", self.all_packages)

    @mock.patch('portage._emerge.config.get_low_priority_categories') # Updated mock target
    def test_single_normal_match(self, mock_get_low_prio):
        mock_get_low_prio.return_value = self.mock_default_low_prio_categories
        selected, low_excluded, masked_excluded = find_best_match_for_name("pkgF", self.all_packages)
        self.assertEqual(selected, self.all_packages[9])
        self.assertEqual(low_excluded, [])
        self.assertEqual(masked_excluded, [])

    @mock.patch('portage._emerge.config.get_low_priority_categories') # Updated mock target
    def test_only_match_is_masked(self, mock_get_low_prio):
        mock_get_low_prio.return_value = self.mock_default_low_prio_categories
        specific_packages = [self.all_packages[3]] 
        with self.assertRaisesRegex(ValueError, "All packages matching 'pkgB' are masked"):
            find_best_match_for_name("pkgB", specific_packages)

    @mock.patch('portage._emerge.config.get_low_priority_categories') # Updated mock target
    def test_all_matches_are_masked(self, mock_get_low_prio):
        mock_get_low_prio.return_value = self.mock_default_low_prio_categories
        specific_packages = [self.all_packages[12], self.all_packages[13]] 
        with self.assertRaisesRegex(ValueError, "All packages matching 'pkgH' are masked"):
            find_best_match_for_name("pkgH", specific_packages)
        try:
            find_best_match_for_name("pkgH", specific_packages)
        except ValueError as e:
            self.assertIn(str(self.all_packages[12]), str(e))
            self.assertIn(str(self.all_packages[13]), str(e))

    @mock.patch('portage._emerge.config.get_low_priority_categories') # Updated mock target
    def test_selection_among_masked_and_unmasked(self, mock_get_low_prio):
        mock_get_low_prio.return_value = self.mock_default_low_prio_categories 
        selected, low_excluded, masked_excluded = find_best_match_for_name("pkgE", self.all_packages)
        self.assertEqual(selected, self.all_packages[8]) 
        self.assertEqual(low_excluded, []) 
        self.assertListEqual(masked_excluded, [self.all_packages[7]])

    @mock.patch('portage._emerge.config.get_low_priority_categories') # Updated mock target
    def test_normal_selected_over_low_priority(self, mock_get_low_prio):
        mock_get_low_prio.return_value = self.mock_default_low_prio_categories 
        selected, low_excluded, masked_excluded = find_best_match_for_name("pkgD", self.all_packages)
        self.assertEqual(selected, self.all_packages[5]) 
        self.assertListEqual(low_excluded, [self.all_packages[6]]) 
        self.assertEqual(masked_excluded, [])

    @mock.patch('portage._emerge.config.get_low_priority_categories') # Updated mock target
    def test_low_priority_selected_if_no_normal(self, mock_get_low_prio):
        mock_get_low_prio.return_value = self.mock_default_low_prio_categories 
        selected, low_excluded, masked_excluded = find_best_match_for_name("pkgC", self.all_packages)
        self.assertEqual(selected, self.all_packages[4])
        self.assertEqual(low_excluded, [])
        self.assertEqual(masked_excluded, [])

    @mock.patch('portage._emerge.config.get_low_priority_categories') # Updated mock target
    def test_ambiguity_among_normal_priority(self, mock_get_low_prio):
        mock_get_low_prio.return_value = [CAT_LOW1, CAT_LOW2] # Make cat1, cat2 normal
        ambiguous_pkgs = [
            Package("pkgAmb", "cat1", "1.0"),
            Package("pkgAmb", "cat2", "1.0") 
        ]
        with self.assertRaisesRegex(ValueError, "Ambiguous package name 'pkgAmb'. Normal priority matches:"):
            find_best_match_for_name("pkgAmb", ambiguous_pkgs)

    @mock.patch('portage._emerge.config.get_low_priority_categories') # Updated mock target
    def test_ambiguity_among_low_priority(self, mock_get_low_prio):
        mock_get_low_prio.return_value = self.mock_default_low_prio_categories 
        with self.assertRaisesRegex(ValueError, "Ambiguous package name 'pkgG'. Low priority matches:"):
            find_best_match_for_name("pkgG", self.all_packages)
        mock_get_low_prio.assert_called_once()

    @mock.patch('portage._emerge.config.get_low_priority_categories') # Updated mock target
    def test_respect_low_priority_config_false(self, mock_get_low_prio):
        with self.assertRaisesRegex(ValueError, "Ambiguous package name 'pkgI'. Normal priority matches:"):
            find_best_match_for_name("pkgI", self.all_packages, respect_low_priority_config=False)
        mock_get_low_prio.assert_not_called() 

    # --- Tests for display_package_resolution_warnings ---

    @mock.patch('builtins.print')
    def test_warnings_masked_only(self, mock_print):
        selected = self.all_packages[0] 
        masked_list = [self.all_packages[3]] 
        display_package_resolution_warnings(selected, [], masked_list)
        mock_print.assert_any_call(f"Info: The following packages were found but are masked: {masked_list}")

    @mock.patch('builtins.print')
    def test_warnings_low_prio_only(self, mock_print):
        selected = self.all_packages[5]    
        low_prio_list = [self.all_packages[6]] 
        display_package_resolution_warnings(selected, low_prio_list, [])
        mock_print.assert_any_call(f"Info: The selected package '{selected}' was chosen over these low-priority alternatives: {low_prio_list}")

    @mock.patch('builtins.print')
    def test_warnings_both_masked_and_low_prio(self, mock_print):
        selected = self.all_packages[5]    
        low_prio_list = [self.all_packages[6]] 
        masked_list = [self.all_packages[3]]   
        display_package_resolution_warnings(selected, low_prio_list, masked_list)
        mock_print.assert_any_call(f"Info: The following packages were found but are masked: {masked_list}")
        mock_print.assert_any_call(f"Info: The selected package '{selected}' was chosen over these low-priority alternatives: {low_prio_list}")

    @mock.patch('builtins.print')
    def test_warnings_no_exclusions(self, mock_print):
        selected = self.all_packages[0] 
        display_package_resolution_warnings(selected, [], [])
        mock_print.assert_not_called()

    @mock.patch('builtins.print')
    def test_warnings_no_selected_package_with_exclusions(self, mock_print):
        masked_list = [self.all_packages[3]]
        low_prio_list = [self.all_packages[6]]
        display_package_resolution_warnings(None, low_prio_list, masked_list)
        
        mock_print.assert_any_call(f"Info: The following packages were found but are masked: {masked_list}")
        
        low_prio_warning_found = False
        for call_arg_tuple in mock_print.call_args_list:
            args, _ = call_arg_tuple
            if args and "low-priority alternatives" in args[0]:
                low_prio_warning_found = True
                break
        self.assertFalse(low_prio_warning_found, "Low-priority warning should not be printed if selected_package is None")

if __name__ == '__main__':
    unittest.main(verbosity=2)
