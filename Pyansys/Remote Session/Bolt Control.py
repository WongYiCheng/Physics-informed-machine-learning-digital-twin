import os
from ansys.mechanical.core import launch_mechanical

# --- 1. SETTINGS & PATHS ---
db_path = r"D:\UM Document\FYP ansys\Remote copy\Remote Copy_files\dp8\global\MECH\SYS.mechdb"
exec_loc = r"C:\Program Files\ANSYS Inc\v252\aisol\Bin\winx64\AnsysWBU.exe"

# --- 2. CLEANUP & LAUNCH ---
# Kill any stuck background processes
os.system("taskkill /f /im AnsysWBU.exe /t")
os.system("taskkill /f /im Mechanical.exe /t")

# Set batch=False so the Ansys GUI appears on your screen
mechanical = launch_mechanical(exec_file=exec_loc, transport_mode="insecure", batch=False, cleanup_on_exit=False)

try:
    print("Opening project...")
    mechanical.run_python_script(f'ExtAPI.DataModel.Project.Open(r"{db_path}")')

    target_bolt = 4
    print(f"Applying Boundary Conditions: Suppressing Bolt {target_bolt}...")

    # --- 3. BOUNDARY CONTROL SCRIPT (NO SOLVE, NO EXTRACTION) ---
    mechanical.run_python_script(f"""
model = ExtAPI.DataModel.Project.Model
static = model.Analyses[0]

# --- A. LOCATE FOLDERS ---
c_folder = [c for c in model.Connections.Children if "Plate bolt" in c.Name][0]
p_folder = [c for c in static.Children if "Plate bolt pretension" in c.Name][0]

# --- B. RESET TO HEALTHY (Unsuppress all bolts) ---
for b in c_folder.Children: 
    b.Suppressed = False
for p in p_folder.Children: 
    p.Suppressed = False

# --- C. APPLY FAULT (Suppress target bolt) ---
[b for b in c_folder.Children if "{target_bolt}" in b.Name][0].Suppressed = True
[b for b in p_folder.Children if "{target_bolt}" in b.Name][0].Suppressed = True

# --- D. MANAGE SUPPORTS ---
# Force Fixed Support ON (so it doesn't float at 0 Hz)
fixed_list = [s for s in static.Children if "Fixed" in s.Name]
if fixed_list:
    fixed_list[0].Suppressed = False

# (Optional) Force Elastic Support OFF to avoid conflicts
elastic_list = [s for s in static.Children if "Elastic" in s.Name]
if elastic_list:
    elastic_list[0].Suppressed = True 
""")

    print(f"Success! Bolt {target_bolt} is suppressed.")
    print("Please look at the Ansys GUI to verify the tree configuration.")

except Exception as e:
    print(f"Error: {e}")

# We intentionally do not call mechanical.exit() here
# so you have time to look at the GUI and save manually if needed.