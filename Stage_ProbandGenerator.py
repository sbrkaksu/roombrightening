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
     
        proband = {"ID": 1, "Phase": "E_Block", "LearnDurchgang": False, "Durchgange": [
            {'ID': 1, "Time": "Evening", "Color": "3000 K", "Scenes" : []},
            {'ID': 2, "Time": "Night", "Color": "3000 K", "Scenes" : []},
        ]}

        with open("Proband_E_Block.txt", "w") as file:
            file.write(printer.pformat(proband))

def generate_probanden_E_block_results():
     
        proband = {"ID": 1, "Phase": "E_Block", "LearnDurchgang": False, "Durchgange": [
            {'ID': 1, "Time": "Evening", "Color": "3000 K", "Results" : [
                  {"Threshold_E(lx)": None, "Reversals (lx)": [], "Reversal Points" : None},
            ]},
            {'ID': 2, "Time": "Night", "Color": "3000 K", "Results" : [
                  {"Threshold_E(lx)": None, "Reversals (lx)": [], "Reversal Points" : None},
            ]},
        ]}

        with open("Proband_E_Block_Results.txt", "w") as file:
            file.write(printer.pformat(proband))

def generate_probanden_Combination_block():
     
        proband = {"ID": 1, "Phase": "Combination_Block", "LearnDurchgang": False, "Durchgange": [
            {'ID': 3, "Time": "Evening", "Color": "3000 K", "Scenes" : []},
            {'ID': 4, "Time": "Night", "Color": "3000 K", "Scenes" : []},
        ]}

        with open("Proband_Combination_Block.txt", "w") as file:
            file.write(printer.pformat(proband))

def generate_probanden_Combination_block_results():
     
        proband = {"ID": 1, "Phase": "Combination_Block", "LearnDurchgang": False, "Durchgange": [
            {'ID': 3, "Time": "Evening", "Color": "3000 K", "Results" : [
                  {"Threshold_Combination_Factor": None, "Reversals (Combination Factor)": [], "Number of Reversals" : None},
            ]},
            {'ID': 4, "Time": "Night", "Color": "3000 K", "Results" : [
                  {"Threshold_Combination_Factor": None, "Reversals (Combination Factor)": [], "Number of Reversals" : None},
            ]},
        ]}

        with open("Proband_Combination_Block_Results.txt", "w") as file:
            file.write(printer.pformat(proband))

if __name__ == "__main__":
    generate_probanden_E_block()
    generate_probanden_Combination_block()
    generate_probanden_E_block_results()
    generate_probanden_Combination_block_results()
