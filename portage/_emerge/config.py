import os

DEFAULT_LOW_PRIORITY_CATEGORIES = ["acct-user", "acct-group", "app-alternatives", "virtual"]
# Note: LOW_PRIORITY_CONF_PATH is effectively replaced by the config_path parameter default.
# ENV_VAR_NAME is 'LOW_PRIORITY_CATEGORIES' by convention from the function body.

def get_low_priority_categories(config_path="/etc/portage/make.conf"):
    '''
    Retrieves the list of low-priority categories.
    Precedence: Environment variable > Config file > Default.
    '''
    env_var_value = os.getenv('LOW_PRIORITY_CATEGORIES')

    if env_var_value is not None: # Environment variable is set
        if env_var_value.strip(): # Not empty or just whitespace
            # Split by space, and filter out potential empty strings if multiple spaces were used
            return [cat for cat in env_var_value.split(' ') if cat]
        else: # Empty or whitespace only
            return [] # Explicitly no low-priority categories

    # Environment variable not set, try config file
    categories_line_from_file_found = False
    parsed_categories_from_file = [] # Default to empty if key found but value is empty

    try:
        if os.path.exists(config_path): # Only attempt to open if file exists
            with open(config_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('#') or not line: # Skip comments and empty lines
                        continue
                    
                    parts = line.split('=', 1)
                    if len(parts) == 2:
                        key, value_str = parts[0].strip(), parts[1].strip()
                        if key == 'LOW_PRIORITY_CATEGORIES':
                            categories_line_from_file_found = True # Mark as found
                            # Remove outer quotes (single or double)
                            if (value_str.startswith('"') and value_str.endswith('"')) or \
                               (value_str.startswith("'") and value_str.endswith("'")):
                                value_str = value_str[1:-1]
                            
                            if value_str.strip(): # Not empty or just whitespace after stripping quotes
                                # Split by space, and filter out potential empty strings
                                parsed_categories_from_file = [cat for cat in value_str.split(' ') if cat]
                            else: # Empty or whitespace only after stripping quotes
                                parsed_categories_from_file = [] 
                            # Found the variable, process this line and stop.
                            break 
            
        if categories_line_from_file_found:
            return parsed_categories_from_file
            
    except IOError:
        # File not found (should be caught by os.path.exists, but good for safety) or other IO error
        # print(f"Warning: Could not read {config_path}. Using default low-priority categories.") # Optional warning
        pass # Fall through to default
    except Exception as e:
        # Handle other potential errors during parsing
        # print(f"Warning: Error parsing {config_path}: {e}. Using default low-priority categories.") # Optional warning
        pass # Fall through to default
        
    # Fall through to default if:
    # - Env var not set
    # - Config file does not exist
    # - Config file exists but LOW_PRIORITY_CATEGORIES not found in it
    # - IOError or other Exception during file processing
    return DEFAULT_LOW_PRIORITY_CATEGORIES
