import os
from ansys.mechanical.core import launch_mechanical

# --- 1. SETTINGS & PATHS ---
db_path = r"D:\UM Document\FYP ansys\Remote copy\Remote Copy_files\dp8\global\MECH\SYS.mechdb"
exec_loc = r"C:\Program Files\ANSYS Inc\v252\aisol\Bin\winx64\AnsysWBU.exe"

# --- 2. CLEANUP & LAUNCH ---
os.system("taskkill /f /im AnsysWBU.exe /t")
os.system("taskkill /f /im Mechanical.exe /t")

mechanical = launch_mechanical(exec_file=exec_loc, transport_mode="insecure", batch=False, cleanup_on_exit=False)

try:
    print("Opening project...")
    mechanical.run_python_script(f'ExtAPI.DataModel.Project.Open(r"{db_path}")')

    target_bolt = 4
    print(f"Applying Boundary Conditions: Suppressing Bolt {target_bolt}...")

    result = mechanical.run_python_script(f"""
from Ansys.Mechanical.DataModel.Enums import SolverType, DataModelObjectCategory
import json

model = ExtAPI.DataModel.Project.Model
static = model.Analyses[0]
modal  = model.Analyses[1]

# ============================================================
# A. BOUNDARY CONDITIONS
# ============================================================
c_folder = [c for c in model.Connections.Children if "Plate bolt" in c.Name][0]
p_folder = [c for c in static.Children if "Plate bolt pretension" in c.Name][0]

for b in c_folder.Children: b.Suppressed = False
for p in p_folder.Children: p.Suppressed = False

[b for b in c_folder.Children if "{target_bolt}" in b.Name][0].Suppressed = True
[b for b in p_folder.Children if "{target_bolt}" in b.Name][0].Suppressed = True

fixed_list = [s for s in static.Children if "Fixed" in s.Name]
if fixed_list: fixed_list[0].Suppressed = False

elastic_list = [s for s in static.Children if "Elastic" in s.Name]
if elastic_list: elastic_list[0].Suppressed = True

# ============================================================
# B. SOLVER + SOLVE
# ============================================================
static.AnalysisSettings.SolverType = SolverType.Direct
static.Solve(True)
modal.Solve(True)

# ============================================================
# C. STATIC — Total Deformation
# ============================================================
td_list = [r for r in static.Solution.Children
           if r.DataModelObjectCategory == DataModelObjectCategory.TotalDeformation]

td = td_list[0] if td_list else static.Solution.AddTotalDeformation()
td.EvaluateAllResults()

static_results = {{
    "max": float(td.Maximum.Value),   # ← explicit float() cast
    "min": float(td.Minimum.Value)
}}

# ============================================================
# D. MODAL — Frequencies + Deformation per mode
# ============================================================
deform_list = []

for child in modal.Solution.Children:
    if child.DataModelObjectCategory == DataModelObjectCategory.TotalDeformation:
        child.EvaluateAllResults()
        deform_list.append({{
            "mode":      int(child.Mode),                      # ← int() cast fixes UInt32
            "freq_hz":   float(child.ReportedFrequency.Value), # ← float() cast
            "max_deform": float(child.Maximum.Value)
        }})

# Sort by mode number just in case
deform_list.sort(key=lambda x: x["mode"])

# ============================================================
# E. RETURN JSON
# ============================================================
output = {{
    "bolt_suppressed": int({target_bolt}),
    "static": static_results,
    "modal":  deform_list
}}

json.dumps(output)
""")

    import json
    data = json.loads(result)

    print(f"\\n=== Bolt {data['bolt_suppressed']} Suppressed ===")
    print(f"Static Max Total Deformation : {data['static']['max']*1000:.4f} mm")
    print(f"Static Min Total Deformation : {data['static']['min']*1000:.4f} mm")
    print(f"\\nModal Results:")
    print(f"  {'Mode':<6} {'Frequency (Hz)':<18} {'Max Deform (mm)'}")
    print(f"  {'-'*42}")
    for m in data['modal']:
        print(f"  {m['mode']:<6} {m['freq_hz']:<18.4f} {m['max_deform']*1000:.6f}")
        
    print(f"Script output: {result}")
    print("Solve complete — check the GUI for results.")

except Exception as e:
    print(f"Error: {e}")
    raise  # re-raise so you see the full traceback