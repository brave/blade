# Note:   Compute discharge
# Author: Kleomenis Katevas (kkatevas@brave.com)
# Date:   06/02/2023

from libs import logger as blade_logger

def compute_power_performance(df):
    # input is a df with columns: timestamp (sec), current (mA), voltage (V)

    if df.timestamp.is_monotonic_increasing is False:
        blade_logger.logger.error("Timestamps are not in increasing order")
        raise ValueError("Timestamps are not in increasing order")

    power = df.current * df.voltage  # in mW
    time_diff = df.timestamp.diff().fillna(0) / 3600  # in hours

    # energy
    energy = power * time_diff  # in mWh
    total_energy_mWh = energy.sum()  # in mWh

    # discharge
    discharge = df.current * time_diff  # in mAh
    total_discharge_mAh = discharge.sum()  # in mAh

    return total_energy_mWh, total_discharge_mAh
