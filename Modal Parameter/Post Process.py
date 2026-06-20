import numpy as np
import pandas as pd
import os

# 1. Setup paths and file list
base_path = r"D:\UM Document\FYP_ML\Modal Parameter\Batch Processing Modal Parameter2"
end_path = r"D:\UM Document\FYP_ML\Modal Parameter\Post Process Modal Parameter2"
file_list = [
    "Modalparameters_UD_Group_final_all.npy",
    "Modalparameters_LD_E1_Group_final_all.npy", "Modalparameters_LD_E2_Group_final_all.npy",
    "Modalparameters_LD_E3_Group_final_all.npy", "Modalparameters_LD_E4_Group_final_all.npy",
    "Modalparameters_MD_E1_Group_final_all.npy", "Modalparameters_MD_E2_Group_final_all.npy",
    "Modalparameters_MD_E3_Group_final_all.npy", "Modalparameters_MD_E4_Group_final_all.npy",
    "Modalparameters_HD_E1_Group_final_all.npy", "Modalparameters_HD_E2_Group_final_all.npy",
    "Modalparameters_HD_E3_Group_final_all.npy", "Modalparameters_HD_E4_Group_final_all.npy"
]

# Labels for readability in the final CSV/DataFrame
class_names = ['UD', 'L1', 'L2', 'L3', 'L4', 'M1', 'M2', 'M3', 'M4', 'H1', 'H2', 'H3', 'H4']

all_data_list = []

print(f"{'File Name':<45} | {'Samples':<8} | {'Dtype Check'}")
print("-" * 70)

for idx, file_name in enumerate(file_list):
    file_path = os.path.join(base_path, file_name)
    
    if not os.path.exists(file_path):
        print(f"Warning: {file_name} not found. Skipping...")
        continue

    # Load and immediately convert to real float to remove +0j brackets
    raw_data = np.load(file_path)
    
    # Selection: First 3 modes, all 11 columns
    # Explicit .real call handles the complex -> float conversion
    data_3m = raw_data[:, :3, :].real.astype(np.float64)
    num_samples = data_3m.shape[0]

    # --- Feature Extraction ---
    # Col 0: Damped Freq (fd), Col 1: Damping Ratio (zeta)
    fd = data_3m[:, :, 0]
    zeta = data_3m[:, :, 1]
    
    # Calculate Natural Frequency: fn = fd / sqrt(1 - zeta^2)
    fn = fd / np.sqrt(1 - np.power(zeta, 2))
    
    # Col 2-10: Mode Shapes (Take Absolute Value)
    shapes = np.abs(data_3m[:, :, 2:])

    # Normalizing: Divide each mode by its own maximum value across the 9 channels
    # We use keepdims=True to allow broadcasting (60, 3, 9) / (60, 3, 1)
    max_vals = np.max(shapes, axis=2, keepdims=True)
    
    # Avoid division by zero in case of noise
    max_vals[max_vals == 0] = 1 
    
    normalized_shapes = shapes / max_vals

    # --- Rearrangement ---
    # Horizontal stack: [Case_ID] + [fn1, fn2, fn3] + [zeta1, zeta2, zeta3] + [A1...A27]
    case_col = np.full((num_samples, 1), idx)
    
    processed_batch = np.hstack([
        case_col,                       # Label (1 col)
        fn,                             # Frequencies (3 cols)
        zeta,                           # Damping (3 cols)
        normalized_shapes.reshape(num_samples, -1) # Flattened Mode Shapes (27 cols)
    ])
    
    all_data_list.append(processed_batch)
    print(f"{file_name:<45} | {num_samples:<8} | {processed_batch.dtype}")

# 2. Final Aggregation
final_matrix = np.vstack(all_data_list)

# 3. Create DataFrame for Precise Header Mapping
headers = ["Case"]
headers += [f"Mode{i}_fn" for i in range(1, 4)]
headers += [f"Mode{i}_zeta" for i in range(1, 4)]
for m in range(1, 4):
    headers += [f"Mode{m}_A{ch}" for ch in range(1, 10)]

df = pd.DataFrame(final_matrix, columns=headers)

# Map the numerical Case to actual labels (Optional, but good for verification)
df['Case_Label'] = df['Case'].map(dict(enumerate(class_names)))
# Move Label to the front
cols = ['Case_Label'] + [c for c in df.columns if c != 'Case_Label']
df = df[cols]

# 4. Save Outputs
df.to_csv(os.path.join(end_path, "Post_Processed_Modal_Parameters.csv"), index=False)
np.save(os.path.join(end_path, "Post_Processed_Modal_Parameters.npy"), final_matrix)

print("\n" + "="*30)
print(f"Final Dataset Shape: {final_matrix.shape}")
print(f"Data successfully saved to {end_path}")
print("="*30)

# Preview the first few rows to confirm formatting
df.head()
