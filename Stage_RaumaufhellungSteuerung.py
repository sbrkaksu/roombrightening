# Data parsing, formatting and file handling
from ast import literal_eval #dict type security for participant file reading
import os
from os.path import abspath, basename, dirname, exists, join, splitext #used for saving result files with correct naming and preventing overwriting
from re import compile #used for parsing the monitor input with regular expressions
import sys

# Timing, async flow
import asyncio #used for asynchronous tasks such as running the scene sequences and reading the monitor input without blocking
from itertools import pairwise #used for calculating fade steps in scene transitions
from timeit import default_timer as timer #used for reaction time measurement

# Numerical calculations
import numpy as np

# GUI
import customtkinter as ctk #GUI framework
from tkinter import filedialog, font, DoubleVar, TclError #used for file dialogs, font configuration
from async_tkinter_loop import async_handler #decorator to allow async functions to be used as event handlers in Tkinter
from async_tkinter_loop.mixins import AsyncCTk #mixin to allow the main application class to run asynchronous tasks

# QLC+ and lighting control, communication
from requests import post #communication with QLC+ via HTTP API
import pyartnet as pan #used for controlling the lighting via Art-Net protocol
import serial #used for communication with the measurement monitor via serial port

# Generates fine-grid block
from Stage_ProbandGenerator import FormatPrinter, scene as create_scene, generate_participant_first_block_results, generate_participant_second_block, generate_participant_second_block_results
from Staircase import AdaptiveStaircase
from GUI_widgets import ClickableTable, CheckWindow, ReminderWindow, ResultsWindow, SwitchButton


#4 digits after the decimal point for E values when saving files
printer = FormatPrinter({float: "{:.4e}"},sort_dicts=False)

# Class representing a phase of the experiment
class Phase(dict):
    def __init__(self, participant_file, *args, **kwargs):
        __slots__ = ()
        self.filename = participant_file
        with open(self.filename, 'r') as f:
            s = f.read()
            super().__init__(literal_eval(s))
        self.phase_type = self["Phase"]
        self.seq_num = len(self["Rounds"])
        self.seq_idx = 0
        self.complete = False
    
    def get_current_sequence(self):
        return self["Rounds"][self.seq_idx]
    
    def next_sequence(self):
        self.seq_idx += 1
        if self.seq_idx >= self.seq_num:
            self.seq_idx -= self.seq_num

    def prev_sequence(self):
        self.seq_idx -= 1
        if self.seq_idx < 0:
            self.seq_idx += self.seq_num
    
    def check_completion(self):
        if self.phase_type in ("First_Block", "Second_Block"):
            completed = [round_data.get("Adaptive_Completed") for round_data in self["Rounds"]]
            return bool(completed) and None not in completed and False not in completed

        reactions = [sz.get("Disturbed") for s in self["Rounds"] for sz in s["Scenes"]]
        return bool(reactions) and None not in reactions
        
        
    def save(self):
        filename_base = splitext(self.filename)[0]
        fname = self.filename
        with open(fname, 'w') as f:
            f.write(printer.pformat(self))

        if self.phase_type in ("Learning Block", "First_Block", "Second_Block"):
            return
        
        if self.check_completion() == True:
            self.complete = True
            fname = f"{filename_base}_result_complete.txt"
            counter = 1
            while exists(fname):
                fname = f"{filename_base}_result_complete_{counter}.txt"
                counter += 1
        with open(fname, 'w') as f:
            f.write(printer.pformat(self))

# Main application class
class App(ctk.CTk, AsyncCTk):
    SEQUENCE_CONTROL_VALUES = {
        "isi": 0,
        "fade_isi": 255,
        "scene": 160,
        "fade_scene": 96,
    }

    def __init__(self):
        super().__init__()
        self.setup_window()
        self.setup_settings()
        self.setup_state()
        self.setup_inquery_controls()
        self.setup_sequence_controls()
        self.setup_table()
        self.setup_timer()
        self.setup_qlc_controls()
        self.setup_roomlight_controls()
        self.setup_monitor_controls()
        self.setup_input_bindings()
        self.setup_check_window_state()

    def setup_window(self):
        self.title("Study Light Trespass Into a Room")
        self.geometry("1190x750") 
        self.resizable(False, False)
        self.style = ctk.set_appearance_mode("light") #force to work in light mode

    def setup_settings(self):
        self.settings = {
            "qlc_address":              'localhost:9999',
            "qlc_project":              'stage-qlc.qxw',
            "monitor_serial_port":      'COM3',
            "monitor_baud_rate":        9600,
            "monitor_E_factor_spot_1":  2.33e7,
            "monitor_E_factor_diffus":  2.71e7,
            "monitor_reading_light_I_offset": 9e-10,
            "scene_duration":           4.5, #4.5, # seconds
            "scene_fade_duration":      0.2, # seconds QLC fades in 100 ms
            "inter-stimulus-interval":  2.5, #2.5, #seconds
            "isi_fade_duration" :       0.5, # seconds. QLC fades in 300 ms
            "sequence_pause_duration":  45.0, # 45 seconds
            "maxE_spot1": 165,
            "maxE_diffus": 433,
            "direct_center_curve": (-3.0235e-09, 0.0020, 0.1933),
            "diffuse_curve": (-2.0148e-08, 0.0076, -0.0306),
            "pixel2_7_multiplier_curve": (9.4010e-05, -7.8784e-05, 0.9898),
            "maxAussteuerung_faktor_pixel1": 0.7,
            "DMX_brightness_reading": 255,
            "DMX_brightness_roomlight": 255,
            "learn_participant_file": "Participant_Learning_Block.txt",
            "max_scene_before_sequence_pause": 16,
        }

    def setup_state(self):
        self.monitor_I = None
        self.scene_start_timestamp = None
        self.current_scene_idx = None
        self.active_phase = None
        self.active_sequence = None
        self.active_scene = None
        self.active_staircase = None
        self.table_scene_offset = 0
        self.sequence_task = None
        self.active_block_reset_requested = False

        self.phase_learning_block = None
        self.phase_first_block = None
        self.phase_second_block = None
        self.first_block_file = "Participant_First_Block.txt"
        self.second_block_file = "Participant_Second_Block.txt"
        self.first_block_results_file = "Participant_First_Block_Results.txt"
        self.second_block_results_file = "Participant_Second_Block_Results.txt"

        self.staircase_sitting_df_1 = None
        self.staircase_sitting_df_0 = None
        self.staircase_sleeping_df_1 = None
        self.staircase_sleeping_df_0 = None
        self.staircase_sitting_second_rep_1 = None
        self.staircase_sitting_second_rep_2 = None
        self.staircase_sleeping_second_rep_1 = None
        self.staircase_sleeping_second_rep_2 = None
        self.first_block_results_saved = False
        self.second_block_results_saved = False
        self.mid_break_reminder_shown = False

        self.sequence_stop_event = asyncio.Event()
        self.sequence_continue_event = asyncio.Event()
        self.pause_stop_event = asyncio.Event()
        self.scene_disturbing = asyncio.Event()
        self.freeze_qlc_active = False

    def setup_inquery_controls(self): #frame on the top right of the GUI
        self.inquery_frame = ctk.CTkFrame(self)
        self.inquery_frame.grid(row=0, column=2, padx=10, pady=10, sticky="nw")
        self.inquery_label = ctk.CTkLabel(self.inquery_frame, text="Is the scene disturbing?").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.stoer_button = ctk.CTkButton(self.inquery_frame, text="Yes", command=lambda: self.set_scene_reaction(disturbing=True))
        self.stoer_button.grid(row=1, column=0, padx=10, pady=10, sticky="w")

    def setup_sequence_controls(self):
        self.seq_crtl_frame = ctk.CTkFrame(self, width=150)
        self.seq_crtl_frame.grid(row=0, column=0, padx=10, pady=10, sticky="wn")

        phase_buttons_settings = {"height":90, "anchor":"n", "border_width":2, "text_color":"black", "border_color":"black",
                                     "fg_color":"transparent", "hover_color":"light blue"}
        first_block_button_settings = {**phase_buttons_settings, "height": 120}
        sequence_buttons_settings = {"height":25, "border_width":1, "text_color":"black", "border_color":"black",
                                        "fg_color":"transparent", "hover_color":"light blue"}

        self.load_participant_button = ctk.CTkButton(self.seq_crtl_frame, text="Load Participant File", command=self.load_participant)
        self.load_participant_button.grid(row=0, column=0, padx=10, pady=10, sticky="n")

        self.learning_block_button = SwitchButton(self.seq_crtl_frame, group="phase", on_color="green", text="Learning Block", **phase_buttons_settings, command=self.load_learning_block, state="disabled")
        self.learning_block_button.grid(row=1, column=0, padx=10, pady=10, sticky="n")

        self.first_block_button = SwitchButton(self.seq_crtl_frame, group="phase", on_color="green", text="First Block", **first_block_button_settings, command=self.select_first_block, state="disabled")
        self.first_block_button.grid(row=2, column=0, padx=10, pady=10, sticky="n")
        self.first_block_prev_seq_button = ctk.CTkButton(self.first_block_button, **sequence_buttons_settings, width=30, text="<", command=self.set_prev_sequence, state="disabled")
        self.first_block_next_seq_button = ctk.CTkButton(self.first_block_button, **sequence_buttons_settings, width=30, text=">", command=self.set_next_sequence, state="disabled")
        self.first_block_prev_seq_button.place(relx=0.3, rely=0.48, anchor="center")
        self.first_block_next_seq_button.place(relx=0.7, rely=0.48, anchor="center")
        self.first_block_results_button = ctk.CTkButton(self.first_block_button, **sequence_buttons_settings, width=70, text="Results", command=self.open_first_block_results, state="disabled")
        self.first_block_results_button.place(relx=0.5, rely=0.78, anchor="center")

        self.second_block_button = SwitchButton(self.seq_crtl_frame, group="phase", on_color="green", text="Second Block", **first_block_button_settings, command=lambda:self.set_phase(self.phase_second_block), state="disabled")
        self.second_block_button.grid(row=3, column=0, padx=10, pady=10, sticky="n")
        self.second_block_prev_seq_button = ctk.CTkButton(self.second_block_button, **sequence_buttons_settings, width=30, text="<", command=self.set_prev_sequence, state="disabled")
        self.second_block_next_seq_button = ctk.CTkButton(self.second_block_button, **sequence_buttons_settings, width=30, text=">", command=self.set_next_sequence, state="disabled")
        self.second_block_prev_seq_button.place(relx=0.3, rely=0.48, anchor="center")
        self.second_block_next_seq_button.place(relx=0.7, rely=0.48, anchor="center")
        self.second_block_results_button = ctk.CTkButton(self.second_block_button, **sequence_buttons_settings, width=70, text="Results", command=self.open_second_block_results, state="disabled")
        self.second_block_results_button.place(relx=0.5, rely=0.78, anchor="center")

        self.sequence_start_reset_button = ctk.CTkButton(self.seq_crtl_frame, text="Start Sequence", command=self.run_sequence, state="disabled")
        self.sequence_start_reset_button.grid(row=4, column=0, padx=10, pady=10, sticky="n")

        self.sequence_stop_continue_button = ctk.CTkButton(self.seq_crtl_frame, text="Pause Sequence", command=self.stop_sequence, state="disabled")
        self.sequence_stop_continue_button.grid(row=5, column=0, padx=10, pady=10, sticky="n")

    def setup_table(self):
        self.table_frame = ctk.CTkFrame(self,fg_color="transparent")
        self.table_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nw")
        self.participant_label = ctk.CTkLabel(self.table_frame, text="Participant", anchor="w", font=(font.nametofont("TkDefaultFont"), 18))
        self.participant_label.grid(row=0, column=0, padx=10, pady=(10,0),sticky='w')
        self.sequence_scene_label = ctk.CTkLabel(self.table_frame, text="Round", anchor="w", font=(font.nametofont("TkDefaultFont"), 18))
        self.sequence_scene_label.grid(row=1, column=0, padx=10, pady=0, sticky='w')

        self.sequence_table = ClickableTable(self.table_frame, header_labels=["Scenes", "Type", "Direct Factor", "E", "E Monitor", "Disturbing", "Reaction Time"], row_num=25)
        self.sequence_table.grid(row=2, column=0, padx=0, pady=10, sticky="w")
        self.sequence_table.set_callback(self.row_click)

    def setup_timer(self):
        self.timer_running = False
        self.countdown_timer_var = DoubleVar()
        self.countdown_timer_var.trace_add('write', self.print_countdown_timer)
        self.scene_countdown_end = 0.0
        self.scene_countdown_finished = asyncio.Event()
        self.countdown_after_id = None
        self.countdown_label  = ctk.CTkLabel(self.table_frame, text="Test", font=(font.nametofont("TkDefaultFont"), 18))
        self.countdown_label.place(relx=0.89, y=14, anchor="nw")
        self.countdown_digits = ctk.CTkLabel(self.table_frame, text="00.0", font=(font.nametofont("TkDefaultFont"), 18))
        self.countdown_digits.place(relx=0.88, y=14, anchor="ne")

    def setup_qlc_controls(self):
        self.qlc_init_button = ctk.CTkButton(self, text="QLC+ initialisieren", command=self.init_qlc)
        self.qlc_init_button.grid(row=1, column=2, padx=10, pady=10, sticky="nw")

        self.artnet_interface_helperbutton = ctk.CTkButton(self, command=self.create_artnet_interface)
        self.project_loaded = False
        self.after(100,self.artnet_interface_helperbutton.invoke) # workaround, because async does not work in __init__

    def setup_roomlight_controls(self):
        self.roomlight_button = ctk.CTkButton(self.seq_crtl_frame, text="Roomlight", command=lambda:self.set_roomlight_level(2))
        self.roomlight_button.grid(row=7, column=0, padx=10, pady=10, sticky="s")
        self.freeze_qlc_button = ctk.CTkButton(self.seq_crtl_frame, text="Freeze QLC", command=self.toggle_freeze_qlc)
        self.freeze_qlc_button.grid(row=9, column=0, padx=10, pady=(0, 10), sticky="s")

    def setup_monitor_controls(self):
        self.read_monitor_button = ctk.CTkButton(self, command=self.read_monitor_continuously)
        self.after(100,self.read_monitor_button.invoke)

    def setup_input_bindings(self):
        self.bind("<F20>", lambda e: self.set_scene_reaction(disturbing=True))

    def setup_check_window_state(self):
        self.position_window = None
        self.state_position_status = None
        self.position_checked_round = None

    @async_handler
    async def read_monitor_continuously(self):
        port = self.settings["monitor_serial_port"]
        baud = self.settings["monitor_baud_rate"]
        value_pattern = compile(r'[+-]\d+\.\d+ E[+-]\d\d')
        try:
            with serial.Serial(port, baud, timeout=1) as ser:
                ser.dtr = True
                raw_text = ''
                while True:
                    if ser.in_waiting > 0:  # Check whether data is available
                        raw_text += ser.read(ser.in_waiting).decode('ascii')  # All available bytes
                        while True:
                            match = value_pattern.search(raw_text)
                            if match:
                                raw_text = raw_text[match.end():]
                                photocurrent = float(match.group().replace(' ', ''))
                                self.monitor_I = photocurrent
                            else:
                                break
                    await asyncio.sleep(0.2)
        except serial.SerialException as e:
            print(f"Fehler beim Zugriff auf {port}: {e}")
        except KeyboardInterrupt:
            print("\nProgramm beendet.")

    def set_scene_monitor(self):
        if self.monitor_I and self.active_scene is not None:
            print(self.monitor_I)
            monitor_I = self.monitor_I
            if self.active_sequence is not None and self.active_sequence["State"] == "Sitting":
                monitor_I = max(0, monitor_I - self.settings["monitor_reading_light_I_offset"])
            direct_factor = self.active_scene["Direct_Factor"]
            factor_direct = self.settings["monitor_E_factor_spot_1"]
            factor_diffuse = self.settings["monitor_E_factor_diffus"]
            factor = (factor_direct * direct_factor) + (factor_diffuse * (1 - direct_factor))
            EM = monitor_I * factor
            EM = f"{EM:.2e}" # format E monitor in exponential notation for the table
            print(EM)
            self.sequence_table.update_cell(EM, "E Monitor")
            self.active_scene["E_monitor"] = EM
    
    def open_check_window(self, state=None):
        if state is not None:
            title, label = {
                "Sitting": ("Participant position: sitting", "Participant is sitting"),
                "Sleeping": ("Participant position: sleeping", "Participant is sleeping"),
            }[state]
            self.position_window = self.show_check_window(self.position_window, title, label)

    def show_check_window(self, window, title, label):
        if window is None or not window.winfo_exists():
            window = CheckWindow(self,title=title,label=label)
        else:
            window.focus()
        self.wait_window(window)
        return window

    def format_result_value_list(self, values):
        if not values:
            return "None"
        return ", ".join(str(value) for value in values)

    def format_first_block_results_text(self, results_data):
        lines = []
        for round_data in results_data["Rounds"]:
            lines.append("Round {id} | {state}".format(id=round_data["ID"], state=round_data["State"]))
            lines.append("")
            for result in round_data["Results"]:
                reversals = result.get("Reversals", [])
                threshold = result.get("E_threshold")
                threshold_text = f"{threshold:.4f}".rstrip("0").rstrip(".") if threshold is not None else "None"
                response_sequence = result.get("Response_Sequence", [])
                lines.append("{type} | DF={df}".format(type=result.get("Type"), df=result.get("Direct_Factor")))
                lines.append("Trials: {trials}".format(trials=len(response_sequence)))
                lines.append("Reversal: {reversals} - {count} reversals".format(
                    reversals=self.format_result_value_list(reversals),
                    count=len(reversals),
                ))
                lines.append("Threshold: {threshold} Lx".format(threshold=threshold_text))
                lines.append("")
            lines.append("")
        return "\n".join(lines).strip()

    def show_first_block_results_popup(self):
        results_file = self.first_block_results_file
        if not exists(results_file):
            ResultsWindow(self, "First Block Results", "Result file not found.")
            return

        with open(results_file, "r") as file:
            results_data = literal_eval(file.read())

        ResultsWindow(self, "First Block Results", self.format_first_block_results_text(results_data))

    def open_first_block_results(self):
        if not self.first_block_results_saved:
            print("First Block is not completed.")
            return
        self.show_first_block_results_popup()

    def format_second_block_results_text(self, results_data):
        lines = []
        for round_data in results_data["Rounds"]:
            lines.append("Round {id} | {state}".format(id=round_data["ID"], state=round_data["State"]))
            lines.append("")
            for result in round_data["Results"]:
                reversals = result.get("Reversals", [])
                threshold = result.get("Direct_Factor_threshold")
                threshold_text = f"{threshold:.4f}".rstrip("0").rstrip(".") if threshold is not None else "None"
                response_sequence = result.get("Response_Sequence", [])
                lines.append("Mixed | Repetition {rep} | Illuminance={illuminance} Lx".format(
                    rep=result.get("Repetition"),
                    illuminance=result.get("Illuminance"),
                ))
                lines.append("Trials: {trials}".format(trials=len(response_sequence)))
                lines.append("Reversal: {reversals} - {count} reversals".format(
                    reversals=self.format_result_value_list(reversals),
                    count=len(reversals),
                ))
                lines.append("Threshold: {threshold}".format(threshold=threshold_text))
                lines.append("")
            lines.append("")
        return "\n".join(lines).strip()

    def show_second_block_results_popup(self):
        results_file = self.second_block_results_file
        if not exists(results_file):
            ResultsWindow(self, "Second Block Results", "Result file not found.")
            return

        with open(results_file, "r") as file:
            results_data = literal_eval(file.read())

        ResultsWindow(self, "Second Block Results", self.format_second_block_results_text(results_data))

    def open_second_block_results(self):
        if not self.second_block_results_saved:
            print("Second Block is not completed.")
            return
        self.show_second_block_results_popup()

    def load_first_block_diffuse_thresholds(self):
        results_file = self.first_block_results_file
        if not exists(results_file):
            print("First Block result file not found.")
            return None, None

        with open(results_file, "r") as file:
            results_data = literal_eval(file.read())

        thresholds = {}
        for round_data in results_data["Rounds"]:
            state = round_data["State"]
            diffuse_results = [
                result for result in round_data["Results"]
                if result.get("Direct_Factor") == 0
            ]
            if not diffuse_results:
                print(f"{state} diffuse threshold is missing.")
                return None, None

            threshold = diffuse_results[0].get("E_threshold")
            if threshold is None:
                print(f"{state} diffuse threshold is None.")
                return None, None

            thresholds[state] = threshold

        if "Sitting" not in thresholds:
            print("Sitting diffuse threshold is missing.")
            return None, None
        if "Sleeping" not in thresholds:
            print("Sleeping diffuse threshold is missing.")
            return None, None

        return thresholds["Sitting"], thresholds["Sleeping"]
    
    def row_click(self,row_idx):
        if self.sequence_task is not None: # if task exists
            if self.sequence_task.done() is False: # if Task is running
                if not self.sequence_stop_event.is_set(): # if Task not stopped
                    print("Task is not stopped")
                    return
        else: # task does not exist
            if self.active_sequence is None: # if participant not loaded
                print("Participant not loaded")
                return
        if self.active_phase.phase_type in ("First_Block", "Second_Block"):
            scene_idx = self.table_scene_offset + row_idx
        else:
            scene_idx = row_idx

        if scene_idx >= len(self.active_sequence["Scenes"]):
            return

        self.current_scene_idx = scene_idx
        self.sequence_table.select_row(row_idx)

    def set_participant_file_family(self, selected_file):
        filename_pattern = compile(
            r"^(Participant(?:_\d+)?)_(First_Block(?:_Results)?|Second_Block(?:_Results)?)\.txt$"
        )
        match = filename_pattern.fullmatch(basename(selected_file))
        if match is None:
            return

        folder = dirname(abspath(selected_file))
        participant_prefix = match.group(1)
        self.first_block_file = join(folder, f"{participant_prefix}_First_Block.txt")
        self.first_block_results_file = join(folder, f"{participant_prefix}_First_Block_Results.txt")
        self.second_block_file = join(folder, f"{participant_prefix}_Second_Block.txt")
        self.second_block_results_file = join(folder, f"{participant_prefix}_Second_Block_Results.txt")

    def load_participant(self):
        participant_file = filedialog.askopenfilename(filetypes=[("Text file", "*.txt"),("All files", "*.*")])
        if not participant_file:
            return

        with open(participant_file, "r") as file:
            participant_data = literal_eval(file.read())

        self.set_participant_file_family(participant_file)

        if (
            participant_data.get("Phase") == "First_Block"
            and participant_data.get("Rounds")
            and "Results" in participant_data["Rounds"][0]
        ):
            self.load_from_first_block_results(participant_file)
            return
        if (
            participant_data.get("Phase") == "Second_Block"
            and participant_data.get("Rounds")
            and "Results" in participant_data["Rounds"][0]
        ):
            self.load_from_second_block_results(participant_file)
            return

        phase = Phase(participant_file)
        if phase.phase_type == "First_Block":
            self.phase_first_block = phase
            self.rebuild_first_block_staircases_from_scenes()
            self.mid_break_reminder_shown = False
            self.learning_block_button.enable()
            self.first_block_button.disable()
            self.active_phase = None
            self.active_sequence = None
            self.participant_label.configure(text="Participant {id}: First Block loaded".format(id=self.phase_first_block["ID"]))
            self.sequence_scene_label.configure(text="Select Learning Block")
            self.sequence_table.update_table([])
            self.sequence_start_reset_button.configure(state="disabled")
        elif phase.phase_type == "Second_Block":
            self.phase_second_block = phase
            if not self.rebuild_second_block_staircases_from_scenes():
                self.phase_second_block = None
                return
            self.second_block_button.enable()
            if self.all_second_block_staircases_finished():
                for round_data in self.phase_second_block["Rounds"]:
                    round_data["Adaptive_Completed"] = True
                self.phase_second_block.save()
                self.save_second_block_results_if_complete()
            self.restore_block_ui(self.phase_second_block)
        else:
            print(f"Unsupported phase type: {phase.phase_type}")

    def load_from_first_block_results(self, results_file):
        self.first_block_results_file = results_file
        self.first_block_results_saved = True
        self.first_block_results_button.configure(state="normal")

        if exists(self.settings["learn_participant_file"]):
            self.phase_learning_block = Phase(self.settings["learn_participant_file"])

        if exists(self.first_block_file):
            self.phase_first_block = Phase(self.first_block_file)
            self.rebuild_first_block_staircases_from_scenes()
            for round_data in self.phase_first_block["Rounds"]:
                round_data["Adaptive_Completed"] = True
            self.first_block_results_saved = True

        self.learning_block_button.enable()
        self.learning_block_button.turn_on()
        self.first_block_button.enable()
        self.first_block_button.turn_on()

        if not self.prepare_second_block(activate=True):
            return
        self.participant_label.configure(text="Participant {id}: First Block completed".format(id=self.phase_second_block["ID"]))

    def load_from_second_block_results(self, results_file):
        self.second_block_results_file = results_file

        self.learning_block_button.enable()
        self.learning_block_button.turn_on()
        self.first_block_button.enable()
        self.first_block_button.turn_on()
        self.second_block_button.enable()
        self.second_block_button.turn_on()

        if exists(self.second_block_file):
            self.phase_second_block = Phase(self.second_block_file)
            if not self.rebuild_second_block_staircases_from_scenes():
                self.phase_second_block = None
                return
            if self.all_second_block_staircases_finished():
                for round_data in self.phase_second_block["Rounds"]:
                    round_data["Adaptive_Completed"] = True
            self.second_block_results_saved = True
            self.second_block_results_button.configure(state="normal")
            self.restore_block_ui(self.phase_second_block)
        else:
            self.second_block_results_saved = True
            self.second_block_results_button.configure(state="normal")
            self.active_phase = None
            self.active_sequence = None
            self.sequence_table.update_table([])
            self.sequence_start_reset_button.configure(state="disabled")

        self.participant_label.configure(text="Participant 1: Second Block completed")

    def create_first_block_staircases(self):
        self.staircase_sitting_df_1 = AdaptiveStaircase(state="sitting", adaptive_stimulus="Illuminance", direct_factor=1)
        self.staircase_sitting_df_0 = AdaptiveStaircase(state="sitting", adaptive_stimulus="Illuminance", direct_factor=0)
        self.staircase_sleeping_df_1 = AdaptiveStaircase(state="sleeping", adaptive_stimulus="Illuminance", direct_factor=1)
        self.staircase_sleeping_df_0 = AdaptiveStaircase(state="sleeping", adaptive_stimulus="Illuminance", direct_factor=0)
        self.first_block_results_saved = False

    def create_second_block_staircases(self):
        sitting_illuminance_threshold, sleeping_illuminance_threshold = self.load_first_block_diffuse_thresholds()
        if sitting_illuminance_threshold is None or sleeping_illuminance_threshold is None:
            print("Second Block staircases could not be created.")
            return False

        self.staircase_sitting_second_rep_1 = AdaptiveStaircase(state="sitting", adaptive_stimulus="Direct_Factor", illuminance=sitting_illuminance_threshold)
        self.staircase_sitting_second_rep_2 = AdaptiveStaircase(state="sitting", adaptive_stimulus="Direct_Factor", illuminance=sitting_illuminance_threshold)
        self.staircase_sleeping_second_rep_1 = AdaptiveStaircase(state="sleeping", adaptive_stimulus="Direct_Factor", illuminance=sleeping_illuminance_threshold)
        self.staircase_sleeping_second_rep_2 = AdaptiveStaircase(state="sleeping", adaptive_stimulus="Direct_Factor", illuminance=sleeping_illuminance_threshold)
        self.second_block_results_saved = False
        return True

    def prepare_second_block(self, activate=False):
        if not exists(self.second_block_file):
            generate_participant_second_block(self.second_block_file)

        self.phase_second_block = Phase(self.second_block_file)
        if not self.rebuild_second_block_staircases_from_scenes():
            self.phase_second_block = None
            return False

        self.second_block_button.enable()
        if self.all_second_block_staircases_finished():
            for round_data in self.phase_second_block["Rounds"]:
                round_data["Adaptive_Completed"] = True
            self.phase_second_block.save()
            self.save_second_block_results_if_complete()

        if activate:
            self.restore_block_ui(self.phase_second_block)
        return True

    def restore_block_ui(self, phase):
        incomplete_indices = [
            index
            for index, round_data in enumerate(phase["Rounds"])
            if not round_data.get("Adaptive_Completed", False)
        ]
        phase.seq_idx = incomplete_indices[0] if incomplete_indices else len(phase["Rounds"]) - 1
        self.set_phase(phase)

        scenes = self.active_sequence["Scenes"]
        scene_limit = self.settings["max_scene_before_sequence_pause"]
        if self.active_sequence.get("Adaptive_Completed", False):
            self.table_scene_offset = max(0, ((max(1, len(scenes)) - 1) // scene_limit) * scene_limit)
        else:
            self.table_scene_offset = (len(scenes) // scene_limit) * scene_limit
        self.set_sequence()

    def get_active_first_block_staircases(self):
        staircases = []

        if self.active_sequence["State"] == "Sitting":
            staircases = [
                self.staircase_sitting_df_1,
                self.staircase_sitting_df_0,
            ]

        elif self.active_sequence["State"] == "Sleeping":
            staircases = [
                self.staircase_sleeping_df_1,
                self.staircase_sleeping_df_0,
            ]

        else:
            print(f"Unsupported First Block state: {self.active_sequence['State']}")

        return staircases

    def get_active_second_block_staircases(self):
        if self.active_sequence["State"] == "Sitting":
            return [
                self.staircase_sitting_second_rep_1,
                self.staircase_sitting_second_rep_2,
            ]

        if self.active_sequence["State"] == "Sleeping":
            return [
                self.staircase_sleeping_second_rep_1,
                self.staircase_sleeping_second_rep_2,
            ]

        print(f"Unsupported Second Block state: {self.active_sequence['State']}")
        return []

    def get_active_second_block_staircase(self):
        staircases = self.get_active_second_block_staircases()
        for staircase in staircases:
            if staircase is not None and not staircase.is_finished():
                return staircase

        return None

    def active_second_block_round_completed(self):
        staircases = self.get_active_second_block_staircases()
        return all(staircase is not None and staircase.is_finished() for staircase in staircases)

    def all_first_block_staircases_finished(self):
        staircases = [
            self.staircase_sitting_df_1,
            self.staircase_sitting_df_0,
            self.staircase_sleeping_df_1,
            self.staircase_sleeping_df_0,
        ]
        return all(staircase is not None and staircase.is_finished() for staircase in staircases)

    def all_second_block_staircases_finished(self):
        staircases = [
            self.staircase_sitting_second_rep_1,
            self.staircase_sitting_second_rep_2,
            self.staircase_sleeping_second_rep_1,
            self.staircase_sleeping_second_rep_2,
        ]
        return all(staircase is not None and staircase.is_finished() for staircase in staircases)

    def save_first_block_results_if_complete(self):
        if self.first_block_results_saved:
            return
        if not self.all_first_block_staircases_finished():
            return

        generate_participant_first_block_results(
            self.staircase_sitting_df_1,
            self.staircase_sitting_df_0,
            self.staircase_sleeping_df_1,
            self.staircase_sleeping_df_0,
            self.first_block_results_file,
        )
        self.first_block_results_saved = True
        self.first_block_results_button.configure(state="normal")
        self.prepare_second_block()

    def save_second_block_results_if_complete(self):
        if self.second_block_results_saved:
            return
        if not self.all_second_block_staircases_finished():
            return

        generate_participant_second_block_results(
            self.staircase_sitting_second_rep_1,
            self.staircase_sitting_second_rep_2,
            self.staircase_sleeping_second_rep_1,
            self.staircase_sleeping_second_rep_2,
            self.second_block_results_file,
        )
        self.second_block_results_saved = True
        self.second_block_results_button.configure(state="normal")

    def complete_active_first_block_round(self):
        self.active_sequence["Adaptive_Completed"] = True
        self.active_phase.save()
        self.save_first_block_results_if_complete()

    def complete_active_second_block_round(self):
        self.active_sequence["Adaptive_Completed"] = True
        self.active_phase.save()
        self.save_second_block_results_if_complete()

    def load_learning_block(self):
        learn_file = self.settings["learn_participant_file"]
        if not exists(learn_file):
            print(f"Learning block file not found: {learn_file}")
            return
        self.phase_learning_block = Phase(learn_file)
        self.set_phase(self.phase_learning_block)

    def select_first_block(self):
        if self.phase_first_block is None:
            return
        if self.phase_learning_block is None or self.phase_learning_block.check_completion() is not True:
            print("Complete the Learning Block before starting First Block.")
            return
        self.restore_block_ui(self.phase_first_block)

    def select_random_staircase(self, staircases):
        seed = int.from_bytes(os.urandom(128), sys.byteorder)
        rng = np.random.default_rng(seed)

        available_staircases = []
        for staircase in staircases:
            if not staircase.is_finished():
                available_staircases.append(staircase)

        if not available_staircases:
            return None

        index = int(rng.integers(0, len(available_staircases)))
        return available_staircases[index]
        
    def generate_and_load_phase_fein(self):
        pass
        
    def set_next_sequence(self):
        if self.active_phase is not None and self.active_phase.phase_type in ("First_Block", "Second_Block"):
            self.change_active_block_page_or_sequence(1)
            return
        self.change_sequence(1)
    
    def set_prev_sequence(self):
        if self.active_phase is not None and self.active_phase.phase_type in ("First_Block", "Second_Block"):
            self.change_active_block_page_or_sequence(-1)
            return
        self.change_sequence(-1)

    def get_active_block_pages(self):
        pages = []
        scene_limit = self.settings["max_scene_before_sequence_pause"]

        for sequence_idx, sequence in enumerate(self.active_phase["Rounds"]):
            scenes = sequence["Scenes"]
            if scenes:
                for page_offset in range(0, len(scenes), scene_limit):
                    pages.append((sequence_idx, page_offset))
                if (
                    len(scenes) % scene_limit == 0
                    and not sequence.get("Adaptive_Completed", False)
                ):
                    pages.append((sequence_idx, len(scenes)))
            else:
                pages.append((sequence_idx, 0))

        return pages

    def change_active_block_page_or_sequence(self, step):
        pages = self.get_active_block_pages()
        current_page = (self.active_phase.seq_idx, self.table_scene_offset)
        current_page_idx = pages.index(current_page)
        next_page_idx = (current_page_idx + step) % len(pages)
        sequence_idx, page_offset = pages[next_page_idx]

        self.active_phase.seq_idx = sequence_idx
        self.table_scene_offset = page_offset
        self.current_scene_idx = None
        self.set_sequence()

    def change_sequence(self, step):
        if self.active_phase is None:
            return
        if step > 0:
            self.active_phase.next_sequence()
        else:
            self.active_phase.prev_sequence()
        self.set_sequence()
        
    def set_phase(self,phase):
        if phase is None:
            return
        self.active_phase = phase
        self.table_scene_offset = 0
        self.set_sequence()
        self.participant_label.configure(text="Participant {id}: {phase}".format(id=self.active_phase["ID"], phase=self.active_phase["Phase"]))
    
    def set_sequence_scene_label(self):
        if self.active_sequence is None:
            return
        scenes = self.active_sequence["Scenes"]
        if self.active_phase.phase_type in ("First_Block", "Second_Block"):
            progress = self.current_scene_idx + 1 if self.current_scene_idx is not None else len(scenes)
            if self.active_phase.phase_type == "First_Block":
                adaptive_stimulus = "Illuminance"
                fixed_stimulus = "Direct Factor"
            else:
                adaptive_stimulus = "Direct Factor"
                fixed_stimulus = "Illuminance"
            label = "Round {did} | Trial {pgr} | Position: {state} | Adaptive Stimulus: {adaptive_stimulus} | Fixed Stimulus: {fixed_stimulus}".format(
                did=self.active_sequence["ID"],
                pgr=progress,
                state=self.active_sequence["State"],
                adaptive_stimulus=adaptive_stimulus,
                fixed_stimulus=fixed_stimulus,
            )
        else:
            progress = self.current_scene_idx + 1 if self.current_scene_idx is not None else 0
            scene_count = len(scenes)
            label = "Round {did} | Trial {pgr}/{num} | Position: {state}".format(
                did=self.active_sequence["ID"],
                pgr=progress,
                num=scene_count,
                state=self.active_sequence["State"],
            )
        self.sequence_scene_label.configure(text=label)
        
    def set_sequence(self):
        self.active_sequence = self.active_phase.get_current_sequence()
        scenes = self.active_sequence["Scenes"]
        if self.active_phase.phase_type in ("First_Block", "Second_Block"):
            scene_limit = self.settings["max_scene_before_sequence_pause"]
            visible_scenes = scenes[self.table_scene_offset:self.table_scene_offset + scene_limit]
            seq_values = [[self.table_scene_offset + idx + 1, s.get("Type"), str(s.get("Direct_Factor")), s.get("E"), s.get("E_monitor"), s.get("Disturbed"), s.get("Reaction Time")] for idx, s in enumerate(visible_scenes)]
            if (
                not self.active_sequence.get("Adaptive_Completed", False)
                and self.table_scene_offset <= len(scenes) < self.table_scene_offset + scene_limit
            ):
                for idx in range(len(seq_values), scene_limit):
                    seq_values.append([self.table_scene_offset + idx + 1, None, None, None, None, None, None])
        else:
            seq_values = [[idx + 1, s.get("Type"), str(s.get("Direct_Factor")), s.get("E"), s.get("E_monitor"), s.get("Disturbed"), s.get("Reaction Time")] for idx, s in enumerate(scenes)]
        self.sequence_table.update_table(seq_values)

        self.set_sequence_scene_label()
        active_block_can_start = (
            self.active_phase.phase_type in ("First_Block", "Second_Block")
            and not self.active_sequence.get("Adaptive_Completed", False)
            and self.table_scene_offset <= len(scenes) < self.table_scene_offset + self.settings["max_scene_before_sequence_pause"]
        )
        can_start = active_block_can_start if self.active_phase.phase_type in ("First_Block", "Second_Block") else bool(scenes)
        self.sequence_start_reset_button.configure(state="normal" if can_start else "disabled")
    
    def stop_sequence(self):
        self.set_sequence_paused(True)
        self.sequence_stop_event.set()
        
    def continue_sequence(self):
        self.set_sequence_paused(False)
        self.sequence_continue_event.set()

    def set_sequence_paused(self, paused):
        if paused:
            self.sequence_stop_continue_button.configure(text="Continue Sequence",
                                                      command=self.continue_sequence,
                                                      fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"])
            self.roomlight_button.configure(state="normal")
            self.set_roomlight_level(1)
        else:
            self.sequence_stop_continue_button.configure(text="Pause Sequence", command=self.stop_sequence, fg_color="red")
            self.roomlight_button.configure(state="disabled")
            self.set_roomlight_level(0)
        
    def reset_sequence(self):
        self.pause_stop_event.set()
        if self.active_phase is not None and self.active_phase.phase_type in ("First_Block", "Second_Block"):
            self.active_block_reset_requested = True
        self.sequence_task.cancel()

    @staticmethod
    def response_from_scene(scene):
        disturbed = scene.get("Disturbed")
        if disturbed == "Yes":
            return "+"
        if disturbed == "No":
            return "-"
        return None

    def rebuild_first_block_staircases_from_scenes(self):
        self.create_first_block_staircases()
        staircases_by_state_and_df = {
            ("Sitting", 1): self.staircase_sitting_df_1,
            ("Sitting", 0): self.staircase_sitting_df_0,
            ("Sleeping", 1): self.staircase_sleeping_df_1,
            ("Sleeping", 0): self.staircase_sleeping_df_0,
        }

        for round_data in self.phase_first_block["Rounds"]:
            state = round_data["State"]
            for scene in round_data["Scenes"]:
                response = self.response_from_scene(scene)
                if response is None:
                    continue
                staircase = staircases_by_state_and_df[(state, scene["Direct_Factor"])]
                staircase.update(response)

    def rebuild_second_block_staircases_from_scenes(self):
        if not self.create_second_block_staircases():
            return False

        staircases_by_state = {
            "Sitting": [self.staircase_sitting_second_rep_1, self.staircase_sitting_second_rep_2],
            "Sleeping": [self.staircase_sleeping_second_rep_1, self.staircase_sleeping_second_rep_2],
        }

        for round_data in self.phase_second_block["Rounds"]:
            staircases = staircases_by_state[round_data["State"]]
            staircase_index = 0
            for scene in round_data["Scenes"]:
                response = self.response_from_scene(scene)
                if response is None:
                    continue
                while staircase_index < len(staircases) and staircases[staircase_index].is_finished():
                    staircase_index += 1
                if staircase_index >= len(staircases):
                    raise RuntimeError("Second Block contains more completed scenes than its staircases.")
                staircases[staircase_index].update(response)
        return True

    def rollback_active_block_page(self):
        del self.active_sequence["Scenes"][self.table_scene_offset:]
        self.active_sequence["Adaptive_Completed"] = False
        self.active_phase.save()

        if self.active_phase.phase_type == "First_Block":
            self.rebuild_first_block_staircases_from_scenes()
        else:
            self.rebuild_second_block_staircases_from_scenes()

        self.active_staircase = None
        self.current_scene_idx = None
        self.set_sequence()

    async def run_sequence_task(self):
        pause_duration = self.settings["sequence_pause_duration"]
        try:
            if self.active_phase.phase_type == "First_Block":
                await self.run_first_block_sequence_loop()
            elif self.active_phase.phase_type == "Second_Block":
                await self.run_second_block_sequence_loop()
            else:
                scenes, cur_next_scenes = await self.prepare_sequence_run()
                if scenes:
                    await self.run_scene_loop(scenes, cur_next_scenes)
        finally:
            await self.cleanup_after_sequence(pause_duration)

    def create_first_block_scene(self, staircase):
        return create_scene(
            direct_factor=staircase.direct_factor,
            type=AdaptiveStaircase.get_type_from_direct_factor(staircase.direct_factor),
            E=staircase.current_value,
            disturbed=None,
            reaction_time=None,
        )

    def create_second_block_scene(self, staircase):
        direct_factor = staircase.current_value
        return create_scene(
            direct_factor=direct_factor,
            type=AdaptiveStaircase.get_type_from_direct_factor(direct_factor),
            E=staircase.illuminance,
            disturbed=None,
            reaction_time=None,
        )

    def calculate_light_components(self, E, direct_factor):
        E_direct = E * direct_factor
        E_diffuse = E * (1 - direct_factor)
        return E_direct, E_diffuse

    def update_active_block_scene_row(self, scene):
        table_row_idx = self.current_scene_idx - self.table_scene_offset
        row_values = [
            self.current_scene_idx + 1,
            scene.get("Type"),
            str(scene.get("Direct_Factor")),
            scene.get("E"),
            scene.get("E_monitor"),
            scene.get("Disturbed"),
            scene.get("Reaction Time"),
        ]
        self.sequence_table.update_row(row_values, table_row_idx)
        self.set_sequence_scene_label()

    async def run_first_block_sequence_loop(self):
        self.check_sequence_setup()
        self.set_reading_light(self.state_position_status == "Sitting")
        self.set_roomlight_level(0)

        scenes = self.active_sequence["Scenes"]
        self.table_scene_offset = len(scenes)
        scene_limit = self.settings["max_scene_before_sequence_pause"]
        scenes_run = 0

        staircases = self.get_active_first_block_staircases()
        staircase = self.select_random_staircase(staircases)

        if staircase is None:
            self.complete_active_first_block_round()
            return

        scene = self.create_first_block_scene(staircase)
        scenes.append(scene)
        self.active_staircase = staircase
        self.current_scene_idx = len(scenes) - 1
        self.update_active_block_scene_row(scene)
        self.set_scene(scene)

        await self.run_initial_isi()

        while scenes_run < scene_limit:
            await self.run_single_scene(scene)
            self.set_scene_reaction(disturbing=False)
            self.active_scene = None
            self.active_staircase = None
            self.sequence_table.deselect_row()
            scenes_run += 1

            if scenes_run >= scene_limit:
                break

            staircases = self.get_active_first_block_staircases()
            staircase = self.select_random_staircase(staircases)

            if staircase is None:
                self.complete_active_first_block_round()
                break

            scene = self.create_first_block_scene(staircase)
            scenes.append(scene)
            self.active_staircase = staircase
            self.current_scene_idx = len(scenes) - 1
            self.update_active_block_scene_row(scene)

            await self.await_first_block_interstimulus_interval(scene)

        if self.select_random_staircase(self.get_active_first_block_staircases()) is None:
            self.complete_active_first_block_round()

    async def run_second_block_sequence_loop(self):
        self.check_sequence_setup()
        self.set_reading_light(self.state_position_status == "Sitting")
        self.set_roomlight_level(0)

        scenes = self.active_sequence["Scenes"]
        self.table_scene_offset = len(scenes)
        scene_limit = self.settings["max_scene_before_sequence_pause"]
        scenes_run = 0

        staircase = self.get_active_second_block_staircase()

        if staircase is None:
            self.complete_active_second_block_round()
            return

        scene = self.create_second_block_scene(staircase)
        scenes.append(scene)
        self.active_staircase = staircase
        self.current_scene_idx = len(scenes) - 1
        self.update_active_block_scene_row(scene)
        self.set_scene(scene)

        await self.run_initial_isi()

        while scenes_run < scene_limit:
            await self.run_single_scene(scene)
            self.set_scene_reaction(disturbing=False)
            self.active_scene = None
            self.active_staircase = None
            self.sequence_table.deselect_row()
            scenes_run += 1

            if scenes_run >= scene_limit:
                break

            staircase = self.get_active_second_block_staircase()

            if staircase is None:
                self.complete_active_second_block_round()
                break

            scene = self.create_second_block_scene(staircase)
            scenes.append(scene)
            self.active_staircase = staircase
            self.current_scene_idx = len(scenes) - 1
            self.update_active_block_scene_row(scene)

            await self.await_first_block_interstimulus_interval(scene)

        if self.active_second_block_round_completed():
            self.complete_active_second_block_round()

    async def await_first_block_interstimulus_interval(self, next_scene):
        isi_duration = self.settings["inter-stimulus-interval"]
        isi_fade_duration = self.settings["isi_fade_duration"]
        while True:
            self.activate_isi()
            await self.await_countdown_timer(start_time=isi_duration,
                                             end_time=isi_fade_duration,
                                             stop_event=self.sequence_stop_event,
                                             label="ISI")
            if self.sequence_stop_event.is_set():
                await self.wait_for_sequence_continue()
                continue

            self.set_scene(next_scene)
            self.fade_isi()
            await self.await_countdown_timer(stop_event=self.sequence_stop_event, label="ISI")
            if not self.sequence_stop_event.is_set():
                return
            await self.wait_for_sequence_continue()

    async def prepare_sequence_run(self):
        self.check_sequence_setup()
        scenes = self.active_sequence["Scenes"]
        if not scenes:
            return [], []
        if self.current_scene_idx is None:
            self.current_scene_idx = 0

        self.set_scene(scenes[self.current_scene_idx])
        self.sequence_table.select_row(self.current_scene_idx)
        cur_next_scenes = [cur_next for cur_next in pairwise([*scenes,None])]

        self.set_reading_light(self.state_position_status == "Sitting")
        self.set_roomlight_level(0)
        await self.run_initial_isi()
        return scenes, cur_next_scenes

    def check_sequence_setup(self):
        current_round = (self.active_phase.phase_type, self.active_sequence["ID"])
        if self.position_checked_round != current_round:
            print("State Position Status: ", self.state_position_status)
            print("Active Sequence State: ", self.active_sequence["State"])
            self.state_position_status = self.active_sequence["State"]
            self.position_checked_round = current_round
            self.open_check_window(state=self.state_position_status)

    async def run_initial_isi(self):
        isi_duration = self.settings["inter-stimulus-interval"]
        isi_fade_duration = self.settings["isi_fade_duration"]
        while True:
            self.activate_isi()
            await self.await_countdown_timer(start_time=isi_duration * 2,
                                             end_time=isi_fade_duration,
                                             stop_event=self.sequence_stop_event,
                                             label="ISI")
            if self.sequence_stop_event.is_set():
                await self.wait_for_sequence_continue()
                continue

            self.fade_isi()
            await self.await_countdown_timer(stop_event=self.sequence_stop_event, label="ISI")
            if not self.sequence_stop_event.is_set():
                return
            await self.wait_for_sequence_continue()

    async def run_scene_loop(self, scenes, cur_next_scenes):
        while self.current_scene_idx < len(scenes):
            scene,next_scene = cur_next_scenes[self.current_scene_idx]
            await self.run_single_scene(scene)
            await self.run_interstimulus_interval(next_scene)

            self.set_scene_reaction(disturbing=False)
            self.sequence_table.deselect_row()
            self.current_scene_idx += 1

    async def run_single_scene(self, scene):
        scene_duration = self.settings["scene_duration"]
        scene_fade_duration = self.settings["scene_fade_duration"]
        table_row_idx = self.current_scene_idx - self.table_scene_offset
        self.sequence_table.select_row(table_row_idx)
        self.set_sequence_scene_label()
        while True:
            self.activate_scene()
            self.active_scene = scene
            self.scene_disturbing.clear()
            self.scene_start_timestamp = timer()
            await self.await_countdown_timer(start_time=scene_duration,
                                             end_time=scene_fade_duration,
                                             stop_event=self.sequence_stop_event,
                                             label="Scene")
            if self.sequence_stop_event.is_set():
                self.fade_scene()
                await self.wait_for_sequence_continue()
                continue

            self.set_scene_monitor()
            self.fade_scene()
            await self.await_countdown_timer(stop_event=self.sequence_stop_event, label="Scene")
            if not self.sequence_stop_event.is_set():
                self.activate_isi()
                return
            await self.wait_for_sequence_continue()

    async def run_interstimulus_interval(self, next_scene):
        isi_duration = self.settings["inter-stimulus-interval"]
        isi_fade_duration = self.settings["isi_fade_duration"]
        while True:
            self.activate_isi()
            await self.await_countdown_timer(start_time=isi_duration,
                                             end_time=isi_fade_duration,
                                             stop_event=self.sequence_stop_event,
                                             label="ISI")
            if self.sequence_stop_event.is_set():
                await self.wait_for_sequence_continue()
                continue

            if next_scene is not None:
                self.set_scene(next_scene)
            self.fade_isi()
            await self.await_countdown_timer(stop_event=self.sequence_stop_event, label="ISI")
            if not self.sequence_stop_event.is_set():
                return
            await self.wait_for_sequence_continue()

    async def wait_for_sequence_continue(self):
        await self.sequence_continue_event.wait()
        self.sequence_continue_event.clear()
        self.sequence_stop_event.clear()

    async def cleanup_after_sequence(self, pause_duration):
        self.set_roomlight_level(1)
        self.reading_light_intensity.set_values([0]) #turn off reading light during pause
        self.sequence_table.deselect_row()
        self.sequence_stop_event.clear()
        self.sequence_start_reset_button.configure(text="Start Sequence", command=self.run_sequence)
        self.sequence_stop_continue_button.configure(text="Pause Sequence", command=self.stop_sequence,
                                                    state="disabled", fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"])
        self.load_participant_button.configure(state="normal")
        self.roomlight_button.configure(state="normal")

        self.countdown_timer_var.set(0)
        self.active_scene = None
        self.current_scene_idx = None
        if self.active_block_reset_requested:
            self.rollback_active_block_page()
            self.active_block_reset_requested = False
        self.set_sequence_scene_label()
        if self.active_phase.phase_type in ("First_Block", "Second_Block"):
            can_start = (
                not self.active_sequence.get("Adaptive_Completed", False)
                and self.table_scene_offset <= len(self.active_sequence["Scenes"]) < self.table_scene_offset + self.settings["max_scene_before_sequence_pause"]
            )
            self.sequence_start_reset_button.configure(state="normal" if can_start else "disabled")
        self.update_phase_buttons_after_sequence()

        show_mid_break_reminder = (
            self.active_phase.phase_type == "First_Block"
            and self.active_phase.check_completion()
            and not self.mid_break_reminder_shown
        )

        await self.await_countdown_timer(start_time=pause_duration,
                                         stop_event=self.pause_stop_event,
                                         label="Pause")
        self.pause_stop_event.clear()
        if show_mid_break_reminder:
            self.mid_break_reminder_shown = True
            ReminderWindow(self, "Break", "Give 3 minutes break!")

    def update_phase_buttons_after_sequence(self):
        if self.phase_learning_block is not None and self.phase_learning_block.check_completion() == True:
            self.learning_block_button.turn_on()
            if self.phase_first_block is not None:
                self.first_block_button.enable()
        if self.phase_first_block is not None and self.phase_first_block.check_completion() == True:
            self.first_block_button.turn_on()
        if self.phase_second_block is not None and self.phase_second_block.check_completion() == True:
            self.second_block_button.turn_on()
        for button in [self.learning_block_button, self.first_block_button, self.second_block_button]:
            if button.selected:
                button.enable_children()

    @async_handler
    async def run_sequence(self):
        if self.timer_running: # pause timer running
            return
        self.sequence_task = asyncio.create_task(self.run_sequence_task(), name="run_sequence")
        # switch button to stop sequence
        self.sequence_stop_continue_button.configure(state='normal',fg_color="red")
        self.sequence_start_reset_button.configure(text="Reset Sequence", command=self.reset_sequence)
        self.load_participant_button.configure(state="disabled")
        # disable sequence change buttons
        self.learning_block_button.disable_children()
        self.first_block_button.disable_children()
        self.second_block_button.disable_children()
        for button in [self.learning_block_button, self.first_block_button, self.second_block_button]:
            if not button.selected:
                button.disable()
        
        # disable room light button
        self.roomlight_button.configure(state="disabled")
        
        await self.sequence_task

    def print_countdown_timer(self, *args):
        self.countdown_digits.configure(text="{:04.1f}".format(self.countdown_timer_var.get()))

    def toggle_freeze_qlc(self):
        self.freeze_qlc_active = not self.freeze_qlc_active
        if self.freeze_qlc_active:
            self.freeze_qlc_button.configure(text="Continue QLC", fg_color="red")
        else:
            self.freeze_qlc_button.configure(text="Freeze QLC", fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"])
    
    async def await_countdown_timer(self, start_time = None, end_time = None, stop_event = None, label=None):
        self.timer_running = True
        if label is not None:
            self.countdown_label.configure(text=label)
        if(end_time == None):
            end_time = 0
        self.scene_countdown_end = end_time
        self.scene_countdown_finished.clear()
        if(start_time != None):
            self.countdown_timer_var.set(start_time)
        self.cancel_countdown_callback()
        self.countdown_after_id = self.after(100, self.countdown_timer_cb) # starts the timer
        if stop_event is not None:
            timer_finished_task = asyncio.create_task(self.scene_countdown_finished.wait())
            stop_task = asyncio.create_task(stop_event.wait())
            _, pending_tasks = await asyncio.wait(
                [timer_finished_task, stop_task],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for pending_task in pending_tasks:
                pending_task.cancel()
            if pending_tasks:
                await asyncio.gather(*pending_tasks, return_exceptions=True)
            if stop_event.is_set():
                self.cancel_countdown_callback()
                self.countdown_timer_var.set(0) # reset to zero
                self.countdown_label.configure(text="")
                self.timer_running = False
                return
        else:
            await self.scene_countdown_finished.wait()
        self.countdown_label.configure(text="")
        self.timer_running = False
        self.countdown_timer_var.set(self.scene_countdown_end) # leave it at end_time

    def countdown_timer_cb(self):
        self.countdown_after_id = None
        if self.freeze_qlc_active:
            self.countdown_after_id = self.after(100, self.countdown_timer_cb)
            return
        timer_value = self.countdown_timer_var.get()
        timer_value -= 0.1
        if timer_value > self.scene_countdown_end:
            self.countdown_timer_var.set(round(timer_value,1))
            self.countdown_after_id = self.after(100, self.countdown_timer_cb)  # decrement countdown every 100 ms
        else:
            self.scene_countdown_finished.set()

    def cancel_countdown_callback(self):
        if self.countdown_after_id is None:
            return
        try:
            self.after_cancel(self.countdown_after_id)
        except TclError:
            pass
        self.countdown_after_id = None
    
    def set_scene_reaction(self, disturbing):
        if self.active_scene is None: # are we even running a scene?
            print("No scene running")
            return
        reaction = self.get_scene_reaction(disturbing)
        if reaction is None:
            return

        stoert, reaction_time = reaction
        self.save_scene_reaction(stoert, reaction_time)

    def get_scene_reaction(self, disturbing):
        if disturbing is True:
            if self.scene_disturbing.is_set():
                print("Already set to disturbing")
                return None
            self.scene_disturbing.set()
            reaction_timestamp = timer()
            return "Yes", round(reaction_timestamp - self.scene_start_timestamp,3)
        if self.scene_disturbing.is_set():
            return None
        return "No", ""

    def save_scene_reaction(self, stoert, reaction_time):
        self.active_scene["Disturbed"] = stoert
        self.sequence_table.update_cell(stoert, "Disturbing")
        self.active_scene["Reaction Time"] = reaction_time
        self.sequence_table.update_cell(reaction_time,"Reaction Time")
        self.update_active_staircase(stoert)
        # save current results to file and check the progress
        if self.active_phase is not None:
            self.active_phase.save()

    def update_active_staircase(self, stoert):
        if self.active_staircase is None:
            return

        response = "+" if stoert == "Yes" else "-"
        self.active_staircase.update(response)
        
    def clear_scene_reaction(self):
        if self.active_scene is not None: # are we even running a scene?
            self.active_scene["Disturbed"] = ""
            self.sequence_table.update_cell("", "Disturbing")
            self.active_scene["Reaction Time"] = ""
            self.sequence_table.update_cell("","Reaction Time")

    def load_qlc_project(self):
        r = False
        try:
            #filename = tk.filedialog.askopenfilename(filetypes=[("QLC+ files", "*.qxw"),("All files", "*.*")])
            filename = self.settings["qlc_project"]
            with open(filename, 'rb') as f:
                r = post("http://{addr}/loadProject".format(addr = self.settings["qlc_address"]), files={'qlcprj': f})
            r = True
        finally:
            return r
    
    @async_handler
    async def init_qlc(self):
        if self.load_qlc_project() == True:
            self.qlc_init_button.configure(text="QLC+ initialisiert", fg_color="green", state="disabled")
            await asyncio.sleep(0.2) # wait for project to load
            self.qlc_init_channel.set_values([255])
            await asyncio.sleep(0.2)
            self.set_all_intensities(0)
            self.set_isi()
            self.fade_isi()
            self.moving_head_ctc.set_values([237])
            self.led_bar_ctc.set_values([240])
            self.spot_color.set_values([255,255,255,255])
            self.room_light_level.set_values([255])

    def set_roomlight_level(self,lvl):
        if lvl == 2:
            # Turn on the bright ceiling light
            self.room_light_level.set_values([255])

            # Set button color to green
            self.roomlight_button.configure(fg_color="green",hover_color="green",command=lambda:self.set_roomlight_level(1))
            self.roomlight_button.hover = False
        else:
            self.roomlight_button.configure(fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"],
                                            hover_color=ctk.ThemeManager.theme["CTkButton"]["hover_color"],
                                            command=lambda:self.set_roomlight_level(2))
            self.roomlight_button.hover = True
            if lvl == 1:
                # Turn on the dim ceiling light
                self.room_light_level.set_values([127])
            if lvl == 0:
                # Turn off the ceiling light
                self.room_light_level.set_values([0])

    def set_reading_light(self,state):
        if state == True:
            self.reading_light_intensity.set_values([self.settings["DMX_brightness_reading"]])
        else:
            self.reading_light_intensity.set_values([0])

    @async_handler
    async def create_artnet_interface(self):
        self.qlc_node = pan.ArtNetNode('127.0.0.1', 6454)
        self.qlc_input = self.qlc_node.add_universe(10)

        self.spot1_intensity    = self.qlc_input.add_channel(start=1, width=2) # Direct spot 1
        self.diffuse_intensity  = self.qlc_input.add_channel(start=3, width=2) # Diffuse spot
        self.led_bar_ctc        = self.qlc_input.add_channel(start=5, width=1) # LED bar CTC
        self.isi_intensity      = self.qlc_input.add_channel(start=9, width=2) # Master ISI intensity
        self.spot_color         = self.qlc_input.add_channel(start=11, width=4) # R,G,B,L
        self.isi_color          = self.qlc_input.add_channel(start=15, width=4) # R,G,B,L
        self.moving_head_ctc    = self.qlc_input.add_channel(start=19, width=1) # CTC
        self.isi_ctc            = self.qlc_input.add_channel(start=20, width=1) # CTC
        self.qlc_init_channel   = self.qlc_input.add_channel(start=21, width=1) # Init-Button
        self.sequence_control   = self.qlc_input.add_channel(start=22, width=1) # Control the Sequence of Szene and ISI
        self.pixel2_7_intensity = self.qlc_input.add_channel(start=23, width=1) # Pixel 2-7 intensity
        self.reading_light_intensity = self.qlc_input.add_channel(start=24, width=1) # Reading light intensity
        self.room_light_level   = self.qlc_input.add_channel(start=25, width=1) # Room light

    def activate_isi(self):
        self.set_sequence_control("isi")
    
    def fade_isi(self):
        self.set_sequence_control("fade_isi")
    
    def activate_scene(self):
        self.set_sequence_control("scene")
    
    def fade_scene(self):
        self.set_sequence_control("fade_scene")

    def set_sequence_control(self, state):
        self.sequence_control.set_values([self.SEQUENCE_CONTROL_VALUES[state]])
    
    def set_scene(self, scene):
        self.set_all_intensities(0)
        self.pixel2_7_intensity.set_values([0])
        E = scene["E"]
        direct_factor = scene["Direct_Factor"]
        E_direct, E_diffuse = self.calculate_light_components(E, direct_factor)

        spot1_dmx = 0
        diffuse_dmx = 0
        pixel2_7_dmx = 0

        if E_direct > 0:
            direct_center_pixel_dmx, direct_pixel2_7_dmx = self.calculate_spot_dmx(E_direct)
            spot1_dmx = direct_center_pixel_dmx
            pixel2_7_dmx = max(pixel2_7_dmx, direct_pixel2_7_dmx)

        if E_diffuse > 0:
            diffuse_dmx = self.calculate_diffus_dmx(E_diffuse)

        spot1_dmx = min(spot1_dmx, 2**16 - 1)
        diffuse_dmx = min(diffuse_dmx, 2**16 - 1)
        pixel2_7_dmx = min(pixel2_7_dmx, 2**8 - 1)
        self.spot1_intensity.set_values(spot1_dmx.to_bytes(2,'big'))
        self.diffuse_intensity.set_values(diffuse_dmx.to_bytes(2,'big'))
        self.pixel2_7_intensity.set_values([pixel2_7_dmx])

    def set_diffus_scene(self, E):
        intensity = self.calculate_diffus_dmx(E)
        self.diffuse_intensity.set_values(intensity.to_bytes(2,'big'))

    def calculate_diffus_dmx(self, E):
        maxE = self.settings["maxE_diffus"]
        E = max(0, min(E, maxE))
        return self.calculate_quadratic_dmx(E, self.settings["diffuse_curve"], 0, 2**16 - 1)

    def calculate_spot_dmx(self, E):
        dmx8_max = 2**8 - 1
        dmx16_max = 2**16 - 1
        maxE = self.settings["maxE_spot1"] * self.settings["maxAussteuerung_faktor_pixel1"]
        linear_limit = 101

        E = max(0, E)

        if E > maxE:
            center_pixel_dmx = dmx16_max
            required_multiplier = E / maxE
            if required_multiplier <= 1:
                other_pixel_dmx = 0
            else:
                other_pixel_dmx = self.calculate_quadratic_dmx(required_multiplier, self.settings["pixel2_7_multiplier_curve"], 0, dmx8_max)
        elif E <= linear_limit:
            center_pixel_dmx = round((E / maxE) * dmx16_max)
            other_pixel_dmx = 0
        else:
            center_pixel_dmx = self.calculate_quadratic_dmx(E, self.settings["direct_center_curve"], 0, dmx16_max)
            other_pixel_dmx = 0
        return center_pixel_dmx, other_pixel_dmx

    def calculate_quadratic_dmx(self, target, curve, dmx_min, dmx_max):
        a, b, c = curve
        discriminant = b**2 - 4 * a * (c - target)
        if discriminant < 0:
            return dmx_min

        sqrt_discriminant = np.sqrt(discriminant)
        roots = [
            (-b + sqrt_discriminant) / (2 * a),
            (-b - sqrt_discriminant) / (2 * a),
        ]
        valid_roots = [root for root in roots if dmx_min <= root <= dmx_max]
        if valid_roots:
            return round(valid_roots[0])

        closest_root = min(roots, key=lambda root: abs(root - min(max(root, dmx_min), dmx_max)))
        return round(min(max(closest_root, dmx_min), dmx_max))
        
    def set_all_intensities(self,i):
        self.spot1_intensity.set_values(i.to_bytes(2,'big'))
        self.diffuse_intensity.set_values(i.to_bytes(2,'big'))

    def set_isi(self):
        brightness = 5700
        self.isi_intensity.set_values(brightness.to_bytes(2,'big'))
        self.isi_color.set_values([255,0,0,0])
        self.pixel2_7_intensity.set_values([0])

app = App()
app.async_mainloop()
