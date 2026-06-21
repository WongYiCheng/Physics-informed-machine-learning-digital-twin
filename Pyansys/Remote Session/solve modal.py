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
static = model.Analyses[0]   # Static Structural
modal  = model.Analyses[1]   # Modal — adjust index if needed

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
# B. SOLVER SETTINGS
# ============================================================
static.AnalysisSettings.SolverType = SolverType.Direct

# ============================================================
# C. SOLVE BOTH ANALYSES
# ============================================================
static.Solve(True)
modal.Solve(True)

# ============================================================
# D. EXTRACT STATIC RESULTS — Total Deformation
# ============================================================
static_results = {{}}

# Find existing Total Deformation result object in tree
td_list = [r for r in static.Solution.Children
           if r.DataModelObjectCategory == DataModelObjectCategory.TotalDeformation]

if td_list:
    td = td_list[0]
    td.EvaluateAllResults()
    static_results["total_deformation_max_mm"] = td.Maximum.Value   # in metres by default
    static_results["total_deformation_min_mm"] = td.Minimum.Value
else:
    # No result object yet — add one programmatically then evaluate
    td = static.Solution.AddTotalDeformation()
    td.EvaluateAllResults()
    static_results["total_deformation_max_mm"] = td.Maximum.Value
    static_results["total_deformation_min_mm"] = td.Minimum.Value

# ============================================================
# E. EXTRACT MODAL RESULTS — Natural Frequencies + Deformation
# ============================================================
modal_results = {{}}
freq_list = []
deform_list = []

modal_solution = modal.Solution

# Get all frequency results
for child in modal_solution.Children:
    if child.DataModelObjectCategory == DataModelObjectCategory.TotalDeformation:
        mode_num = child.Mode          # mode number (1, 2, 3...)
        child.EvaluateAllResults()
        deform_list.append({{
            "mode": mode_num,
            "frequency_hz": child.ReportedFrequency.Value,
            "max_deformation": child.Maximum.Value
        }})

modal_results["modes"] = deform_list

# ============================================================
# F. RETURN DATA AS JSON STRING
# ============================================================
output = {{
    "bolt_suppressed": {target_bolt},
    "static": static_results,
    "modal": modal_results
}}
""")
    print(f"Script output: {result}")
    print("Solve complete — check the GUI for results.")

except Exception as e:
    print(f"Error: {e}")
    raise  # re-raise so you see the full traceback