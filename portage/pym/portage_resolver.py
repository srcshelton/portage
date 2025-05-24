import os # For get_low_priority_categories dependency and general utility
from portage._emerge.config import get_low_priority_categories # Important import

class Package:
    def __init__(self, name, category, version="0", masked=False):
        self.name = name
        self.category = category
        self.version = version # Ensure version is stored
        self.masked = masked

    def is_masked(self): 
        return self.masked

    def __repr__(self):
        # Indicate masked status in repr for clarity in tests/logs
        masked_status = " [M]" if self.masked else "" 
        return f"{self.category}/{self.name}-{self.version}{masked_status}"

    def __eq__(self, other):
        if not isinstance(other, Package):
            return NotImplemented
        return (self.name == other.name and
                self.category == other.category and
                self.version == other.version and
                self.masked == other.masked)

    def __hash__(self):
        return hash((self.name, self.category, self.version, self.masked))

def find_best_match_for_name(name_query, all_packages, respect_low_priority_config=True):
    matches = [pkg for pkg in all_packages if pkg.name == name_query]

    if not matches:
        raise ValueError(f"No package found with name: {name_query}")

    masked_excluded_packages_list = [pkg for pkg in matches if pkg.is_masked()]
    unmasked_matches = [pkg for pkg in matches if not pkg.is_masked()]

    if not unmasked_matches:
        raise ValueError(f"All packages matching '{name_query}' are masked: {masked_excluded_packages_list}")

    low_priority_categories = []
    if respect_low_priority_config:
        low_priority_categories = get_low_priority_categories()
    
    normal_priority_candidates = []
    low_priority_candidates = []
    
    if not respect_low_priority_config: # Treat all as normal if flag is false
        normal_priority_candidates = list(unmasked_matches)
    else:
        for pkg in unmasked_matches:
            if pkg.category in low_priority_categories:
                low_priority_candidates.append(pkg)
            else:
                normal_priority_candidates.append(pkg)

    # Prioritize normal_priority_candidates
    if len(normal_priority_candidates) == 1:
        return (normal_priority_candidates[0], low_priority_candidates, masked_excluded_packages_list)
    
    if len(normal_priority_candidates) > 1:
        raise ValueError(f"Ambiguous package name '{name_query}'. Normal priority matches: {normal_priority_candidates}")

    # No normal_priority_candidates, consider low_priority_candidates
    if len(low_priority_candidates) == 1:
        return (low_priority_candidates[0], [], masked_excluded_packages_list)
        
    if len(low_priority_candidates) > 1:
        raise ValueError(f"Ambiguous package name '{name_query}'. Low priority matches: {low_priority_candidates}")

    # If normal_priority_candidates is empty AND low_priority_candidates is empty,
    # AND unmasked_matches was not empty, it means all unmasked packages were
    # processed but did not result in a selection or ambiguity error above.
    # This typically means all unmasked packages were low-priority, and there were zero of them
    # (e.g. an empty list of low-priority candidates after filtering).
    if not normal_priority_candidates and not low_priority_candidates and unmasked_matches:
        # This implies all unmasked packages were categorized as low-priority (if respect_low_priority_config was true)
        # but the low_priority_candidates list ended up empty. This specific case might indicate
        # that no suitable candidates remained after all filtering.
        # The prompt's version of find_best_match_for_name includes a final fallback return.
        # If this specific state is reached (no normal, no low, but there *were* unmasked matches),
        # it's an edge case meaning no candidates fit the single/multiple criteria.
        # The previous version of this code had a more specific error here.
        # For now, aligning with the prompt's implied fallback.
        pass # Let it fall through to the final return (None, ...)

    # Fallback if somehow no package is selected and no specific error raised prior.
    # This aligns with the function signature in the prompt for this subtask.
    return (None, low_priority_candidates, masked_excluded_packages_list)


def display_package_resolution_warnings(selected_package, low_priority_excluded, masked_excluded):
    if masked_excluded:
        print(f"Info: The following packages were found but are masked: {masked_excluded}")
    
    if selected_package and low_priority_excluded:
        print(f"Info: The selected package '{selected_package}' was chosen over these low-priority alternatives: {low_priority_excluded}")
