import nidaqmx
from nidaqmx.constants import AcquisitionType
import numpy as np
import matplotlib.pyplot as plt

# --- Configuration Constants ---
SAMPLING_RATE = 2048
SAMPLES_PER_CHANNEL = 4096
TRIGGER_LEVEL = 20.0
PRE_TRIGGER_SAMPLES = 45

# ---Configuration for how DAQ ---
HAMMER_CHANNEL = "/cDAQ1Mod1/ai0"
ACCEL_CHANNELS = ["/cDAQ1Mod1/ai1", "/cDAQ1Mod1/ai2", "/cDAQ1Mod1/ai3", 
                  "/cDAQ1Mod2/ai0", "/cDAQ1Mod2/ai1", "/cDAQ1Mod2/ai3", 
                  "/cDAQ1Mod4/ai1", "/cDAQ1Mod4/ai2", "/cDAQ1Mod4/ai3"]

def acquire_impact_data():
    """Exact software trigger logic from your original EMA method."""
    CHUNK_SIZE = 200
    print("\n[DAQ] Waiting for hammer hit (Software Trigger)...")
    
    with nidaqmx.Task() as task:
        task.ai_channels.add_ai_force_iepe_chan(HAMMER_CHANNEL, current_excit_val=0.002)
        for accel in ACCEL_CHANNELS:
            task.ai_channels.add_ai_accel_chan(accel, sensitivity=40.0/9.80665, current_excit_val=0.002)

        task.timing.cfg_samp_clk_timing(rate=SAMPLING_RATE, sample_mode=AcquisitionType.CONTINUOUS)

        stream_buffer = np.empty((10, 0))
        triggered = False
        history_buffer = None
        task.start()

        while True:
            in_data = np.array(task.read(number_of_samples_per_channel=CHUNK_SIZE))
            if not triggered:
                hammer_chunk = in_data[0, :]
                trigger_indices = np.where(hammer_chunk > TRIGGER_LEVEL)[0]
                if len(trigger_indices) > 0:
                    triggered = True
                    print("[DAQ] Hit detected! Recording...")
                    full_stream = np.concatenate((history_buffer, in_data), axis=1) if history_buffer is not None else in_data
                    hist_len = history_buffer.shape[1] if history_buffer is not None else 0
                    stream_buffer = full_stream
                    trigger_index_in_buffer = hist_len + trigger_indices[0]
                else:
                    if history_buffer is None: history_buffer = in_data
                    else: history_buffer = np.concatenate((history_buffer, in_data), axis=1)
                    
                    max_needed = 2048 + PRE_TRIGGER_SAMPLES + 100
                    if history_buffer.shape[1] > max_needed:
                        history_buffer = history_buffer[:, -max_needed:]
            else:
                stream_buffer = np.concatenate((stream_buffer, in_data), axis=1)
                req_end = (trigger_index_in_buffer - PRE_TRIGGER_SAMPLES) + SAMPLES_PER_CHANNEL
                
                if stream_buffer.shape[1] >= req_end:
                    req_start = trigger_index_in_buffer - PRE_TRIGGER_SAMPLES
                    bias_start = trigger_index_in_buffer - PRE_TRIGGER_SAMPLES - 2048
                    bias_end = trigger_index_in_buffer - PRE_TRIGGER_SAMPLES
                    
                    bias_data = stream_buffer[:, bias_start:bias_end]
                    bias = np.mean(bias_data, axis=1, keepdims=True)
                    final_data = stream_buffer[:, req_start:req_end]
                    return final_data, bias

def compute_frf(final_data, bias):
    """Processes raw data into FRF using your exact windowing and DC removal."""
    clean_data = final_data - bias
    f_data, a_data = clean_data[0], clean_data[1:]
    
    # Exact rectangular window indices: 42 to 68
    rect_window = np.zeros(SAMPLES_PER_CHANNEL)
    rect_window[42:68] = 1.0
    f_windowed = f_data * rect_window
    
    fft_f = np.fft.rfft(f_windowed)
    fft_a = np.array([np.fft.rfft(acc) for acc in a_data])
    freqs = np.fft.rfftfreq(SAMPLES_PER_CHANNEL, d=1/SAMPLING_RATE)
    
    Sxx = np.real(fft_f * np.conj(fft_f))
    Sxy = fft_a * np.conj(fft_f)
    frf = Sxy / (Sxx + 1e-15)
    
    return freqs, frf, f_windowed, a_data

def plot_validation(freqs, frf, f_windowed, a_data):
    """Plots the dashboard for human verification."""
    plt.ioff()
    fig, axs = plt.subplots(2, 1, figsize=(12, 8))
    
    # Subplot 1: Hammer Force (Check for double hits)
    axs[0].plot(f_windowed, color='tab:red', lw=1)
    axs[0].set_title("Hammer Impulse Time Response (Windowed & DC Removed)")
    axs[0].set_ylabel("Force (N)")
    axs[0].grid(True, alpha=0.3)

    # Subplot 2: FRF Magnitudes (Check for clean resonances)
    for i in range(9):
        axs[1].plot(freqs, np.abs(frf[i]), label=f'Sensor {i+1}', lw=0.8)
    
    axs[1].set_xlim(0, 200) # Default to your desired 200Hz limit
    axs[1].set_ylim(0, 15)
    axs[1].set_title("9-Point FRF Magnitude Response (0-200 Hz)")
    axs[1].set_xlabel("Frequency (Hz)")
    axs[1].set_ylabel("Magnitude")
    axs[1].legend(loc='upper right', ncol=3, fontsize='x-small')
    axs[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show() # Blocks execution until the plot window is closed
    
    choice = input("\nAccept this measurement for Digital Twin update? (y/n): ").strip().lower()
    return choice == 'y'

# --- MAIN TESTING & DEBUGGING FUNCTION ---
def main():
    print("--- EMA Data Acquisition Debug Mode ---")
    try:
        # 1. Capture the hit
        raw_data, bias_vals = acquire_impact_data()
        
        # 2. Process to FRF
        freqs, frf_data, f_time, a_time = compute_frf(raw_data, bias_vals)
        
        # 3. User Validation
        is_accepted = plot_validation(freqs, frf_data, f_time, a_time)
        
        if is_accepted:
            print("[DEBUG] Measurement accepted. Exporting features...")
            print("frf_data shape:", frf_data.shape)
            # Here is where your next code module (Feature Extraction) would start
            # e.g., features = extract_features(freqs, frf_data)
        else:
            print("[DEBUG] Measurement rejected by user.")
            
    except Exception as e:
        print(f"[ERROR] An error occurred during acquisition: {e}")

# if __name__ == "__main__":
#     main()
