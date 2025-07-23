# Note:   Compute discharge
# Author: Kleomenis Katevas (kkatevas@brave.com)
# Date:   06/02/2023

from libs import logger as blade_logger

def compute_power_performance(df, timestamp_col='timestamp', current_col='current (mA)', voltage_col='voltage (V)'):
    # input is a df with columns for timestamp, current, voltage
    # column names can be customized via parameters
    
    # Check if the specified columns exist, if not try alternative columns
    if current_col not in df.columns:
        if 'current' in df.columns:
            current_col = 'current'
        else:
            blade_logger.logger.error(f"Error: Neither '{current_col}' nor 'current' columns found in dataframe")
            raise ValueError(f"Neither '{current_col}' nor 'current' columns found in dataframe")
    
    if voltage_col not in df.columns:
        if 'voltage' in df.columns:
            voltage_col = 'voltage'
        else:
            blade_logger.logger.error(f"Error: Neither '{voltage_col}' nor 'voltage' columns found in dataframe")
            raise ValueError(f"Neither '{voltage_col}' nor 'voltage' columns found in dataframe")

    if df[timestamp_col].is_monotonic_increasing is False:
        blade_logger.logger.error("Timestamps are not in increasing order")
        raise ValueError("Timestamps are not in increasing order")

    power = df[current_col] * df[voltage_col]  # in mW
    time_diff = df[timestamp_col].diff().fillna(0) / 3600  # in hours

    # energy
    energy = power * time_diff  # in mWh
    total_energy_mWh = energy.sum()  # in mWh

    # discharge
    discharge = df[current_col] * time_diff  # in mAh
    total_discharge_mAh = discharge.sum()  # in mAh

    return total_energy_mWh, total_discharge_mAh
