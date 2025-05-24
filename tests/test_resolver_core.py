import unittest
from unittest import mock
import os

# Assuming 'portage' is in PYTHONPATH
from portage.resolver.core import Package, find_best_match_for_name, display_package_resolution_warnings
# We need to import portage.config.core to be able to mock a function within it.
import portage.config.core 

# Define constants for problematic categories to ensure object identity if needed
CAT_LOW1 = "cat-low1"
CAT_LOW2 = "cat-low2"

class TestResolverCore(unittest.TestCase):

    def setUp(self):
        """Set up a common set of packages for testing."""
        self.packages_data = [
            # name, category, version, masked
            ("pkgA", "cat1", "1.0", False),      # 0: Normal
            ("pkgA", "cat1", "0.9", False),      # 1: Normal, older (Note: find_best_match currently doesn't differentiate by version, would cause ambiguity)
            ("pkgA", "cat2", "1.0", False),      # 2: Normal, different cat for pkgA
            ("pkgB", "cat1", "1.0", True),       # 3: Masked
            ("pkgC", "cat-low", "1.0", False),   # 4: Potentially low priority
            ("pkgD", "cat-normal", "1.0", False),# 5: Normal
            ("pkgD", "cat-low", "1.0", False),   # 6: Potentially low priority for pkgD
            ("pkgE", "cat-low", "1.0", True),    # 7: Masked and low priority
            ("pkgE", "cat-low", "1.1", False),   # 8: Low priority, unmasked
            ("pkgF", "cat-normal", "1.0", False),# 9: Single normal match
            ("pkgG", CAT_LOW1, "1.0", False),    # 10: Ambiguity among low-priority (use constant)
            ("pkgG", CAT_LOW2, "1.0", False),    # 11: Ambiguity among low-priority (use constant)
            ("pkgH", "cat-normal", "1.0", True), # 12: All masked scenario
            ("pkgH", "cat-normal", "1.1", True), # 13: All masked scenario
            ("pkgI", "cat-normal", "1.0", False),# 14: For respect_low_priority_config=False test
            ("pkgI", "cat-low", "1.1", False)    # 15: For respect_low_priority_config=False test
        ]
        self.all_packages = [Package(n, c, v, m) for n, c, v, m in self.packages_data]
        
        # This default list is used by mocks if not overridden per-test
        self.mock_default_low_prio_categories = ["cat-low", CAT_LOW1, CAT_LOW2]


    # --- Tests for find_best_match_for_name ---

    @mock.patch('portage.resolver.core.get_low_priority_categories')
    def test_no_package_found(self, mock_get_low_prio):
        mock_get_low_prio.return_value = self.mock_default_low_prio_categories
        with self.assertRaisesRegex(ValueError, "No package found with name: nonExistent"):
            find_best_match_for_name(self.all_packages, "nonExistent")

    @mock.patch('portage.resolver.core.get_low_priority_categories')
    def test_single_normal_match(self, mock_get_low_prio):
        mock_get_low_prio.return_value = self.mock_default_low_prio_categories
        selected, low_excluded, masked_excluded = find_best_match_for_name(self.all_packages, "pkgF")
        self.assertEqual(selected, self.all_packages[9])
        self.assertEqual(low_excluded, [])
        self.assertEqual(masked_excluded, [])

    @mock.patch('portage.resolver.core.get_low_priority_categories')
    def test_only_match_is_masked(self, mock_get_low_prio):
        mock_get_low_prio.return_value = self.mock_default_low_prio_categories
        specific_packages = [self.all_packages[3]] # pkgB, cat1, 1.0, True
        with self.assertRaisesRegex(ValueError, "All packages matching 'pkgB' are masked"):
            find_best_match_for_name(specific_packages, "pkgB")

    @mock.patch('portage.resolver.core.get_low_priority_categories')
    def test_all_matches_are_masked(self, mock_get_low_prio):
        mock_get_low_prio.return_value = self.mock_default_low_prio_categories
        specific_packages = [self.all_packages[12], self.all_packages[13]] # pkgH versions, all masked
        with self.assertRaisesRegex(ValueError, "All packages matching 'pkgH' are masked"):
            find_best_match_for_name(specific_packages, "pkgH")
        try:
            find_best_match_for_name(specific_packages, "pkgH")
        except ValueError as e:
            self.assertIn(str(self.all_packages[12]), str(e))
            self.assertIn(str(self.all_packages[13]), str(e))

    @mock.patch('portage.resolver.core.get_low_priority_categories')
    def test_selection_among_masked_and_unmasked(self, mock_get_low_prio):
        mock_get_low_prio.return_value = self.mock_default_low_prio_categories # "cat-low" is low
        # pkgE: cat-low/1.0 (masked, low), cat-low/1.1 (unmasked, low)
        selected, low_excluded, masked_excluded = find_best_match_for_name(self.all_packages, "pkgE")
        self.assertEqual(selected, self.all_packages[8]) # cat-low/pkgE-1.1
        self.assertEqual(low_excluded, []) # Selected is low-prio, so nothing excluded *in favor* of it
        self.assertListEqual(masked_excluded, [self.all_packages[7]])

    @mock.patch('portage.resolver.core.get_low_priority_categories')
    def test_normal_selected_over_low_priority(self, mock_get_low_prio):
        mock_get_low_prio.return_value = self.mock_default_low_prio_categories # "cat-low" is low
        # pkgD: cat-normal/1.0, cat-low/1.0
        selected, low_excluded, masked_excluded = find_best_match_for_name(self.all_packages, "pkgD")
        self.assertEqual(selected, self.all_packages[5]) # cat-normal/pkgD-1.0
        self.assertListEqual(low_excluded, [self.all_packages[6]]) # cat-low/pkgD-1.0 excluded
        self.assertEqual(masked_excluded, [])

    @mock.patch('portage.resolver.core.get_low_priority_categories')
    def test_low_priority_selected_if_no_normal(self, mock_get_low_prio):
        mock_get_low_prio.return_value = self.mock_default_low_prio_categories # "cat-low" is low
        # pkgC: cat-low/1.0 (only match for pkgC)
        selected, low_excluded, masked_excluded = find_best_match_for_name(self.all_packages, "pkgC")
        self.assertEqual(selected, self.all_packages[4])
        self.assertEqual(low_excluded, [])
        self.assertEqual(masked_excluded, [])

    @mock.patch('portage.resolver.core.get_low_priority_categories')
    def test_ambiguity_among_normal_priority(self, mock_get_low_prio):
        mock_get_low_prio.return_value = [CAT_LOW1, CAT_LOW2] # Make cat1, cat2 normal
        # Using pkgA: cat1/1.0, cat1/0.9 (name collision), cat2/1.0
        # Current find_best_match_for_name does not consider version for ambiguity if name/cat matches.
        # Let's use truly ambiguous ones for this test:
        ambiguous_pkgs = [
            Package("pkgAmb", "cat1", "1.0"),
            Package("pkgAmb", "cat2", "1.0") 
        ]
        with self.assertRaisesRegex(ValueError, "Ambiguous package name: pkgAmb. Normal priority matches:"):
            find_best_match_for_name(ambiguous_pkgs, "pkgAmb")

    @mock.patch('portage.resolver.core.get_low_priority_categories')
    def test_ambiguity_among_low_priority(self, mock_get_low_prio):
        mock_get_low_prio.return_value = self.mock_default_low_prio_categories # CAT_LOW1, CAT_LOW2 are low
        # pkgG: CAT_LOW1/1.0, CAT_LOW2/1.0
        # This is the problematic test.
        # Expected: "Low priority matches"
        # Actual (from previous runs): "Normal priority matches" indicating mock/logic issue for these specific strings
        with self.assertRaisesRegex(ValueError, "Ambiguous package name: pkgG. Low priority matches:"):
            find_best_match_for_name(self.all_packages, "pkgG")
        mock_get_low_prio.assert_called_once()


    @mock.patch('portage.resolver.core.get_low_priority_categories')
    def test_respect_low_priority_config_false(self, mock_get_low_prio):
        # pkgI: cat-normal/1.0, cat-low/1.1
        # When respect_low_priority_config=False, both are normal, causing ambiguity
        with self.assertRaisesRegex(ValueError, "Ambiguous package name: pkgI. Normal priority matches:"):
            find_best_match_for_name(self.all_packages, "pkgI", respect_low_priority_config=False)
        mock_get_low_prio.assert_not_called() # Crucially, get_low_priority_categories shouldn't be called

    # --- Tests for display_package_resolution_warnings ---

    @mock.patch('builtins.print')
    def test_warnings_masked_only(self, mock_print):
        selected = self.all_packages[0] # cat1/pkgA-1.0
        masked_list = [self.all_packages[3]] # cat1/pkgB-1.0 (masked)
        display_package_resolution_warnings(selected, [], masked_list)
        mock_print.assert_any_call(f"Info: The following packages were found but are masked: {masked_list}")

    @mock.patch('builtins.print')
    def test_warnings_low_prio_only(self, mock_print):
        selected = self.all_packages[5]    # cat-normal/pkgD-1.0
        low_prio_list = [self.all_packages[6]] # cat-low/pkgD-1.0
        display_package_resolution_warnings(selected, low_prio_list, [])
        mock_print.assert_any_call(f"Info: The selected package '{selected}' was chosen over these low-priority alternatives: {low_prio_list}")

    @mock.patch('builtins.print')
    def test_warnings_both_masked_and_low_prio(self, mock_print):
        selected = self.all_packages[5]    # cat-normal/pkgD-1.0
        low_prio_list = [self.all_packages[6]] # cat-low/pkgD-1.0
        masked_list = [self.all_packages[3]]   # cat1/pkgB-1.0 (masked)
        display_package_resolution_warnings(selected, low_prio_list, masked_list)
        mock_print.assert_any_call(f"Info: The following packages were found but are masked: {masked_list}")
        mock_print.assert_any_call(f"Info: The selected package '{selected}' was chosen over these low-priority alternatives: {low_prio_list}")

    @mock.patch('builtins.print')
    def test_warnings_no_exclusions(self, mock_print):
        selected = self.all_packages[0] # cat1/pkgA-1.0
        display_package_resolution_warnings(selected, [], [])
        mock_print.assert_not_called()

    @mock.patch('builtins.print')
    def test_warnings_no_selected_package_with_exclusions(self, mock_print):
        # This scenario implies an error was raised before selection, but if lists were populated.
        masked_list = [self.all_packages[3]]
        low_prio_list = [self.all_packages[6]]
        display_package_resolution_warnings(None, low_prio_list, masked_list)
        
        # Only masked warning should print if no selected package
        mock_print.assert_any_call(f"Info: The following packages were found but are masked: {masked_list}")
        
        # Check that the low-priority warning (which requires a selected_package) was NOT called
        # by iterating through calls, as assert_any_call would be true if only masked was called.
        low_prio_warning_found = False
        for call_arg_tuple in mock_print.call_args_list:
            args, _ = call_arg_tuple
            if args and "low-priority alternatives" in args[0]:
                low_prio_warning_found = True
                break
        self.assertFalse(low_prio_warning_found, "Low-priority warning should not be printed if selected_package is None")

if __name__ == '__main__':
    unittest.main(verbosity=2)
