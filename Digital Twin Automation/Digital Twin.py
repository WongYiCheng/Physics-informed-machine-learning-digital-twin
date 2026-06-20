import numpy as np
import joblib
import os
import time
import pandas as pd

# Import your custom modules
import daq_system           # Module 1: NI-DAQ & Dashboard
import feature_extractor    # Module 2: PCA, WCC, Ratios
import ansys_twin           # Module 3: Older Version (would not be used anymore)
import ansys_twin_updated     # Updated Ansys Twin with better process management

# --- 1. INITIALIZATION & LOADING ---
# Load your pre-trained Random Forest and your Healthy Baseline
joblib_name = 'HD'
rf_model = joblib.load(f'Machine Learning Algorithm\\{joblib_name}_damage_rf_model.pkl')
scaler = joblib.load(f'Machine Learning Algorithm\\{joblib_name}_damage_scaler.pkl') # Keep if you used X_train_scaled
s_baseline = np.load(f'PCA Feature Extraction\\healthy_slope_baseline_{joblib_name}.npy') 

print("Model, Scaler, and Baseline Loaded Successfully.")

# Paths for Ansys (required to ensure where's the ANSYS file to be called out)
DB_PATH = r"D:\UM Document\FYP ansys\Remote copy\Remote Copy_files\dp8\global\MECH\SYS.mechdb"
EXEC_LOC = r"C:\Program Files\ANSYS Inc\v252\aisol\Bin\winx64\AnsysWBU.exe"

print("--- Initializing Digital Twin System ---")


# --- 2. THE MAIN AUTOMATION  ---
def run_digital_twin():
    try:
        print("\n>>> STARTING: Single Impact Capture & Update...")

        # STEP A: Data Acquisition (Wait for one trigger)
        raw_data, bias_vals = daq_system.acquire_impact_data() # 9,2049

        # STEP B: Signal Processing
        freqs, frf_complex, f_time, a_time = daq_system.compute_frf(raw_data, bias_vals)

        # STEP C: Interactive Validation
        if not daq_system.plot_validation(freqs, frf_complex, f_time, a_time):
            print("Hit rejected. Exiting without update.")
            return # Exit the function early

        # STEP D: Feature Extraction
        frf_abs = np.abs(frf_complex[:, 20:401])  # Ensure we have the correct shape, we need 100-200 Hz range for feature extraction, which corresponds to indices 20-400 (inclusive) in the original 2049-bin FRF. This slicing should be done before any feature extraction steps that rely on the frequency bins, to ensure consistency with the training data and the expected input format for the PCA and WCC calculations.
        freqs = np.linspace(10, 200, 381) # Update freqs to match the sliced FRF range
        frf_mag_9, pca_frf = feature_extractor.get_base_processed_data(frf_abs)
        
        # Calculate WCC for all three modes
        wcc_m1 = feature_extractor.extract_wcc_feature(freqs, pca_frf, s_baseline, 20, 60)
        
        ratios = feature_extractor.extract_peak_ratios(freqs, frf_mag_9, 20, 60)
        
        # Assemble for Scaler (using DataFrame to avoid name warnings)
        column_names = ['wcc_m1','pt2/8', 'pt4/6'] 
        feature_df = pd.DataFrame([[wcc_m1, ratios[0], ratios[1]]], 
                                  columns=column_names)

        # STEP E: Machine Learning Classification
        scaled_features = scaler.transform(feature_df)
        prediction = rf_model.predict(scaled_features)[0]
        
        print("value of feature vector:", feature_df.values)
        print(f"\n[ML RESULT]: Damage State Detected -> {prediction}")

        # # STEP F: Update Digital Twin (Ansys)
        # # Uncomment this once you are ready to update the Ansys BCs
        
        print(f"[TWIN]: Syncing physical state to Ansys Mechanical...")

        # damage_params = ansys_twin.get_damage_parameters(prediction)
        # ansys_status = ansys_twin.apply_digital_twin_sync(DB_PATH, EXEC_LOC, damage_params)
        # print(f"[ANSYS]: {ansys_status}")
        
        solver = ansys_twin_updated.MechanicalSolver()
        solver.run(damage_case=2)

        print("\n>>> SUCCESS: Process complete. Script exiting.")

    except Exception as e:
        print(f"\n[CRITICAL ERROR]: {e}")

if __name__ == "__main__":
    run_digital_twin()
