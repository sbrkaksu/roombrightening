import os, sys
from pprint import PrettyPrinter #used for pretty-printing the participant data structures when saving to file
import numpy as np
from Formatter import FormatPrinter

"""
printer = FormatPrinter({float: "{:.4e}"}, sort_dicts=False)
"""
printer = FormatPrinter({float: "{}"}, sort_dicts=False)


#generates Participant_Learning_Block.txt for Learning Phase
def generate_learning_participant():
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
            direct_factor=1 if scene_type == "Direct" else 0,
            E=float(E),
            disturbed=None,
            reaction_time=None,
        )
        for scene_type, E in zip(selected_types, selected_E_values)
    ]
    participant = {"ID": -1, "Phase": "Learning Block", "LearnRound": True, "Rounds": [
        {'ID': -1, "State": "Sitting", "Color": "3000 K", "Scenes" : scenes},
    ]}
    with open("Participant_Learning_Block.txt", "w") as file:
        file.write(printer.pformat(participant))


def scene(type, direct_factor, E, disturbed, reaction_time):
    return {"Type": type, "Direct_Factor": direct_factor, "E": E, "Disturbed": disturbed, "Reaction Time": reaction_time}
# Generates participant files when this .py file is run


def generate_participant_first_block():
     
        participant = {"ID": 1, "Phase": "First_Block", "LearnRound": False, "Rounds": [
            {'ID': 1, "State": "Sitting", "Color": "3000 K", "Scenes" : []},
            {'ID': 2, "State": "Sleeping", "Color": "3000 K", "Scenes" : []},
        ]}

        with open("Participant_First_Block.txt", "w") as file:
            file.write(printer.pformat(participant))

def generate_participant_first_block_results(staircase_sitting_df_1, staircase_sitting_df_0,
                                         staircase_sleeping_df_1, staircase_sleeping_df_0):
     
        participant = {"ID": 1, "Phase": "First_Block", "LearnRound": False, "Rounds": [
            {'ID': 1, "State": "Sitting", "Color": "3000 K", "Adaptive_Stimulus": "Illuminance", "Results" : [
                  { "Repetition": 1,
                    "Type": staircase_sitting_df_1.type_of_illumination,
                    "Direct_Factor": staircase_sitting_df_1.direct_factor,  
                   "Stimulus History": staircase_sitting_df_1.history,
                   "Response_Sequence": staircase_sitting_df_1.response_sequence_history,
                   "Reversals": staircase_sitting_df_1.reversal_points,
                   "E_threshold": staircase_sitting_df_1.get_threshold()},

                  { "Repetition": 1,
                    "Type": staircase_sitting_df_0.type_of_illumination,
                    "Direct_Factor": staircase_sitting_df_0.direct_factor,  
                   "Stimulus History": staircase_sitting_df_0.history,
                   "Response_Sequence": staircase_sitting_df_0.response_sequence_history,
                   "Reversals": staircase_sitting_df_0.reversal_points,
                   "E_threshold": staircase_sitting_df_0.get_threshold()},
            ]},
            {'ID': 2, "State": "Sleeping", "Color": "3000 K", "Adaptive_Stimulus": "Illuminance", "Results" : [
                  {"Repetition": 1,
                   "Type": staircase_sleeping_df_1.type_of_illumination, 
                   "Direct_Factor": staircase_sleeping_df_1.direct_factor,  
                   "Stimulus History": staircase_sleeping_df_1.history,
                   "Response_Sequence": staircase_sleeping_df_1.response_sequence_history,
                   "Reversals": staircase_sleeping_df_1.reversal_points,
                   "E_threshold": staircase_sleeping_df_1.get_threshold()},
                    
                  {"Repetition": 1,
                   "Type": staircase_sleeping_df_0.type_of_illumination,
                   "Direct_Factor": staircase_sleeping_df_0.direct_factor,  
                   "Stimulus History": staircase_sleeping_df_0.history,
                   "Response_Sequence": staircase_sleeping_df_0.response_sequence_history,
                   "Reversals": staircase_sleeping_df_0.reversal_points,
                   "E_threshold": staircase_sleeping_df_0.get_threshold()},
            ]},
        ]}

        with open("Participant_First_Block_Results.txt", "w") as file:
            file.write(printer.pformat(participant))

def generate_participant_second_block():
     
        participant = {"ID": 1, "Phase": "Second_Block", "LearnRound": False, "Rounds": [
            {'ID': 3, "State": "Sitting", "Color": "3000 K", "Scenes" : []},
            {'ID': 4, "State": "Sleeping", "Color": "3000 K", "Scenes" : []},
        ]}

        with open("Participant_Second_Block.txt", "w") as file:
            file.write(printer.pformat(participant))

def generate_participant_second_block_results():
     
        participant = {"ID": 1, "Phase": "Second_Block", "LearnRound": False, "Rounds": [
            {'ID': 3, "State": "Sitting", "Color": "3000 K", "Adaptive_Stimulus": "Direct_Factor", "Results" : [
                  {"Repetition": 1, "Illuminance": None, "Stimulus History": [], "Response_Sequence": [], "Reversals": [], "Direct_Factor_threshold": None},
                  {"Repetition": 2, "Illuminance": None, "Stimulus History": [], "Response_Sequence": [], "Reversals": [], "Direct_Factor_threshold": None},
            ]},
            {'ID': 4, "State": "Sleeping", "Color": "3000 K", "Adaptive_Stimulus": "Direct_Factor", "Results" : [
                  {"Repetition": 1, "Illuminance": None, "Stimulus History": [], "Response_Sequence": [], "Reversals": [], "Direct_Factor_threshold": None},
                  {"Repetition": 2, "Illuminance": None, "Stimulus History": [], "Response_Sequence": [], "Reversals": [], "Direct_Factor_threshold": None},
            ]},
        ]}

        with open("Participant_Second_Block_Results.txt", "w") as file:
            file.write(printer.pformat(participant))

if __name__ == "__main__":
    generate_learning_participant()
    generate_participant_first_block()
    generate_participant_second_block()

