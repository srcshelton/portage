import os # For test stub
from portage.config.core import get_low_priority_categories

class Package:
    def __init__(self, name, category="unknown/category", version="0", masked=False):
        self.name = name
        self.category = category
        self.version = version
        self._masked = masked

    def is_masked(self):
        return self._masked

    def __repr__(self):
        # User-friendly representation for warnings
        return f"{self.category}/{self.name}-{self.version}" + (" (masked)" if self._masked else "")

def find_best_match_for_name(packages, name, respect_low_priority_config: bool = True):
    """
    Finds the best match for a given package name, optionally ignoring low-priority settings.
    Raises an error if multiple packages match (ambiguity) or if no package matches.
    Returns a tuple: 
        (selected_package_or_None, 
         low_priority_excluded_packages_list, 
         masked_excluded_packages_list)
    """
    matches = [pkg for pkg in packages if pkg.name == name]
    
    if not matches:
        # If no packages by that name exist at all in the input list.
        raise ValueError(f"No package found with name: {name}")

    masked_excluded_packages_list = [pkg for pkg in matches if pkg.is_masked()]

    # Filter out masked packages first for actual consideration
    unmasked_matches = [pkg for pkg in matches if not pkg.is_masked()]

    if not unmasked_matches:
        # All originally found packages were masked.
        # The masked_excluded_packages_list is already populated with all 'matches'.
        raise ValueError(f"All packages matching '{name}' are masked. Original matches: {masked_excluded_packages_list}")

    # Get low-priority categories
    if respect_low_priority_config:
        low_priority_categories = get_low_priority_categories()
    else:
        low_priority_categories = [] # Effectively treat all categories as normal priority
    
    normal_priority_candidates = []
    low_priority_candidates = [] # Will remain empty if respect_low_priority_config is False

    if respect_low_priority_config:
        for pkg in unmasked_matches:
            if pkg.category in low_priority_categories:
                low_priority_candidates.append(pkg)
            else:
                normal_priority_candidates.append(pkg)
    else:
        # If not respecting low priority config, all unmasked matches are normal priority
        normal_priority_candidates.extend(unmasked_matches)
        # low_priority_candidates list remains empty
    
    # Resolution Logic
    if len(normal_priority_candidates) == 1:
        return normal_priority_candidates[0], low_priority_candidates, masked_excluded_packages_list
    
    if len(normal_priority_candidates) > 1:
        # Ambiguity among normal priority packages
        raise ValueError(f"Ambiguous package name: {name}. Normal priority matches: {normal_priority_candidates}")

    # No normal priority candidates, check low_priority ones
    if not normal_priority_candidates:
        if len(low_priority_candidates) == 1:
            # Only a low-priority one was found. Masked list still relevant.
            return low_priority_candidates[0], [], masked_excluded_packages_list
        
        if len(low_priority_candidates) > 1:
            # Ambiguity among low priority packages
            raise ValueError(f"Ambiguous package name: {name}. Low priority matches: {low_priority_candidates}")
        
        # No normal and no low_priority candidates (e.g. all unmasked were filtered as low_priority but list became empty)
        # This case should ideally be covered if low_priority_candidates was initially populated but then became empty
        # However, if unmasked_matches was populated, and all went to low_priority_candidates,
        # then the checks above (len == 1 or len > 1) handle it.
        # If unmasked_matches was populated but low_priority_candidates is empty AND normal_priority_candidates is empty
        # it implies a logic flaw or an edge case like all categories are low priority but then an empty list is returned.
        # For now, this implies no suitable package.
        raise ValueError(f"No suitable package found for '{name}'. All unmasked candidates were low-priority and resulted in no selection, or other filtering removed them.")

    # Should not be reached if logic is correct, implies an unhandled state.
    # However, all paths should lead to a return or an exception.
    # This could be if normal_priority_candidates is empty, and low_priority_candidates is also empty,
    # but unmasked_matches was not empty.
    # This state means all unmasked packages were filtered out by some criteria not explicitly an error above.
    # For instance, if all unmasked packages were low-priority, and then the low_priority_candidates list was >1 or ==1 or ==0.
    # This is effectively "No package found" after all filtering.
    # If we reach here, it means unmasked_matches was not empty, but after priority filtering, no candidates remained.
    # This implies all unmasked_matches were low_priority, and then were perhaps filtered out (e.g. if low_priority_candidates became empty).
    # Or, normal_priority_candidates was empty, and low_priority_candidates was also empty.
    # The masked_excluded_packages_list is still relevant.
    raise ValueError(f"No package found for '{name}' after all filtering stages. Masked versions found: {masked_excluded_packages_list if masked_excluded_packages_list else 'None'}")

def display_package_resolution_warnings(selected_package, low_priority_excluded, masked_excluded):
    """
    Prints warnings based on excluded packages.
    """
    if masked_excluded:
        print(f"Info: The following packages were found but are masked: {masked_excluded}")

    if selected_package and low_priority_excluded:
        print(f"Info: The selected package '{selected_package}' was chosen over these low-priority alternatives: {low_priority_excluded}")
    
    # If no package was selected, find_best_match_for_name would have raised an error.
    # This function is primarily for post-selection warnings.
    # However, if find_best_match_for_name were to return (None, [], []), this could be a place for a generic "nothing found"
    # but errors are more direct.

# Example Usage (not part of the function, just for testing)
if __name__ == '__main__':
    # Setup for testing get_low_priority_categories (same as before)
    dummy_conf_path = "dummy_low_priority.conf"
    original_config_path = None
    try:
        with open(dummy_conf_path, 'w') as f:
            f.write('LOW_PRIORITY_CATEGORIES="acct-group acct-user"\n')
        import portage.config.core
        original_config_path = portage.config.core.LOW_PRIORITY_CONF_PATH
        portage.config.core.LOW_PRIORITY_CONF_PATH = dummy_conf_path
    except ImportError:
        print("Warning: portage.config.core not found. Using a dummy get_low_priority_categories for testing.")
        def get_low_priority_categories():
            if os.path.exists(dummy_conf_path):
                try:
                    with open(dummy_conf_path, 'r') as f_dummy:
                        for line in f_dummy:
                            if line.startswith("LOW_PRIORITY_CATEGORIES="):
                                val = line.split("=",1)[1].strip().strip('"\'')
                                return val.split()
                except IOError: return ["acct-group", "acct-user"]
            return ["acct-group", "acct-user"]

    all_packages_data = [
        ("pkgcraft", "sys-libs", "1.0", True),
        ("pkgcraft", "sys-libs", "1.1", False),
        ("dummy", "app-admin", "1.0", False),
        ("another", "app-admin", "2.0", True),
        ("another", "app-admin", "2.1", False),
        ("podman", "acct-group", "1.0", False),      # Low priority
        ("podman", "app-containers", "1.0", False), # Normal priority
        ("podman", "dev-python", "1.0", True),      # Masked
        ("lonely", "acct-user", "1.0", False),       # Low priority, only match
        ("ambiglow", "acct-group", "1.0", False),    # Low priority
        ("ambiglow", "acct-user", "1.1", False),     # Low priority
        ("onlylow", "acct-group", "1.0", False),
        ("multimask", "app-foo", "1.0", True),
        ("multimask", "app-foo", "1.1", True),
        ("multimask", "app-foo", "1.2", False),      # Normal one to be selected
        ("multimask", "acct-user", "1.0", False),    # Low prio for multimask
        ("specificmasked", "app-test", "1.0", True) # For fully-qualified masked test
    ]
    all_packages = [Package(n,c,v,m) for n,c,v,m in all_packages_data]

    test_queries = [
        # Short names (existing tests)
        ("pkgcraft", "Standard Resolution"),
        ("dummy", "Single Normal Match"),
        ("podman", "Low Priority Filtering"),
        ("lonely", "Only Low Priority Match"),
        ("ambiglow", "Ambiguity Among Low Priority"),
        ("multimask", "Selection with Masked and Low Priority"),
        ("non-existent", "No Matches"),
        ("onlylow", "Single match, but it's low priority"),
        # Fully-qualified names
        ("app-containers/podman", "Fully-qualified: Select app-containers/podman-1.0"),
        ("sys-libs/pkgcraft", "Fully-qualified: Select sys-libs/pkgcraft-1.1 (unmasked)"),
        ("dev-python/podman", "Fully-qualified: dev-python/podman-1.0 is masked"),
        ("app-test/specificmasked", "Fully-qualified: app-test/specificmasked-1.0 is masked"),
        ("foo/bar", "Fully-qualified: foo/bar not found"),
        ("acct-group/podman", "Fully-qualified: Select acct-group/podman-1.0 (low priority, but specific)"),
    ]

    # Special test for "All Masked" which needs a custom package list
    print("\n--- Test: All Masked (short name) ---")
    only_masked_pkgs = [Package("onlymasked", "app-misc", "1.0", True)]
    try:
        find_best_match_for_name(only_masked_pkgs, "onlymasked")
    except ValueError as e:
        print(f"Error: {e}")
        assert "All packages matching 'onlymasked' are masked" in str(e)

    for query, description in test_queries:
        for respect_flag_val in [True, False]:
            if '/' in query and not respect_flag_val: # Fully qualified tests only run once, flag doesn't change their direct lookup
                continue

            print(f"\n--- Test: {description} (Query: '{query}', RespectLowPrio: {respect_flag_val}) ---")
            
            if '/' in query:
                # Simulate dispatcher handling for fully-qualified names
                cat_query, name_query = query.split('/', 1)
                found_pkg = None
                candidates_for_fq = [p for p in all_packages if p.category == cat_query and p.name == name_query]
                
                if not candidates_for_fq:
                    print(f"Error: Fully-qualified package {query} not found.")
                    continue

                non_masked_fq = [p for p in candidates_for_fq if not p.is_masked()]
                if non_masked_fq:
                    found_pkg = non_masked_fq[0] 
                    print(f"Selected fully-qualified package: {found_pkg}")
                else: 
                    found_pkg = candidates_for_fq[0] 
                    print(f"Error: Fully-qualified package {found_pkg} is masked.")
            else:
                # Handle as a short name, using find_best_match_for_name
                try:
                    match, low_excluded, masked_excluded = find_best_match_for_name(all_packages, query, respect_low_priority_config=respect_flag_val)
                    print(f"Found: {match}, LowPrioExcluded: {low_excluded}, MaskedExcluded: {masked_excluded}")
                    display_package_resolution_warnings(match, low_excluded, masked_excluded)

                    # Specific assertions for changed behavior
                    if query == "podman" and not respect_flag_val:
                        # This case should now be an error, so this path shouldn't be hit.
                        # The error is caught below.
                        assert False, "Podman test with respect_low_priority_config=False should have raised ambiguity error"
                    elif query == "podman" and respect_flag_val:
                         assert match and match.category == "app-containers" # Check specific selection
                         assert any(p.category == "acct-group" for p in low_excluded)


                except ValueError as e:
                    print(f"Error: {e}")
                    if query == "podman" and not respect_flag_val:
                        assert "Normal priority matches" in str(e) # Expect ambiguity among normal
                        assert "app-containers/podman-1.0" in str(e) and "acct-group/podman-1.0" in str(e)
                    elif query == "ambiglow" and not respect_flag_val:
                        # When not respecting low prio, ambiglow (both low prio) should still be ambiguous.
                        # But now they are "Normal priority matches"
                        assert "Normal priority matches" in str(e)
                    elif query == "ambiglow" and respect_flag_val:
                        assert "Low priority matches" in str(e) # Original error type
                    # Other error assertions for non-existent, all_masked etc. can be maintained or added here.
                    elif query == "non-existent":
                         assert "No package found with name" in str(e)



    # Clean up
    if os.path.exists(dummy_conf_path):
        os.remove(dummy_conf_path)
    if original_config_path and 'portage.config.core' in dir():
        portage.config.core.LOW_PRIORITY_CONF_PATH = original_config_path
    print("\nAll tests finished. Dummy config file removed.")
