import os, sys
from pprint import PrettyPrinter #used for pretty-printing the proband data structures when saving to file
import numpy as np
from Formatter import FormatPrinter

printer = FormatPrinter({float: "{:.4e}"}, sort_dicts=False)

"""
#generates ProbandLernen.txt for Learning Phase
def generate_learn_proband():
    proband = {"ID": -1, "Abstufung": "lernen"} # Abstufung = Phase
    durchgang = {"ID": -1, "Diffus": False, "Zeit": "Abend"}
    durchgang["Szenen"] = rng.permutation(scenes_test).tolist()
    proband["Durchgange"] = [durchgang]
    with open("ProbandLernen.txt", "w") as file:
        file.write(printer.pformat(proband))
"""

# Generates Probandens grob when this .py file is run
def generate_probanden_E_block():
    for proband_id in range(1, 5): 
        proband = {"ID": proband_id, "Phase": "E_threshold_determination", "LearnDurchgang": False, "Durchgange": [
            {'ID': 4, "Scenes" : []}
        ]}

        with open("Proband{}_E_Block_Trials.txt".format(proband_id), "w") as file:
            file.write(printer.pformat(proband))

if __name__ == "__main__":
    pass
