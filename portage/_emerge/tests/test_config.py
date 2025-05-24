import unittest
from unittest import mock
import os
import shutil

# Updated import to directly get components from portage._emerge.config
from portage._emerge.config import get_low_priority_categories, DEFAULT_LOW_PRIORITY_CATEGORIES, ENV_VAR_NAME

class TestGetLowPriorityCategories(unittest.TestCase):

    def setUp(self):
        """Set up for test methods."""
        self.test_dir = "test_config_dir_emerge" # Changed to avoid conflict if old tests run
        os.makedirs(self.test_dir, exist_ok=True)
        self.dummy_make_conf_path = os.path.join(self.test_dir, "dummy_make.conf")
        
        # Ensure a clean slate for os.environ for relevant tests
        self.environ_patcher = mock.patch.dict(os.environ, {}, clear=True)
        self.mock_environ = self.environ_patcher.start()
        
        # No longer patching core.LOW_PRIORITY_CONF_PATH as tests pass config_path explicitly

    def tearDown(self):
        """Tear down after test methods."""
        if os.path.exists(self.dummy_make_conf_path):
            os.remove(self.dummy_make_conf_path)
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        
        self.environ_patcher.stop()

    def _write_dummy_conf(self, content):
        with open(self.dummy_make_conf_path, 'w') as f:
            f.write(content)

    # --- Environment Variable Tests ---
    def test_env_var_valid_list(self):
        self.mock_environ[ENV_VAR_NAME] = "env_catA env_catB"
        self.assertEqual(get_low_priority_categories(config_path=self.dummy_make_conf_path), ["env_catA", "env_catB"])

    def test_env_var_empty_string(self):
        self.mock_environ[ENV_VAR_NAME] = ""
        self.assertEqual(get_low_priority_categories(config_path=self.dummy_make_conf_path), [])

    def test_env_var_whitespace_string(self):
        self.mock_environ[ENV_VAR_NAME] = "   "
        self.assertEqual(get_low_priority_categories(config_path=self.dummy_make_conf_path), [])

    def test_env_var_overrides_config_file(self):
        self.mock_environ[ENV_VAR_NAME] = "env_override"
        self._write_dummy_conf(f'{ENV_VAR_NAME}="file_cat1 file_cat2"')
        self.assertEqual(get_low_priority_categories(config_path=self.dummy_make_conf_path), ["env_override"])

    # --- Config File Tests (os.environ is clear due to setUp) ---
    def test_config_file_valid_list(self):
        self._write_dummy_conf(f'{ENV_VAR_NAME}="file_catA file_catB"')
        self.assertEqual(get_low_priority_categories(config_path=self.dummy_make_conf_path), ["file_catA", "file_catB"])

    def test_config_file_single_quotes_and_spaces(self):
        self._write_dummy_conf(f"  {ENV_VAR_NAME}  =  'file_cat_single   file_cat_sq'  ")
        self.assertEqual(get_low_priority_categories(config_path=self.dummy_make_conf_path), ["file_cat_single", "file_cat_sq"])

    def test_config_file_no_variable_defined(self):
        self._write_dummy_conf("SOME_OTHER_VARIABLE=test")
        self.assertEqual(get_low_priority_categories(config_path=self.dummy_make_conf_path), DEFAULT_LOW_PRIORITY_CATEGORIES)

    def test_config_file_malformed_variable_unclosed_quote(self):
        self._write_dummy_conf(f'{ENV_VAR_NAME}="file_cat_malformed') 
        with mock.patch('builtins.print') as mock_print:
            self.assertEqual(get_low_priority_categories(config_path=self.dummy_make_conf_path), DEFAULT_LOW_PRIORITY_CATEGORIES)
            expected_raw_value = '"file_cat_malformed' 
            mock_print.assert_any_call(f"Warning: Category list in {self.dummy_make_conf_path} is not properly quoted. Value: '{expected_raw_value}'. Using defaults.")

    def test_config_file_is_empty(self):
        self._write_dummy_conf("")
        self.assertEqual(get_low_priority_categories(config_path=self.dummy_make_conf_path), DEFAULT_LOW_PRIORITY_CATEGORIES)

    def test_config_file_variable_empty_quotes(self):
        self._write_dummy_conf(f'{ENV_VAR_NAME}=""')
        self.assertEqual(get_low_priority_categories(config_path=self.dummy_make_conf_path), [])

    def test_config_file_variable_whitespace_in_quotes(self):
        self._write_dummy_conf(f'{ENV_VAR_NAME}="   "')
        self.assertEqual(get_low_priority_categories(config_path=self.dummy_make_conf_path), [])
        
    def test_config_file_does_not_exist(self):
        if os.path.exists(self.dummy_make_conf_path):
            os.remove(self.dummy_make_conf_path)
        self.assertEqual(get_low_priority_categories(config_path=self.dummy_make_conf_path), DEFAULT_LOW_PRIORITY_CATEGORIES)

    # --- Default Value Test ---
    def test_default_value_used_when_no_env_and_no_file_var(self):
        self._write_dummy_conf("# Only comments in this file")
        self.assertEqual(get_low_priority_categories(config_path=self.dummy_make_conf_path), DEFAULT_LOW_PRIORITY_CATEGORIES)

    # --- Precedence Test ---
    def test_precedence_env_empty_overrides_file(self):
        self.mock_environ[ENV_VAR_NAME] = "" 
        self._write_dummy_conf(f'{ENV_VAR_NAME}="file_val1 file_val2"')
        self.assertEqual(get_low_priority_categories(config_path=self.dummy_make_conf_path), [])
        
    def test_env_var_multiple_spaces_between_cats(self):
        self.mock_environ[ENV_VAR_NAME] = "env_catA  env_catB   env_catC"
        self.assertEqual(get_low_priority_categories(config_path=self.dummy_make_conf_path), ["env_catA", "env_catB", "env_catC"])

if __name__ == '__main__':
    unittest.main()
