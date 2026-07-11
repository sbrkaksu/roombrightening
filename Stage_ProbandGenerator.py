import os, sys
from pprint import PrettyPrinter #used for pretty-printing the proband data structures when saving to file
import numpy as np
from Formatter import FormatPrinter

"""
printer = FormatPrinter({float: "{:.4e}"}, sort_dicts=False)
"""
printer = FormatPrinter({float: "{}"}, sort_dicts=False)


#generates ProbandLernen.txt for Learning Phase
def generate_learn_proband():
    seed = int.from_bytes(os.urandom(128), sys.byteorder)
    rng = np.random.default_rng(seed)
    stimuli_learning = [ 0.1, 0.147, 0.215, 0.316, 0.464, 0.681, 
            1, 1.47, 2.15, 3.16, 4.64, 6.81, 
            10, 14.7, 21.5, 31.6, 46.4, 68.1, 
            100, 147, 215, 316]
    selected_E_values = rng.choice(stimuli_learning, size=12, replace=False)
    selected_types = rng.permutation([
        "Direct", "Direct", "Direct", "Direct", "Direct", "Direct",
        "Diffuse", "Diffuse", "Diffuse", "Diffuse", "Diffuse", "Diffuse",
    ])
    scenes = [
        scene(
            type=str(scene_type),
            combination_factor=1 if scene_type == "Direct" else 0,
            E=float(E),
            disturbed=None,
            reaction_time=None,
        )
        for scene_type, E in zip(selected_types, selected_E_values)
    ]
    proband = {"ID": -1, "Phase": "Learning Block", "LearnDurchgang": True, "Durchgange": [
        {'ID': -1, "Time": "Evening", "Color": "3000 K", "Scenes" : scenes},
    ]}
    with open("ProbandLernenB.txt", "w") as file:
        file.write(printer.pformat(proband))


def scene(type, combination_factor, E, disturbed, reaction_time):
    return {"Type": type, "Combination_Factor": combination_factor, "E": E, "Disturbed": disturbed, "Reaction Time": reaction_time}
# Generates Probandens grob when this .py file is run


def generate_probanden_E_block():
     
        proband = {"ID": 1, "Phase": "E_Block", "LearnDurchgang": False, "Durchgange": [
            {'ID': 1, "Time": "Evening", "Color": "3000 K", "Scenes" : []},
            {'ID': 2, "Time": "Night", "Color": "3000 K", "Scenes" : []},
        ]}

        with open("Proband_E_Block.txt", "w") as file:
            file.write(printer.pformat(proband))

def generate_probanden_E_block_results(staircase_direct_evening,staircase_diffuse_evening,
                                       staircase_direct_night, staircase_diffuse_night):
     
        proband = {"ID": 1, "Phase": "E_Block", "LearnDurchgang": False, "Durchgange": [
            {'ID': 1, "Time": "Evening", "Color": "3000 K", "Results" : [
                  { "Type": staircase_direct_evening.type_of_illumination,
                    "Combination_Factor": staircase_direct_evening.combination_factor,  
                   "E_threshold": staircase_direct_evening.get_threshold(), 
                   "Reversals": staircase_direct_evening.reversal_points, 
                   "Response_Sequence": staircase_direct_evening.response_sequence_history},

                  { "Type": staircase_diffuse_evening.type_of_illumination,
                    "Combination_Factor": staircase_diffuse_evening.combination_factor,  
                   "E_threshold": staircase_diffuse_evening.get_threshold(), 
                   "Reversals": staircase_diffuse_evening.reversal_points, 
                   "Response_Sequence": staircase_diffuse_evening.response_sequence_history},
            ]},
            {'ID': 2, "Time": "Night", "Color": "3000 K", "Results" : [
                  {"Type": staircase_direct_night.type_of_illumination, 
                   "Combination_Factor": staircase_direct_night.combination_factor,  
                   "E_threshold": staircase_direct_night.get_threshold(), 
                   "Reversals": staircase_direct_night.reversal_points, 
                   "Response_Sequence": staircase_direct_night.response_sequence_history},
                   
                  {"Type": staircase_diffuse_night.type_of_illumination,
                   "Combination_Factor": staircase_diffuse_night.combination_factor,  
                   "E_threshold": staircase_diffuse_night.get_threshold(), 
                   "Reversals": staircase_diffuse_night.reversal_points, 
                   "Response_Sequence": staircase_diffuse_night.response_sequence_history},
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
                  {"E": None, "Reversals (lx)": [], "Reversal Points" : None},
            ]},
            {'ID': 4, "Time": "Night", "Color": "3000 K", "Results" : [
                  {"E": None, "Reversals (lx)": [], "Reversal Points" : None},
            ]},
        ]}

        with open("Proband_Combination_Block_Results.txt", "w") as file:
            file.write(printer.pformat(proband))

if __name__ == "__main__":
    generate_learn_proband()
    generate_probanden_E_block()
    generate_probanden_Combination_block()

