"""
Configuration validation utilities for BESS sizing analysis.
Validates configuration parameters to prevent simulation crashes and ensure valid inputs.
"""


def validate_battery_config(config):
    """
    Validate battery configuration parameters.

    Checks all critical constraints to prevent simulation crashes and
    ensure physically realistic and computationally valid configurations.

    Args:
        config: Configuration dictionary with battery and simulation parameters

    Returns:
        tuple: (is_valid, list_of_error_messages)
            - is_valid: Boolean indicating if configuration is valid
            - list_of_error_messages: List of validation error strings (empty if valid)

    Example:
        >>> config = {'MIN_SOC': 0.95, 'MAX_SOC': 0.05}  # Invalid
        >>> is_valid, errors = validate_battery_config(config)
        >>> print(is_valid)
        False
        >>> print(errors[0])
        'MIN_SOC must be less than MAX_SOC'
    """
    errors = []

    # Critical Validation #1: SOC Limits
    if config['MIN_SOC'] >= config['MAX_SOC']:
        errors.append(
            f"MIN_SOC ({config['MIN_SOC']*100:.0f}%) must be less than "
            f"MAX_SOC ({config['MAX_SOC']*100:.0f}%)"
        )

    if not (0 <= config['MIN_SOC'] <= 1):
        errors.append(f"MIN_SOC must be between 0 and 1 (got {config['MIN_SOC']})")

    if not (0 <= config['MAX_SOC'] <= 1):
        errors.append(f"MAX_SOC must be between 0 and 1 (got {config['MAX_SOC']})")

    # Critical Validation #2: Battery Size Range
    if config['MIN_BATTERY_SIZE_MWH'] >= config['MAX_BATTERY_SIZE_MWH']:
        errors.append(
            f"MIN_BATTERY_SIZE ({config['MIN_BATTERY_SIZE_MWH']} MWh) must be less than "
            f"MAX_BATTERY_SIZE ({config['MAX_BATTERY_SIZE_MWH']} MWh)"
        )

    if config['MIN_BATTERY_SIZE_MWH'] <= 0:
        errors.append(f"MIN_BATTERY_SIZE must be positive (got {config['MIN_BATTERY_SIZE_MWH']} MWh)")

    if config['BATTERY_SIZE_STEP_MWH'] <= 0:
        errors.append(f"BATTERY_SIZE_STEP must be positive (got {config['BATTERY_SIZE_STEP_MWH']} MWh)")

    # Critical Validation #3: Efficiency
    if not (0 < config['ROUND_TRIP_EFFICIENCY'] <= 1):
        errors.append(
            f"Round-trip efficiency must be between 0 and 1 "
            f"(got {config['ROUND_TRIP_EFFICIENCY']*100:.1f}%)"
        )

    # Critical Validation #4: C-Rates
    if config['C_RATE_CHARGE'] <= 0:
        errors.append(f"C-Rate Charge must be positive (got {config['C_RATE_CHARGE']})")

    if config['C_RATE_DISCHARGE'] <= 0:
        errors.append(f"C-Rate Discharge must be positive (got {config['C_RATE_DISCHARGE']})")

    # Critical Validation #5: Degradation
    if config['DEGRADATION_PER_CYCLE'] < 0:
        errors.append(f"Degradation per cycle cannot be negative (got {config['DEGRADATION_PER_CYCLE']})")

    # Critical Validation #6: Initial SOC within limits
    if 'INITIAL_SOC' in config:
        if not (config['MIN_SOC'] <= config['INITIAL_SOC'] <= config['MAX_SOC']):
            errors.append(
                f"INITIAL_SOC ({config['INITIAL_SOC']*100:.0f}%) must be between "
                f"MIN_SOC ({config['MIN_SOC']*100:.0f}%) and MAX_SOC ({config['MAX_SOC']*100:.0f}%)"
            )

    # Critical Validation #7: Target Delivery
    if config['TARGET_DELIVERY_MW'] <= 0:
        errors.append(f"Target delivery must be positive (got {config['TARGET_DELIVERY_MW']} MW)")

    # Critical Validation #8: Solar Capacity
    if config['SOLAR_CAPACITY_MW'] <= 0:
        errors.append(f"Solar capacity must be positive (got {config['SOLAR_CAPACITY_MW']} MW)")

    # Critical Validation #9: Max Daily Cycles
    if config['MAX_DAILY_CYCLES'] <= 0:
        errors.append(f"Max daily cycles must be positive (got {config['MAX_DAILY_CYCLES']})")

    # Critical Validation #10: Optimization Parameters
    if config['MARGINAL_IMPROVEMENT_THRESHOLD'] <= 0:
        errors.append(
            f"Marginal improvement threshold must be positive "
            f"(got {config['MARGINAL_IMPROVEMENT_THRESHOLD']})"
        )

    if config['MARGINAL_INCREMENT_MWH'] <= 0:
        errors.append(
            f"Marginal increment must be positive (got {config['MARGINAL_INCREMENT_MWH']} MWh)"
        )

    # Return validation result
    is_valid = len(errors) == 0
    return is_valid, errors
