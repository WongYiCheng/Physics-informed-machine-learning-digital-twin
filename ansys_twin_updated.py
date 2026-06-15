from ansys.mechanical.core import launch_mechanical
import os


class MechanicalSolver:
    """
    Manages a single Ansys Mechanical session.
    Call run(damage_case) for a one-shot launch → solve → exit.
    Or use launch() / solve() / exit() individually for automation loops.

    Bolt pair mapping:
        damage_case 1 → suppress bolts 1 & 2
        damage_case 2 → suppress bolts 3 & 4
        damage_case 3 → suppress bolts 5 & 6
        damage_case 4 → suppress bolts 7 & 8
    """

    DB_PATH   = r"D:\UM Document\FYP ansys\Remote copy\Remote Copy_files\dp8\global\MECH\SYS.mechdb"
    EXEC_PATH = r"C:\Program Files\ANSYS Inc\v252\aisol\Bin\winx64\AnsysWBU.exe"

    def __init__(self):
        self.mechanical = None

    # ------------------------------------------------------------------
    # ONE-SHOT CONVENIENCE METHOD
    # ------------------------------------------------------------------

    def run(self, damage_case: int):
        """
        Full pipeline in one call: launch → solve → exit.
        Use this when you only need to run a single case.

        Parameters
        ----------
        damage_case : int
            1-based damage index (1–4).
        """
        try:
            self.launch()
            self.solve(damage_case)
        finally:
            self.exit()

    # ------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------

    def launch(self):
        """Kill stale processes and start a fresh Mechanical session."""
        print("Killing stale Ansys processes...")
        os.system("taskkill /f /im AnsysWBU.exe /t")
        os.system("taskkill /f /im Mechanical.exe /t")

        print("Launching Mechanical...")
        self.mechanical = launch_mechanical(
            exec_file=self.EXEC_PATH,
            transport_mode="insecure",
            batch=False,
            cleanup_on_exit=False,
        )

        print("Opening project...")
        self.mechanical.run_python_script(
            f'ExtAPI.DataModel.Project.Open(r"{self.DB_PATH}")'
        )
        print("Session ready.\n")

    def solve(self, damage_case: int):
        """
        Apply damage, solve static + modal, and evaluate total deformation.

        Parameters
        ----------
        damage_case : int
            1-based index mapping to a bolt pair:
            1 → bolts 1&2,  2 → bolts 3&4,  3 → bolts 5&6,  4 → bolts 7&8
        """
        if self.mechanical is None:
            raise RuntimeError("Call launch() before solve().")

        bolt_a, bolt_b = self._bolt_pair(damage_case)
        print(f"[Case {damage_case}] Suppressing bolts {bolt_a} & {bolt_b} ...")

        self.mechanical.run_python_script(
            self._build_script(bolt_a, bolt_b)
        )

        print(f"[Case {damage_case}] Solve complete.\n")

    def exit(self):
        """Gracefully close the Mechanical session."""
        if self.mechanical is not None:
            self.mechanical.exit()
            self.mechanical = None
            print("Mechanical session closed.")

    # ------------------------------------------------------------------
    # PRIVATE HELPERS
    # ------------------------------------------------------------------

    @staticmethod
    def _bolt_pair(damage_case: int):
        """Return the two bolt numbers for a given damage case."""
        bolt_a = 2 * damage_case - 1
        bolt_b = 2 * damage_case
        return bolt_a, bolt_b

    @staticmethod
    def _build_script(bolt_a: int, bolt_b: int) -> str:
        """Build the IronPython script string that runs inside Mechanical."""
        return f"""
from Ansys.Mechanical.DataModel.Enums import SolverType, DataModelObjectCategory

model  = ExtAPI.DataModel.Project.Model
static = model.Analyses[0]
modal  = model.Analyses[1]

# ── A. LOCATE FOLDERS ────────────────────────────────────────────────
c_folder = [c for c in model.Connections.Children if "Plate bolt" in c.Name][0]
p_folder = [c for c in static.Children if "Plate bolt pretension" in c.Name][0]

# ── B. RESET — unsuppress everything ─────────────────────────────────
for b in c_folder.Children: b.Suppressed = False
for p in p_folder.Children: p.Suppressed = False

# ── C. FAULT — suppress the target pair ──────────────────────────────
def suppress_by_name(children, name_token):
    match = [x for x in children if name_token in x.Name]
    if not match:
        raise ValueError("Could not find item containing: " + name_token)
    match[0].Suppressed = True

suppress_by_name(c_folder.Children, "{bolt_a}")
suppress_by_name(c_folder.Children, "{bolt_b}")
suppress_by_name(p_folder.Children, "{bolt_a}")
suppress_by_name(p_folder.Children, "{bolt_b}")

# ── D. SUPPORTS ───────────────────────────────────────────────────────
fixed_list   = [s for s in static.Children if "Fixed"   in s.Name]
elastic_list = [s for s in static.Children if "Elastic" in s.Name]
if fixed_list:   fixed_list[0].Suppressed   = False
if elastic_list: elastic_list[0].Suppressed = True

# ── E. SOLVER SETTINGS ────────────────────────────────────────────────
static.AnalysisSettings.SolverType = SolverType.Direct

# ── F. SOLVE ──────────────────────────────────────────────────────────
static.Solve(True)
modal.Solve(True)

# ── G. EVALUATE TOTAL DEFORMATION (static) ───────────────────────────
td_list = [r for r in static.Solution.Children
           if r.DataModelObjectCategory == DataModelObjectCategory.TotalDeformation]
td = td_list[0] if td_list else static.Solution.AddTotalDeformation()
td.EvaluateAllResults()

# ── H. EVALUATE TOTAL DEFORMATION (all modal modes) ───────────────────
for child in modal.Solution.Children:
    if child.DataModelObjectCategory == DataModelObjectCategory.TotalDeformation:
        child.EvaluateAllResults()

"done"
"""


# ======================================================================
# TEST RUN
# ======================================================================

if __name__ == "__main__":

    # ── Test 1: one-shot run() convenience method ─────────────────────
    print("=" * 50)
    print("TEST 1: one-shot run() for damage case 1")
    print("=" * 50)
    solver = MechanicalSolver()
    solver.run(damage_case=1)
    print("TEST 1 PASSED\n")

    # ── Test 2: manual launch → multi-case loop → exit ────────────────
    print("=" * 50)
    print("TEST 2: manual loop over all 4 damage cases")
    print("=" * 50)
    solver = MechanicalSolver()
    solver.launch()

    for case in range(1, 5):
        solver.solve(case)

    solver.exit()
    print("TEST 2 PASSED\n")

    # ── Test 3: bolt pair mapping sanity check (no Ansys needed) ──────
    print("=" * 50)
    print("TEST 3: bolt pair mapping")
    print("=" * 50)
    expected = {1: (1, 2), 2: (3, 4), 3: (5, 6), 4: (7, 8)}
    for case, (exp_a, exp_b) in expected.items():
        got_a, got_b = MechanicalSolver._bolt_pair(case)
        assert (got_a, got_b) == (exp_a, exp_b), \
            f"Case {case}: expected ({exp_a},{exp_b}), got ({got_a},{got_b})"
        print(f"  Case {case} → bolts {got_a} & {got_b}  ✓")
    print("TEST 3 PASSED\n")

    # ── Test 4: solve() guard — must call launch() first ──────────────
    print("=" * 50)
    print("TEST 4: RuntimeError guard on solve() without launch()")
    print("=" * 50)
    solver = MechanicalSolver()
    try:
        solver.solve(1)
        print("TEST 4 FAILED — should have raised RuntimeError")
    except RuntimeError as e:
        print(f"  Caught expected error: {e}  ✓")
        print("TEST 4 PASSED\n")

    print("All tests done.")
