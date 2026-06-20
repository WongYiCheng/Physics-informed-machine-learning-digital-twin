import numpy as np
from sklearn.decomposition import PCA
from scipy.signal import find_peaks

def get_base_processed_data(frf_9_points):
    """
    Step 1: Convert raw complex FRF to Magnitude and PCA-compressed signals.
    Returns:
        frf_mag_9: (9, 2049) Magnitude-only FRF
        pca_frf: (2049,) 1st Principal Component 'Signal'
    """
    # 1. Convert complex FRF to Absolute Magnitude
    frf_mag_9 = np.abs(frf_9_points)
    
    # 2. Perform 'On-the-Fly' PCA (Matches your training logic)
    # Transpose [9, 2049] -> [2049, 9] for PCA features
    trial_data_abs = frf_mag_9.T 
    pca = PCA(n_components=1)
    pca.fit(trial_data_abs)
    
    # 3. Project data onto 1st component
    pca_frf = trial_data_abs.dot(pca.components_.T).flatten()
    
    return frf_mag_9, pca_frf

def extract_wcc_feature(freqs, pca_line, s_baseline, f_low, f_high):
    """
    Matches training logic in extract_pca_features exactly:
    - s_baseline : raw slope of UD mean (not pre-scaled) — as saved by training script
    - pca_line   : raw PCA signal (381,)
    """
    idx_start = np.searchsorted(freqs, f_low)
    idx_end   = np.searchsorted(freqs, f_high, side='right')

    # ── Slope of test PCA signal ──────────────────────────────────────
    s = np.diff(pca_line, append=0)                  # (381,)
    s_win = s[idx_start:idx_end]                     # windowed slope

    # ── Slope of baseline (raw, loaded from .npy) ─────────────────────
    s_base_win = s_baseline[idx_start:idx_end]       # windowed baseline slope

    # ── Scale baseline using its own max (matches training) ───────────
    s_base_max = np.abs(s_base_win).max()
    if s_base_max == 0 or np.isnan(s_base_max):
        s_base_max = 1
    s_rs_base = s_base_win * 50 / s_base_max         # scaled to [-50, 50]

    # ── Scale test signal using its own max (matches training) ────────
    s_max = np.abs(s_win).max()
    if s_max == 0 or np.isnan(s_max):
        s_max = 1
    s_rs_curr = s_win * 50 / s_max                   # scaled to [-50, 50]

    # ── WCC feature: sum of absolute slope differences ────────────────
    wcc = np.sum(np.abs(s_rs_curr - s_rs_base))

    return wcc

def extract_peak_ratios(freqs, frf_mag_9, f_low, f_high):
    """
    Step 3: Extract ratios using the magnitude-only 9-point FRF.
    """
    idx_start = np.searchsorted(freqs, f_low)
    idx_end = np.searchsorted(freqs, f_high, side='right')
    peak_amps = []
    
    for i in range(9):
        sensor_mag_win = frf_mag_9[i, idx_start:idx_end]
        peaks, _ = find_peaks(sensor_mag_win)
        
        if peaks.size > 0:
            p_amp = sensor_mag_win[peaks[np.argmax(sensor_mag_win[peaks])]]
        else:
            p_amp = np.max(sensor_mag_win) if sensor_mag_win.size > 0 else 1e-9
        peak_amps.append(p_amp)
    
    # Calculate ratios for Case Detection
    r28 = peak_amps[1] / (peak_amps[7] + 1e-15)
    r46 = peak_amps[3] / (peak_amps[5] + 1e-15)
    
    return [r28, r46]

# --- MAIN DEBUGGING / CHECKING FUNCTION ---
def main():
    print("=== Feature Extraction Debugging ===\n")
    
    # 1. Create Dummy Data (9 points, 2049 frequency bins)
    # Simulated complex FRF with some random noise
    frf_load = np.load(r"D:\UM Document\FYP_ML\450,60,2 Dataset\processed_dataset3\frf_UD_Group_Final.npy")  # Shape: (9, 2049)
    dummy_frf = frf_load[0]  # Use the first sample for testing
    dummy_frf = dummy_frf[:, 20:401]  # Slice to the desired frequency range
    dummy_freqs = np.linspace(10, 200, 381)  # Update freqs to match the sliced FRF range

    dummy_s_baseline = np.load('PCA Feature Extraction\\healthy_slope_baseline_HD.npy') 

    # 2. Test Step 1: PCA Processing
    mag_9, pca_line = get_base_processed_data(dummy_frf)
    print(f"[STEP 1] Magnitude 9-Pt Shape: {mag_9.shape}")
    print(f"[STEP 1] PCA Signal Shape:     {pca_line.shape}")
    print(f"[STEP 1] PCA Sample Values (first 5): {pca_line[:5]}\n")

    # 3. Test Step 2: WCC Extraction (Mode 1: 30-50 Hz)
    wcc_val = extract_wcc_feature(dummy_freqs, pca_line, dummy_s_baseline, 20, 60)
    print(f"[STEP 2] WCC Value (30-50Hz): {wcc_val:.4f}\n")

    # 4. Test Step 3: Peak Ratios (Mode 1: 30-50 Hz)
    ratios = extract_peak_ratios(dummy_freqs, mag_9, 20, 60)
    print(f"[STEP 3] Peak Ratios:")
    print(f"         - pt2/8: {ratios[0]:.4f}")
    print(f"         - pt4/6: {ratios[1]:.4f}\n")

    # 5. Final Feature Vector for Machine Learning
    # Assuming m2 and m3 are placeholders for this debug
    final_vector = [wcc_val, 0.0, 0.0, ratios[0], ratios[1]]
    print(f"--- FINAL 5-FEATURE VECTOR ---")
    print(f"Values: {final_vector}")
    print(f"Array:  {np.array(final_vector)}")

if __name__ == "__main__":
    main()
