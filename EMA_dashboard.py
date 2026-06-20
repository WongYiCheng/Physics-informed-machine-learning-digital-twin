import nidaqmx
from nidaqmx.constants import AcquisitionType
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import CheckButtons, MultiCursor, TextBox
import os

# -------- Note ---------
'''
Saving location: Same folder with this python file
invovle 3 functions: (1) acquire data, (2) interactive plot, (3) main executive function
- dc offset, and rectangular windowing are applied in the main function, the acquired data function obtain pure time series data only
at the end of the code, 4 type of file will be saved (raw time series, frequency amplitude series, coherence, frequency x axis)
'''
# For saving file name
class_name = '(T)MD_E4_T01_R1'

# --- Configuration ---
HAMMER_CHANNEL = "/cDAQ1Mod1/ai0"
ACCEL_CHANNELS = ["/cDAQ1Mod1/ai1", "/cDAQ1Mod1/ai2", "/cDAQ1Mod1/ai3", 
                  "/cDAQ1Mod2/ai0", "/cDAQ1Mod2/ai1", "/cDAQ1Mod2/ai3", 
                  "/cDAQ1Mod4/ai1", "/cDAQ1Mod4/ai2", "/cDAQ1Mod4/ai3"]
SAMPLING_RATE = 2048
SAMPLES_PER_CHANNEL = 4096
TRIGGER_LEVEL = 20.0    
PRE_TRIGGER_SAMPLES = 45
NUM_AVERAGES = 20

def acquire_impact_data():
    """Acquires data using a software trigger logic."""
    CHUNK_SIZE = 200
    
    print("\nWaiting for hammer hit (Software Trigger)...")
     
    with nidaqmx.Task() as task:
        task.ai_channels.add_ai_force_iepe_chan(HAMMER_CHANNEL,current_excit_val=0.002)
        for accel in ACCEL_CHANNELS:
            task.ai_channels.add_ai_accel_chan(accel, sensitivity=40.0/9.80665, current_excit_val=0.002)

        task.timing.cfg_samp_clk_timing(
            rate=SAMPLING_RATE,
            sample_mode=AcquisitionType.CONTINUOUS,
            samps_per_chan=SAMPLES_PER_CHANNEL * 2
        )

        stream_buffer = []
        triggered = False
        history_buffer = None
        task.start()

        while True:
            in_data = np.array(task.read(number_of_samples_per_channel=CHUNK_SIZE)) #determine holding samples
            if not triggered:
                hammer_chunk = in_data[0, :]
                trigger_indices = np.where(hammer_chunk > TRIGGER_LEVEL)[0]
                if len(trigger_indices) > 0:
                    triggered = True
                    print("Hit detected! Recording...")
                    #full stream length = history + indata
                    full_stream = np.concatenate((history_buffer, in_data), axis=1) if history_buffer is not None else in_data
                    hist_len = history_buffer.shape[1] if history_buffer is not None else 0
                    stream_buffer = full_stream
                    trigger_index_in_buffer = hist_len + trigger_indices[0] #absolute index in the full stream
                else:
                    if history_buffer is None:
                        history_buffer = in_data
                    else:
                        # GLUE new data to the old data
                        history_buffer = np.concatenate((history_buffer, in_data), axis=1)

                    max_needed = 2048 + PRE_TRIGGER_SAMPLES + 100
                    if history_buffer.shape[1] > max_needed:
                        history_buffer = history_buffer[:, -max_needed:]
                        #history_buffer = in_data[:, -(PRE_TRIGGER_SAMPLES + 10):]
            else:
                stream_buffer = np.concatenate((stream_buffer, in_data), axis=1)
                #stream_buffer length should be at least trigger_index + pre_trigger + desired samples
                req_start = trigger_index_in_buffer - PRE_TRIGGER_SAMPLES #absolute index of the desired start point in the stream buffer
                req_end = (trigger_index_in_buffer - PRE_TRIGGER_SAMPLES) + SAMPLES_PER_CHANNEL
                bias_start = trigger_index_in_buffer - PRE_TRIGGER_SAMPLES - 2048
                bias_end = trigger_index_in_buffer - PRE_TRIGGER_SAMPLES

                if stream_buffer.shape[1] >= req_end:
                    bias_data = stream_buffer[:, bias_start:bias_end]
                    bias = np.mean(bias_data, axis=1, keepdims=True)
                    final_data = stream_buffer[:, req_start:req_end]
                    return final_data, bias

def plot_interactive_dashboard(time_axis, freqs, force, resps, fft_f, fft_r, cum_coh, avg_frf, count):
    plt.ioff() # Ensure it blocks correctly for measurement decision
    fig = plt.figure(figsize=(20, 10))
    gs = fig.add_gridspec(2, 3)
    
    # Define Subplots
    ax_f_time = fig.add_subplot(gs[0, 0])
    ax_f_spec = fig.add_subplot(gs[1, 0])
    ax_r_time = fig.add_subplot(gs[0, 1]) 
    ax_r_spec = fig.add_subplot(gs[1, 1])
    ax_frf    = fig.add_subplot(gs[0, 2])
    ax_coh    = fig.add_subplot(gs[1, 2])

    # --- LINK FREQUENCY X-AXES ---
    ax_coh.sharex(ax_frf)
    ax_r_spec.sharex(ax_frf)
    ax_f_spec.sharex(ax_frf)

    # --- ADDITIONAL DASHBOARD ELEMENTS ---
    WINDOW_START_IDX = 35
    WINDOW_END_IDX = 72

    window_start_t = time_axis[WINDOW_START_IDX]
    window_end_t = time_axis[WINDOW_END_IDX]

    ax_f_time.axvline(window_start_t, color='magenta', ls='--', lw=1.2, label='Force window start')
    ax_f_time.axvline(window_end_t,   color='magenta', ls='--', lw=1.2, label='Force window end')
    ax_f_time.axvspan(window_start_t, window_end_t, color='magenta', alpha=0.12)
    ax_f_time.set_xlim(time_axis[WINDOW_START_IDX-20], time_axis[WINDOW_END_IDX +20])
    
    # 1. Plotting Data
    ax_f_time.plot(time_axis, force, 'tab:red', lw=0.8)
    ax_f_spec.plot(freqs, np.abs(fft_f), 'tab:red', lw=0.8)

    lines_r_time = [ax_r_time.plot(time_axis, r, label=f'Ch{i+1}', lw=0.7)[0] for i, r in enumerate(resps)]
    lines_r_spec = [ax_r_spec.plot(freqs, np.abs(fr), lw=0.7)[0] for i, fr in enumerate(fft_r)]
    lines_coh    = [ax_coh.plot(freqs, coh, lw=0.7)[0] for i, coh in enumerate(cum_coh)]
    lines_frf    = [ax_frf.plot(freqs, np.abs(frf), lw=0.8)[0] for i, frf in enumerate(avg_frf)]

    # 2. Titles and Formatting
    ax_f_time.set_title("Hammer Impulse (Time)")
    ax_f_spec.set_title("Input Spectrum (Freq)")
    ax_r_time.set_title("Response (Time)")
    ax_r_spec.set_title("Response Spectrum (Freq)")
    ax_frf.set_title(f"Average FRF (N={count})")
    ax_coh.set_title("Coherence")
    ax_coh.set_ylim(-0.05, 1.1)

    for ax in [ax_f_time, ax_f_spec, ax_r_time, ax_r_spec, ax_coh, ax_frf]: ax.grid(True, alpha=0.3)

    # 3. RIGHT SIDE CONTROL PANEL (Checkboxes + Range Control)
    rax = fig.add_axes([0.88, 0.70, 0.08, 0.15]) 
    check = CheckButtons(rax, [f'Accel {i+1}' for i in range(len(resps))], [True]*len(resps))
    
    def toggle(label):
        idx = int(label.split()[-1]) - 1
        for line_set in [lines_r_time, lines_r_spec, lines_coh, lines_frf]:
            line_set[idx].set_visible(not line_set[idx].get_visible())
        plt.draw()
    check.on_clicked(toggle)

    # Range Control Boxes (Objective 3)
    ax_xm = fig.add_axes([0.92, 0.55, 0.04, 0.03]); txt_xm = TextBox(ax_xm, 'X Min ', initial=f"{freqs[0]:.0f}")
    ax_xM = fig.add_axes([0.92, 0.50, 0.04, 0.03]); txt_xM = TextBox(ax_xM, 'X Max ', initial= "200") #f"{freqs[-1]:.0f}"
    ax_ym = fig.add_axes([0.92, 0.40, 0.04, 0.03]); txt_ym = TextBox(ax_ym, 'Y Min ', initial="0.0001")
    ax_yM = fig.add_axes([0.92, 0.35, 0.04, 0.03]); txt_yM = TextBox(ax_yM, 'Y Max ', initial="10")

    def update_lims(val):
        try:
            ax_frf.set_xlim(float(txt_xm.text), float(txt_xM.text))
            ax_frf.set_ylim(float(txt_ym.text), float(txt_yM.text))
            fig.canvas.draw_idle()
        except: pass
    for box in [txt_xm, txt_xM, txt_ym, txt_yM]: box.on_submit(update_lims)

    # 4. CROSSHAIR & SNAPPING (Objectives 1 & 2)
    freq_axes = [ax_f_spec, ax_r_spec, ax_coh, ax_frf]
    fv_lines = {ax: ax.axvline(color='blue', ls='--', lw=0.6, visible=False) for ax in freq_axes}
    fh_lines = {ax: ax.axhline(color='blue', ls='--', lw=0.6, visible=False) for ax in freq_axes}
    f_texts = {ax: ax.text(0.05, 0.85, '', transform=ax.transAxes, fontsize=8, bbox=dict(fc='white', alpha=0.7)) for ax in freq_axes}

    # Hammer Time Snapping
    h_v = ax_f_time.axvline(color='green', ls='--', lw=0.8, visible=False)
    h_h = ax_f_time.axhline(color='green', ls='--', lw=0.8, visible=False)
    h_text = ax_f_time.text(0.05, 0.9, '', transform=ax_f_time.transAxes, fontsize=8, bbox=dict(fc='white', alpha=0.7))

    def on_mouse_move(event):
        if event.inaxes == ax_f_time:
            idx = np.searchsorted(time_axis, event.xdata)
            if 0 <= idx < len(time_axis):
                tx, ty = time_axis[idx], force[idx]
                h_v.set_xdata([tx]); h_h.set_ydata([ty]); h_v.set_visible(True); h_h.set_visible(True)
                h_text.set_text(f"t:{tx:.3f}s\nF:{ty:.2f}N"); h_text.set_visible(True)
                fig.canvas.draw_idle()
        elif event.inaxes in freq_axes:
            active_idx = 0
            for i, line in enumerate(lines_r_spec):
                if line.get_visible(): active_idx = i
            idx = np.searchsorted(freqs, event.xdata)
            if 0 <= idx < len(freqs):
                tx = freqs[idx]
                for ax in freq_axes:
                    if ax == ax_f_spec: ty = np.abs(fft_f[idx])
                    elif ax == ax_r_spec: ty = np.abs(fft_r[active_idx][idx])
                    elif ax == ax_coh: ty = cum_coh[active_idx][idx]
                    else: ty = np.abs(avg_frf[active_idx][idx])
                    fv_lines[ax].set_xdata([tx]); fh_lines[ax].set_ydata([ty]); fv_lines[ax].set_visible(True); fh_lines[ax].set_visible(True)
                    f_texts[ax].set_text(f"CH{active_idx+1}\nf:{tx:.1f}Hz\ny:{ty:.3f}"); f_texts[ax].set_visible(True)
                fig.canvas.draw_idle()
        else:
            h_v.set_visible(False); h_h.set_visible(False); h_text.set_visible(False)
            for ax in freq_axes: fv_lines[ax].set_visible(False); fh_lines[ax].set_visible(False); f_texts[ax].set_visible(False)
            fig.canvas.draw_idle()

    fig.canvas.mpl_connect('motion_notify_event', on_mouse_move)

    # 5. MULTICURSOR
    fig.multi = MultiCursor(fig.canvas, freq_axes, color='gray')

    # References to prevent garbage collection
    fig.refs = [check, txt_xm, txt_xM, txt_ym, txt_yM]
    
    plt.tight_layout(rect=[0, 0.03, 0.88, 0.95])
    fig.suptitle(f"Impact Validation Dashboard - Measurement {count}", fontsize=16)
    
    ax.set_xlim(0, 200)  # Focuses the view on 0-200 Hz immediately
    ax.set_ylim(0, 15) # Sets a reasonable vertical range for FRF magnitudes
    plt.show(block=True)
    return fig

def main():
    valid_samples = 0
    accepted_time_series, frf_history, coh_history = [], [], []
    sum_Pxx, sum_Pxy, sum_Pyy = None, None, None
    
    dt = 1/SAMPLING_RATE
    time_axis = np.linspace(-PRE_TRIGGER_SAMPLES*dt, (SAMPLES_PER_CHANNEL-PRE_TRIGGER_SAMPLES-1)*dt, SAMPLES_PER_CHANNEL)

    #Windowing Function
    rect_window = np.zeros_like(time_axis)
    start = 42
    end = 68
    rect_window[start:end] = 1.0

    #DC Removal and Alignment Buffers
    offset_len = 2048
    bias = None
    offset = False
  
    
    print(f"Starting Acquisition. Target: {NUM_AVERAGES} averages.")

    while valid_samples < NUM_AVERAGES:
        print(f"\n--- Measurement {valid_samples + 1} of {NUM_AVERAGES} ---")
        try:
            raw_data, bias = acquire_impact_data()
            f_data, a_data = raw_data[0], raw_data[1:]
            
            # DC Removal and Windowing
            if offset is False:
                f_bias = bias[0, 0]
                a_biases = bias[1:].flatten()
                offset = True


            f_data -= f_bias
            a_data = [a - bias for a, bias in zip(a_data, a_biases)]
            f_windowed = f_data * rect_window
            
            fft_f = np.fft.rfft(f_windowed)
            fft_a = np.array([np.fft.rfft(r) for r in a_data])
            freqs = np.fft.rfftfreq(SAMPLES_PER_CHANNEL, d=dt)

            Pxx_curr = np.real(fft_f * np.conj(fft_f))
            Pxy_curr = fft_a * np.conj(fft_f)
            Pyy_curr = np.real(fft_a * np.conj(fft_a))
            
            if sum_Pxy is not None:
                Sxx, Sxy, Syy = sum_Pxx + Pxx_curr, sum_Pxy + Pxy_curr, sum_Pyy + Pyy_curr
            else:
                Sxx, Sxy, Syy = Pxx_curr, Pxy_curr, Pyy_curr

            cum_coh = (np.abs(Sxy)**2) / (Sxx * Syy + 1e-15)
            avg_frf = Sxy / (Sxx + 1e-15)


            # Dashboard pauses here for user to toggle checkboxes and decide
            print("Interact with the plot. Close it to decide (y/n).")
            fig = plot_interactive_dashboard(time_axis, freqs, f_windowed, a_data, fft_f, fft_a, cum_coh, avg_frf, valid_samples + 1)
            
            choice = input(f"Accept hit {valid_samples+1}? (y/n): ").strip().lower()

            if choice == 'y':
                if sum_Pxx is None:
                    sum_Pxx, sum_Pxy, sum_Pyy = Pxx_curr, Pxy_curr, Pyy_curr
                else:
                    sum_Pxx += Pxx_curr; sum_Pxy += Pxy_curr; sum_Pyy += Pyy_curr
                
                coh_history.append((np.abs(sum_Pxy)**2) / (sum_Pxx * sum_Pyy + 1e-15))
                frf_history.append(sum_Pxy / (sum_Pxx + 1e-15))
                accepted_time_series.append(raw_data)
                valid_samples += 1
            
        except KeyboardInterrupt: break

    # --- Final Save Logic (N, 5, 2049) ---
    if valid_samples > 0:
        np.save(f"frf_{class_name}.npy", np.array(frf_history))
        np.save(f"avg_coherence_{class_name}.npy", np.array(coh_history))
        np.save(f"raw_time_series_{class_name}.npy", np.array(accepted_time_series))
        np.save(f"frequencies_{class_name}.npy", freqs)
        print(f"Data saved successfully as {class_name}.")
    else:
        print("No valid samples acquired. Nothing saved.")

if __name__ == "__main__":
    main()
    #remind me that add vertical lines, change cursor, and x axis plot limits to 200hz by default
