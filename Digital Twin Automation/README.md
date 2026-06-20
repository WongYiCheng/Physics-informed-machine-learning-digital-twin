Digital Twin Automation

There are total of 3 module known as daq_system, feature_extractor, and ansys_twin_updated.

The first module are daq_system where the data acquisition is being done, it involved in dc offset and rectangular windowing of the data. The specifications of the configurations constant. The sampling size is 9,2049 np matrix.

The second module correspond to feature_extractor. The feature that are being extracted are PCA-FRF, WCC and PAR. 

The third module is ansys_twin_updated. It provide the algorithm of how the ANSYS update the model with given input (which is the machine learning fault diagnosis. The current model only support input of 1-4 and severity damage. If case and different function to support LD-MD with different location are not yet being done.

For different ANSYS model, the ansys_twin_updated should vary with the naming for example:

<img width="707" height="715" alt="image" src="https://github.com/user-attachments/assets/aa6fbe8b-5f82-4558-900a-04a45a3b7987" />

Inside the ansys_twin_updated code, 
Part A locates the folder that you ant to make changes
c_folder = [c for c in model.Connections.Children if "Plate bolt" in c.Name][0]
p_folder = [c for c in static.Children if "Plate bolt pretension" in c.Name][0]
naming method is Model.Connections (refer to the model family, inside there are child folder named connections. Inside there are another children file if named Plate_bolt. Same to the Static family

For part b, is to ensure all suppressions are removed

For part c, prepare a function for suppression, then input should be string representation of number such as "3"
suppress_by_name(c_folder.Children, "3") or
suppress_by_name(c_folder.Children, "{bolt_a}")

----------- Below shows comparison of with and without the use of @staticmethod ------
def solve(self, damage_case):   # normal method — needs self (the instance)
        bolt_a, bolt_b = self._bolt_pair(damage_case)

@staticmethod
def _bolt_pair(damage_case):    # static — no self needed, just pure logic
    bolt_a = 2 * damage_case - 1
    bolt_b = 2 * damage_case
    return bolt_a, bolt_b
