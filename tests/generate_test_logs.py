import pandas as pd
import numpy as np
import os

def generate_normal_data(n=100):
    np.random.seed(42)
    return pd.DataFrame({
        "Board_ID": [f"N{str(i).zfill(3)}" for i in range(1, n+1)],
        "Voltage_Input_V": np.random.normal(12.0, 0.05, n),
        "Voltage_5V_Out": np.random.normal(5.0, 0.02, n),
        "Voltage_3V3_Out": np.random.normal(3.3, 0.015, n),
        "Ripple_5V_mV": np.random.normal(12, 2, n),
        "Ripple_3V3_mV": np.random.normal(8, 1.5, n),
        "Current_Draw_mA": np.random.normal(145, 5, n),
        "Temperature_Reg_C": np.random.normal(42, 2, n),
        "Clock_Freq_MHz": np.random.normal(16.0, 0.0005, n)
    })

def generate_faulty_data(n_normal=80, n_faulty=20):
    df = generate_normal_data(n_normal)
    df["Board_ID"] = [f"F{str(i).zfill(3)}" for i in range(1, n_normal+1)]
    
    # Generate anomalies
    np.random.seed(99)
    # 1. Thermal Runaway (High Temp, High Current, Voltage Drop)
    f1 = pd.DataFrame({
        "Board_ID": [f"F-T{str(i).zfill(2)}" for i in range(1, 6)],
        "Voltage_Input_V": np.random.normal(12.0, 0.05, 5),
        "Voltage_5V_Out": np.random.normal(4.2, 0.1, 5), # Voltage sag
        "Voltage_3V3_Out": np.random.normal(3.25, 0.05, 5),
        "Ripple_5V_mV": np.random.normal(150, 20, 5), # High ripple
        "Ripple_3V3_mV": np.random.normal(30, 5, 5),
        "Current_Draw_mA": np.random.normal(320, 15, 5), # High current
        "Temperature_Reg_C": np.random.normal(85, 5, 5), # Thermal runaway
        "Clock_Freq_MHz": np.random.normal(15.99, 0.005, 5)
    })
    
    # 2. Clock Drift (only clock is off)
    f2 = pd.DataFrame({
        "Board_ID": [f"F-C{str(i).zfill(2)}" for i in range(1, 6)],
        "Voltage_Input_V": np.random.normal(12.0, 0.05, 5),
        "Voltage_5V_Out": np.random.normal(5.0, 0.02, 5),
        "Voltage_3V3_Out": np.random.normal(3.3, 0.015, 5),
        "Ripple_5V_mV": np.random.normal(12, 2, 5),
        "Ripple_3V3_mV": np.random.normal(8, 1.5, 5),
        "Current_Draw_mA": np.random.normal(145, 5, 5),
        "Temperature_Reg_C": np.random.normal(42, 2, 5),
        "Clock_Freq_MHz": np.random.normal(14.5, 0.2, 5) # Severe clock drift
    })
    
    # 3. Input Overvoltage (Input high, regulators surviving but hot)
    f3 = pd.DataFrame({
        "Board_ID": [f"F-V{str(i).zfill(2)}" for i in range(1, 11)],
        "Voltage_Input_V": np.random.normal(15.5, 0.5, 10), # High Input VR
        "Voltage_5V_Out": np.random.normal(5.1, 0.05, 10),
        "Voltage_3V3_Out": np.random.normal(3.35, 0.05, 10),
        "Ripple_5V_mV": np.random.normal(30, 5, 10),
        "Ripple_3V3_mV": np.random.normal(15, 3, 10),
        "Current_Draw_mA": np.random.normal(160, 10, 10),
        "Temperature_Reg_C": np.random.normal(65, 4, 10), # Hot due to dissipation
        "Clock_Freq_MHz": np.random.normal(16.0, 0.0005, 10)
    })
    
    return pd.concat([df, f1, f2, f3], ignore_index=True)

if __name__ == "__main__":
    os.makedirs(r"c:\Users\sriha\OneDrive\Desktop\TN IMPACT\data", exist_ok=True)
    normal_df = generate_normal_data(100)
    normal_df.to_csv(r"c:\Users\sriha\OneDrive\Desktop\TN IMPACT\data\synthetic_testlog_normal.csv", index=False)
    
    faulty_df = generate_faulty_data(80, 20)
    faulty_df.to_csv(r"c:\Users\sriha\OneDrive\Desktop\TN IMPACT\data\synthetic_testlog_faulty.csv", index=False)
    
    print("Successfully generated synthetic test datasets in the data folder.")
