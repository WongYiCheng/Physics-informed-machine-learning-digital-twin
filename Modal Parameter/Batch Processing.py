# Extract model parameter(natural frequency and modal shape) into np file.

from sdypy import EMA
import numpy as np
import matplotlib.pyplot as plt

import os

# Update these paths to match your Python 3.13 installation location
tcl_path = r"C:\Program Files\Python313\tcl\tcl8.6"
tk_path = r"C:\Program Files\Python313\tcl\tk8.6"

os.environ['TCL_LIBRARY'] = tcl_path
os.environ['TK_LIBRARY'] = tk_path

class_name = 'HD_E4_Group_final'
frf_full = np.load(rf"D:\UM Document\FYP_ML\450,60,2 Dataset\processed_dataset3\frf_{class_name}.npy")
freq = np.linspace(0, 1024, 2049)

modal_params_list = []

for i in range(frf_full.shape[0]):
    frf = frf_full[i, :]

    acc = EMA.Model(frf=frf,
                    freq=freq,
                    lower=10,
                    upper=200,
                    pol_order_high=50)

    acc.get_poles(method='lscf')
    # acc.select_poles()

    # Modal Analysis Final Results (Averaged from Experimental Trials)
    # UD: Undamaged Reference
    # Mean Calculation: [(44.6+45.2+45.2)/3, (109.9+109.9+109.9)/3, (151.6+151.6+151.5)/3]
    # n_freq = [45.0, 109.9, 151.6] # UD Group Final

    # # LD: Light Damage 
    # n_freq = [43.4, 109.3, 151.5] # LD_E1 Group Final
    # n_freq = [43.4, 109.5, 151.4] # LD_E2 Group Final
    # n_freq = [42.9, 109.2, 151.3] # LD_E3 Group Final
    # n_freq = [42.7, 109.1, 150.5] # LD_E4 Group Final

    # # MD: Medium Damage
    # n_freq = [41.2, 107.0, 146.9] # MD_E1 Group Final
    # n_freq = [42.1, 107.3, 147.7] # MD_E2 Group Final
    # n_freq = [41.3, 107.6, 147.4] # MD_E3 Group Final
    # n_freq = [41.1, 107.4, 147.3] # MD_E4 Group Final

    # # HD: Heavy Damage (Note: Modal density increases significantly here)
    # n_freq = [39.3, 83.7, 124.6]  # HD_E1 Group Final

    # # HD_E2 exhibits high modal splitting/coupling
    # n_freq = [36.5, 71.2, 81.4, 115.5, 131.8, 152.4] #, 168.6, 177.8, 185.1, 189.1] # HD_E2 Group Final

    # # HD_E3
    # n_freq = [38.0, 77.6, 115.5, 146.9, 192.2] # HD_E3 Group Final

    # # HD_E4
    n_freq = [40.6, 113.3, 146.7, 172.0] # HD_E4 Group Final


    acc.select_closest_poles(n_freq)

    frf_rec, modal_const = acc.get_constants(whose_poles='own', FRF_ind='all', upper_r=False)

    acc.print_modal_data()

    acc.A

    acc.nat_freq

    acc.nat_xi

    # column 0 is the natural frequency, column 1 is the damping ratio, columns 2... are mode shapes
    modal_parameters = np.c_[np.array(acc.nat_freq).reshape(-1), np.array(acc.nat_xi).reshape(-1), acc.A.transpose()]

    modal_params_list.append(modal_parameters)

# save all modal parameters to one npy file
with open(f"Modal Parameter\\Batch Processing Modal Parameter2\\Modalparameters_{class_name}_all.npy", "wb") as f:
    np.save(f, modal_params_list)
