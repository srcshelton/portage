import os
import shlex

# Configuration constants
LOW_PRIORITY_CONF_PATH = "/etc/portage/make.conf"
DEFAULT_LOW_PRIORITY_CATEGORIES = ["acct-user", "acct-group", "app-alternatives", "virtual"]
ENV_VAR_NAME = "LOW_PRIORITY_CATEGORIES"

def get_low_priority_categories(config_path=LOW_PRIORITY_CONF_PATH):
    """
    Reads low-priority categories based on precedence:
    1. Environment variable (ENV_VAR_NAME).
    2. Configuration file (e.g., make.conf at config_path).
    3. Default list.

    Args:
        config_path (str): The path to the configuration file.

    Returns:
        list[str]: A list of low-priority category strings.
    """
    # 1. Check Environment Variable
    env_value = os.getenv(ENV_VAR_NAME)
    if env_value is not None:  # Env var is set
        if env_value.strip():  # Env var is not empty or just whitespace
            # Parse env var (simple space-separated string)
            return [cat for cat in env_value.split(' ') if cat]
        else:
            # Env var is set but empty or whitespace-only, means an empty list.
            return []

    # 2. Check Configuration File (if env var was not set)
    categories_line_from_file = None
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                for line_content in f:
                    stripped_line = line_content.strip()
                    if not stripped_line or stripped_line.startswith('#'):
                        continue
                    parts = stripped_line.split('=', 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        if key == ENV_VAR_NAME: # Use ENV_VAR_NAME for consistency
                            categories_line_from_file = stripped_line
                            break
            
            if categories_line_from_file:
                assign_split = categories_line_from_file.split('=', 1)
                if len(assign_split) < 2: # Should not happen if key was found
                    print(f"Warning: Malformed line (unexpected format) in {config_path}: '{categories_line_from_file}'. Using defaults.")
                    return DEFAULT_LOW_PRIORITY_CATEGORIES
                
                raw_value = assign_split[1].strip()
                is_double_quoted = raw_value.startswith('"') and raw_value.endswith('"')
                is_single_quoted = raw_value.startswith("'") and raw_value.endswith("'")

                if is_double_quoted or is_single_quoted:
                    value_to_parse = raw_value[1:-1]
                else:
                    print(f"Warning: Category list in {config_path} is not properly quoted. Value: '{raw_value}'. Using defaults.")
                    return DEFAULT_LOW_PRIORITY_CATEGORIES

                parsed_categories = value_to_parse.split()
                if not all(isinstance(cat, str) for cat in parsed_categories): # Should always be true
                    print(f"Warning: Malformed category list content in {config_path}. Using defaults.")
                    return DEFAULT_LOW_PRIORITY_CATEGORIES
                
                valid_categories = [cat for cat in parsed_categories if cat]
                if not valid_categories and value_to_parse.strip(): # Content was non-empty whitespace
                    print(f"Warning: Parsed categories list is empty from a non-empty whitespace string in {config_path}. Value: '{raw_value}'. Using defaults.")
                    return DEFAULT_LOW_PRIORITY_CATEGORIES
                return valid_categories
            else:
                # Variable not found in the file, fall through to default
                pass
        except IOError as e:
            print(f"Warning: Could not read {config_path}: {e}. Using defaults.")
            # Fall through to default
        except Exception as e:
            print(f"Warning: Error parsing {config_path}: {e}. Using defaults.")
            # Fall through to default
    
    # 3. Default Value
    return DEFAULT_LOW_PRIORITY_CATEGORIES

if __name__ == '__main__':
    dummy_make_conf_path = "dummy_make.conf" 
    original_env_var_value = os.getenv(ENV_VAR_NAME)

    def run_test(test_name, env_value_to_set, config_file_content, expected_cats, config_file_path_override=dummy_make_conf_path):
        print(f"--- Test: {test_name} ---")
        
        current_env_for_test = os.getenv(ENV_VAR_NAME)
        # Set environment variable for the test
        if env_value_to_set is None:
            if ENV_VAR_NAME in os.environ:
                del os.environ[ENV_VAR_NAME]
        else:
            os.environ[ENV_VAR_NAME] = env_value_to_set
        
        # Create/remove dummy config file
        if config_file_content is None:
            if os.path.exists(config_file_path_override):
                os.remove(config_file_path_override)
        else:
            with open(config_file_path_override, 'w') as f:
                f.write(config_file_content)
        
        # For debugging, print what os.getenv will see INSIDE the function call
        effective_env_val = os.getenv(ENV_VAR_NAME)
        
        cats = get_low_priority_categories(config_path=config_file_path_override)
        
        print(f"Env Var ('{ENV_VAR_NAME}') for test was: '{env_value_to_set}' (effective as: '{effective_env_val}')")
        print(f"Config File ('{config_file_path_override}') Content: {'Present with content' if config_file_content else 'None or Not Present'}")
        if config_file_content: print(f"   Content: \"{config_file_content.strip()}\"")
        print(f"Returned Categories: {cats}")
        print(f"Expected Categories: {expected_cats}")
        assert cats == expected_cats, f"Test '{test_name}' Failed: Expected {expected_cats}, got {cats}"
        print("-" * 30)

    # Test Scenarios:
    # 1. Env var set and not empty (overrides file)
    run_test("Env var set (overrides file)", "env_cat1 env_cat2", f'{ENV_VAR_NAME}="file_cat1"', ["env_cat1", "env_cat2"])

    # 2. Env var set to empty string (results in empty list, overrides file)
    run_test("Env var set to empty string", "", f'{ENV_VAR_NAME}="file_cat1"', [])

    # 3. Env var set to whitespace string (results in empty list, overrides file)
    run_test("Env var set to whitespace", "   ", f'{ENV_VAR_NAME}="file_cat1"', [])
    
    # 4. Env var not set, config file used
    run_test("Env var unset, config file used", None, f'{ENV_VAR_NAME}="file_cat1 file_cat2"', ["file_cat1", "file_cat2"])

    # 5. Env var not set, config file present but var not defined
    run_test("Env var unset, config file no var", None, 'OTHER_VAR="test"', DEFAULT_LOW_PRIORITY_CATEGORIES)

    # 6. Env var not set, config file present, var malformed (e.g. no closing quote)
    run_test("Env var unset, config file malformed var", None, f'{ENV_VAR_NAME}="file_cat1', DEFAULT_LOW_PRIORITY_CATEGORIES)

    # 7. Env var not set, config file present, var is empty string in quotes
    run_test("Env var unset, config file empty var quotes", None, f'{ENV_VAR_NAME}=""', [])
    
    # 8. Env var not set, config file present, var is whitespace in quotes
    run_test("Env var unset, config file whitespace var quotes", None, f'{ENV_VAR_NAME}="   "', [])

    # 9. Env var not set, config file does not exist
    run_test("Env var unset, config file non-existent", None, None, DEFAULT_LOW_PRIORITY_CATEGORIES, config_file_path_override="non_existent_dummy_make.conf")

    # 10. Env var not set, config file used (single quotes and mixed spaces)
    run_test("Env var unset, config file single quotes", None, f"  {ENV_VAR_NAME} =  'media-sound   sci-libs'  \n", ["media-sound", "sci-libs"])
    
    # 11. Env var not set, config file exists but is empty
    run_test("Env var unset, config file empty", None, "", DEFAULT_LOW_PRIORITY_CATEGORIES)


    # Restore original environment variable state and clean up dummy file
    if original_env_var_value is None:
        if ENV_VAR_NAME in os.environ:
            del os.environ[ENV_VAR_NAME]
    else:
        os.environ[ENV_VAR_NAME] = original_env_var_value
    
    if os.path.exists(dummy_make_conf_path):
        os.remove(dummy_make_conf_path)
    if os.path.exists("non_existent_dummy_make.conf"): # Should not exist, but clean if it does
        os.remove("non_existent_dummy_make.conf")

    print("All tests finished. Dummy file removed, environment restored.")
