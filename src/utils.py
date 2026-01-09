"""
Utility functions for AmFIBia application.
"""


def format_current(current_A):
    """
    Format a current value (in Amperes) with appropriate unit.
    Returns string like "150 pA", "1.5 nA", "2.3 µA", etc.
    """
    if current_A == 0:
        return "Not set"
    
    abs_current = abs(current_A)
    
    if abs_current < 0.1e-9:  # Less than 0.1 nA -> use pA
        value = current_A * 1e12
        unit = "pA"
    elif abs_current <= 100e-9:  # Up to 100 nA -> use nA
        value = current_A * 1e9
        unit = "nA"
    elif abs_current < 10e-6:  # Less than 10 µA -> use µA
        value = current_A * 1e6
        unit = "µA"
    elif abs_current < 10e-3:  # Less than 10 mA -> use mA
        value = current_A * 1e3
        unit = "mA"
    else:  # Use A
        value = current_A
        unit = "A"
    
    # Format: use decimal if needed, otherwise integer
    if value == int(value):
        return f"{int(value)} {unit}"
    else:
        return f"{value:.2g} {unit}"
