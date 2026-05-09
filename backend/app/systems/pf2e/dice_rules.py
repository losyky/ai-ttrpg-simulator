"""PF2e four-degree success determination."""

from __future__ import annotations


def determine_success(total: int, dc: int, natural: int = 0) -> str:
    """PF2e four-degree success system.
    
    Args:
        total: Total roll result (including modifiers)
        dc: Difficulty class
        natural: The natural d20 roll (for nat 20/1 adjustment)
    
    Returns:
        Success level string or empty string if dc <= 0.
    """
    if dc <= 0:
        return ""
    diff = total - dc
    if diff >= 10:
        success = "critical_success"
    elif diff >= 0:
        success = "success"
    elif diff >= -10:
        success = "failure"
    else:
        success = "critical_failure"

    levels = ["critical_failure", "failure", "success", "critical_success"]
    idx = levels.index(success)
    
    if natural == 20:
        success = levels[min(idx + 1, 3)]
    elif natural == 1:
        success = levels[max(idx - 1, 0)]
    
    return success
