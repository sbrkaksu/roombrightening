# Data parsing, formatting and file handling
from ast import literal_eval #dict type security for subject file reading
import os
from os.path import splitext, exists #used for saving result files with correct naming and preventing overwriting 
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
from tkinter import filedialog, font, DoubleVar #used for file dialogs, font configuration
from CTkTable import CTkTable #custom table widget for displaying the scenes and their parameters
from async_tkinter_loop import async_handler #decorator to allow async functions to be used as event handlers in Tkinter
from async_tkinter_loop.mixins import AsyncCTk #mixin to allow the main application class to run asynchronous tasks

# QLC+ and lighting control, communication
from requests import post #communication with QLC+ via HTTP API
import pyartnet as pan #used for controlling the lighting via Art-Net protocol
import serial #used for communication with the measurement monitor via serial port

# Generates fine-grid block
from Stage_ProbandGenerator import FormatPrinter, scene as create_scene
from trial import AdaptiveStaircase

#loops through all children of a widget and its children in GUI
def all_children(wid, finList=None):
    finList = finList or []
    children = wid.winfo_children()
    for item in children:
        finList.append(item)
        all_children(item, finList)
    return finList


#4 digits after the decimal point for E values when saving files
printer = FormatPrinter({float: "{:.4e}"},sort_dicts=False)

superscript_map = { "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴", "5": "⁵",
                   "6": "⁶","7": "⁷", "8": "⁸", "9": "⁹","+": "⁺","-": "⁻"}

superscript_trans = str.maketrans(''.join(superscript_map.keys()),''.join(superscript_map.values()))

#formats float in scientific notation with superscript exponent, e.g. 1.23e+04 -> 1.23 ⋅10⁺⁴ 
def pprint_scientific(f):
    b,e = np.format_float_scientific(f, precision=2, min_digits=2, exp_digits=1).split('e', 1)
    return "{} ⋅10{}".format(b, e.translate(superscript_trans)) 

#formatting E values in the table with above formatter
table_printer = FormatPrinter({float: pprint_scientific, str: "{}"} ) 

#Creates a clickable table with header and specified number of rows
class ClickableTable(ctk.CTkFrame):
    def __init__(self, *args, header_labels, row_num, callback = None, **kwargs):
        super().__init__(*args, **kwargs,fg_color="transparent")

        self.row_num = row_num
        self.col_num = len(header_labels)
        self.selected_row = None
        self.column_widths = [max(85, len(label) * 8 + 20) for label in header_labels]
        
        #table header
        self.table_header = CTkTable(self, row=1, column=self.col_num, header_color='white', corner_radius=0, height=10, width=85)
        self.table_header.grid(row=0, column=0, padx=5, pady=1, sticky="n")
        self.table_header.update_values([header_labels])
        self.header_dict = dict(zip(header_labels, range(len(header_labels))))

        #table body
        self.table = CTkTable(self, row=self.row_num, column=self.col_num, corner_radius=0, height=10, width=85 ,hover_color= "#92d5e0")
        self.table.grid(row=1, column=0, padx=10, pady=(0,10), sticky="n")
        self.apply_column_widths()
        
        if callback is not None:
            self.set_callback(callback)

    def apply_column_widths(self):
        for col, width in enumerate(self.column_widths):
            self.table_header.frame[0, col].configure(width=width, require_redraw=True)
            for row in range(self.table.rows):
                self.table.frame[row, col].configure(width=width, require_redraw=True)
        
    def set_callback(self, callback):
        for i in range(self.table.rows):
            self.table.edit_row(row=i, command = lambda i=i: callback(i))

    def deselect_row(self):
        if self.selected_row is not None:
            self.table.deselect_row(self.selected_row)

    def select_row(self, row_idx):
        self.deselect_row()
        self.selected_row = row_idx
        self.table.select_row(self.selected_row)

    def update_table(self, values):
        #for button in self.table.frame.values():
            #button.configure(text=" ")
        for i in range(self.table.rows):
            for j in range(self.table.columns):
                try:
                    value = values[i][j]
                    if value == None: value = " "
                except IndexError: value = " "
                self.table.frame[i,j].configure(text=str(table_printer.pformat(value)),require_redraw=True)

        #self.table.update_data()
        
    def update_cell(self,value, col, row_idx=None):
        if row_idx is None:
            row_idx = self.selected_row
        if isinstance(col, str):
            col = self.header_dict[col]
        self.table.insert(row_idx, col, str(table_printer.pformat(value)))

    def update_row(self, values, row_idx):
        for col, value in enumerate(values):
            if value is None:
                value = " "
            self.table.frame[row_idx, col].configure(text=str(table_printer.pformat(value)), require_redraw=True)

 # Creates a pop-up window with a confirm button       
class CheckWindow(ctk.CTkToplevel):
    def __init__(self, parent, title, label, *args, **kwargs):
        super().__init__(parent,*args, **kwargs)
        super().transient(parent) # always on top of parent window
        super().grab_set() # block parent window
        
        self.geometry("300x200")
        self.title(title)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.confirm_button = ctk.CTkButton(self, text=label, command=self.destroy)
        self.confirm_button.grid(row=0, column=0, padx=20, pady=30, sticky="nsew")

# Creates a pop-up window with multiple dropdowns    
class CheckWindowDropDown(ctk.CTkToplevel):
    def __init__(self, parent, title, options_dictlist, callback, *args, **kwargs):
        super().__init__(parent,*args, **kwargs)
        super().transient(parent) # always on top of parent window
        super().grab_set() # block parent window
        self.options_dictlist = options_dictlist
        self.geometry("400x800")
        self.title(title)
        self.dropdowns = []
        for i,d in enumerate(self.options_dictlist):
            # pop the title of the dropDown
            title = d["Title"]
            options = d["Options"]
            ctk.CTkLabel(self, text=title).grid(row=i*2, column=0, padx=10, pady=5, sticky="nw")
            dropdown = ctk.CTkOptionMenu(self, values=options)
            dropdown.grid(row=(i*2) + 1, column=0, padx=20, pady=(0,5), sticky="nw")
            d["Dropdown"] = dropdown
            
        self.confirm_button = ctk.CTkButton(self, text="Confirm", state="normal",
                                            command=self.call_callback_and_selfdestruct)
        self.confirm_button.grid(row=(i+1)*2, column=0, padx=10, pady=30, sticky="nsew")
        self.callback = callback
    
    def check_set_options(self,val):
        # check if all dropdowns have a value set
        selected_options = [d["Dropdown"].get() for d in self.options_dictlist]
        if '' in selected_options or None in selected_options:
            return
        self.confirm_button.configure(state="normal")
    
    def call_callback_and_selfdestruct(self):
        # call the callback function with the selected options
        selected_options = {d["Title"]: d["Dropdown"].get() for d in self.options_dictlist}
        self.callback(selected_options)
        self.destroy()

# Switch button class that can be toggled on and off, and can be part of a group where only one button can be selected at a time. 
class SwitchButton(ctk.CTkButton):
# the three transparent buttons on the left
    button_groups = {}
    
    def __init__(self , *args, on_color, group=None, command=None, **kwargs):
        super().__init__(*args, command=self.on_click, hover=False, **kwargs)

        self.on_color = on_color
        self.off_color = super().cget("fg_color")
        self.border_color = super().cget("border_color")
        self.border_width = super().cget("border_width")
        self.selected = False
        self.command = command
        self.group = group
        self.on_enter_id = None
        self.on_leave_id = None

        if group is not None:
            SwitchButton.button_groups.setdefault(group, []).append(self)
            
        if super().cget("state") == "disabled": # to be able to call disable()
            self.enabled = True
            self.disable()
        else: # to be able to call enable()
            self.enabled = False
            self.enable() # check later
        # create label
        
    def on_enter(self, event): #mouse on
        super().configure(border_color="white")
        

    def on_leave(self, event):#mouse off
        super().configure(border_color=self.border_color)

    def add_enter_leave_interaction(self): # binds events for mouse enter and leave 
        if self.on_enter_id is None and self.on_leave_id is None:
            self.on_enter_id = super().bind("<Enter>", self.on_enter, add='+')
            self.on_leave_id = super().bind("<Leave>", self.on_leave, add='+')
            

    def remove_enter_leave_interaction(self): #unbinds events for mouse enter and leave
        super().unbind("<Enter>")
        super().unbind("<Leave>")
        self.on_enter_id, self.on_leave_id = None, None

    def on_click(self):
        if self.selected == False:
            self.select()
            if self.group is not None: # go through all buttons in the group and deselect them
                [sb.deselect() for sb in SwitchButton.button_groups[self.group] if sb is not self]
            if self.command is not None:
                self.command()

    def turn_on(self): #is activated when the phase is completed, fg_color = green
        super().configure(fg_color=self.on_color)

    def enable(self): #makes the button clickable
        if self.enabled == False:
            super().configure(state="normal")
            super().configure(border_color=self.border_color)
            self.add_enter_leave_interaction()
            self.enabled = True

    def enable_children(self):
        if self.enabled == True:
            for child in all_children(self):
                if isinstance(child, ctk.CTkButton):
                    child.configure(state="normal")

# called first when the GUI starts
    def disable(self):#makes the button unclickable 
        if self.enabled == True:
            super().configure(state="disabled", border_color="gray")
            self.remove_enter_leave_interaction()
            self.enabled = False
            self.disable_children()

    def disable_children(self):
        for child in all_children(self):
            if isinstance(child, ctk.CTkButton):
                child.configure(state="disabled")

    def select(self):
        if self.enabled == True and self.selected == False:
            self.selected = True
            self.remove_enter_leave_interaction()
            super().configure(border_color="white", border_width=self.border_width*2)
            self.enable_children()

    def deselect(self):
        if self.enabled == True and self.selected == True:
            self.selected = False
            self.add_enter_leave_interaction()
            super().configure(border_color=self.border_color, border_width=self.border_width)
            self.disable_children()
            
    def set_command(self, command):
        self.command = command

# Class representing a phase of the experiment
class Phase(dict):
    def __init__(self,proband_file, *args, **kwargs):
        __slots__ = ()
        self.filename = proband_file
        with open(self.filename, 'r') as f:
            s = f.read()
            super().__init__(literal_eval(s))
        self.phase_type = self["Phase"]
        self.seq_num = len(self["Durchgange"])
        self.seq_idx = 0
        self.complete = False
    
    def get_current_sequence(self):
        return self["Durchgange"][self.seq_idx]
    
    def next_sequence(self):
        self.seq_idx += 1
        if self.seq_idx >= self.seq_num:
            self.seq_idx -= self.seq_num

    def prev_sequence(self):
        self.seq_idx -= 1
        if self.seq_idx < 0:
            self.seq_idx += self.seq_num
    
    def check_completion(self):
        if self.phase_type == "E_Block":
            completed = [durchgang.get("Adaptive_Completed") for durchgang in self["Durchgange"]]
            return bool(completed) and None not in completed and False not in completed

        reactions = [sz.get("Disturbed") for s in self["Durchgange"] for sz in s["Scenes"]]
        return bool(reactions) and None not in reactions
        
        
    def save(self):
        filename_base = splitext(self.filename)[0]
        fname = self.filename
        with open(fname, 'w') as f:
            f.write(printer.pformat(self))

        if self.phase_type == "Learning Block":
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
    ROOMLIGHT_OFF = 0
    ROOMLIGHT_DIM = 1
    ROOMLIGHT_BRIGHT = 2

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
        self.title("Study Room Brightening")
        self.geometry("1190x750") 
        self.resizable(False, False)
        self.style = ctk.set_appearance_mode("light") #force to work in light mode

    def setup_settings(self):
        self.settings = {
            "qlc_address":              'localhost:9999',
            "qlc_project":              'Stage_VersuchsraumLeo.qxw',
            "monitor_serial_port":      'COM3',
            "monitor_baud_rate":        9600,
            "monitor_E_factor_spot_1":  2.41e7,
            "monitor_E_factor_diffus":  1.26e7,
            "scene_duration":           1.5, #4.5, # seconds
            "scene_fade_duration":      0.2, # seconds QLC fades in 100 ms
            "inter-stimulus-interval":  0.5, #2.5, #seconds
            "isi_fade_duration" :       0.5, # seconds. QLC fades in 300 ms
            "sequence_pause_duration":  5.0, # 45 seconds
            "maxE_spot1": 168.9,
            "maxE_diffus": 610,
            "maxAussteuerung_faktor_pixel1": 0.7,
            "DMX_brightness_reading": 255,
            "DMX_brightness_roomlight": 255,
            "learn_proband_file": "ProbandLernenB.txt",
            "adaptive_batch_scene_limit": 16,
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

        self.phase_learning_block = None
        self.phase_e_block = None
        self.phase_combination_block = None

        self.staircase_direct_evening = None
        self.staircase_diffuse_evening = None
        self.staircase_direct_night = None
        self.staircase_diffuse_night = None

        self.sequence_stop_event = asyncio.Event()
        self.sequence_continue_event = asyncio.Event()
        self.pause_stop_event = asyncio.Event()
        self.scene_disturbing = asyncio.Event()

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
        sequence_buttons_settings = {"height":25, "border_width":1, "text_color":"black", "border_color":"black",
                                        "fg_color":"transparent", "hover_color":"light blue"}

        self.load_proband_button = ctk.CTkButton(self.seq_crtl_frame, text="Load subject phase", command=self.load_proband)
        self.load_proband_button.grid(row=0, column=0, padx=10, pady=10, sticky="n")

        self.learning_block_button = SwitchButton(self.seq_crtl_frame, group="phase", on_color="green", text="Learning Block", **phase_buttons_settings, command=self.load_learning_block, state="disabled")
        self.learning_block_button.grid(row=1, column=0, padx=10, pady=10, sticky="n")

        self.e_block_button = SwitchButton(self.seq_crtl_frame, group="phase", on_color="green", text="E Block", **phase_buttons_settings, command=self.select_e_block, state="disabled")
        self.e_block_button.grid(row=2, column=0, padx=10, pady=10, sticky="n")
        self.add_sequence_nav_buttons(self.e_block_button, "e_block", sequence_buttons_settings)

        self.combination_block_button = SwitchButton(self.seq_crtl_frame, group="phase", on_color="green", text="Combination Block", **phase_buttons_settings, command=lambda:self.set_phase(self.phase_combination_block), state="disabled")
        self.combination_block_button.grid(row=3, column=0, padx=10, pady=10, sticky="n")
        self.add_sequence_nav_buttons(self.combination_block_button, "combination_block", sequence_buttons_settings)

        self.sequence_start_reset_button = ctk.CTkButton(self.seq_crtl_frame, text="Start Durchgang", command=self.run_sequence, state="disabled")
        self.sequence_start_reset_button.grid(row=4, column=0, padx=10, pady=10, sticky="n")

        self.sequence_stop_continue_button = ctk.CTkButton(self.seq_crtl_frame, text="Pause Durchgang", command=self.stop_sequence, state="disabled")
        self.sequence_stop_continue_button.grid(row=5, column=0, padx=10, pady=10, sticky="n")

    def add_sequence_nav_buttons(self, parent, prefix, settings):
        next_button = ctk.CTkButton(parent, **settings, width=30, text=">", command=self.set_next_sequence, state="disabled")
        prev_button = ctk.CTkButton(parent, **settings, width=30, text="<", command=self.set_prev_sequence, state="disabled")
        next_button.place(relx=0.7, rely=0.6, anchor="center")
        prev_button.place(relx=0.3, rely=0.6, anchor="center")
        setattr(self, f"{prefix}_next_seq_button", next_button)
        setattr(self, f"{prefix}_prev_seq_button", prev_button)

    def setup_table(self):
        self.table_frame = ctk.CTkFrame(self,fg_color="transparent")
        self.table_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nw")
        self.proband_label = ctk.CTkLabel(self.table_frame, text="Proband", anchor="w", font=(font.nametofont("TkDefaultFont"), 18))
        self.proband_label.grid(row=0, column=0, padx=10, pady=(10,0),sticky='w')
        self.sequence_scene_label = ctk.CTkLabel(self.table_frame, text="Durchgang", anchor="w", font=(font.nametofont("TkDefaultFont"), 18))
        self.sequence_scene_label.grid(row=1, column=0, padx=10, pady=0, sticky='w')

        self.sequence_table = ClickableTable(self.table_frame, header_labels=["Scenes", "Combination Factor", "Type", "E", "E Monitor", "Disturbing", "Reaction Time"], row_num=25)
        self.sequence_table.grid(row=2, column=0, padx=0, pady=10, sticky="w")
        self.sequence_table.set_callback(self.row_click)

    def setup_timer(self):
        self.timer_running = False
        self.countdown_timer_var = DoubleVar()
        self.countdown_timer_var.trace_add('write', self.print_countdown_timer)
        self.scene_countdown_end = 0.0
        self.scene_countdown_finished = asyncio.Event()
        self.countdown_label  = ctk.CTkLabel(self.table_frame, text="Test", font=(font.nametofont("TkDefaultFont"), 18))
        self.countdown_label.place(relx=0.89, y=18, anchor="nw")
        self.countdown_digits = ctk.CTkLabel(self.table_frame, text="00.0", font=(font.nametofont("TkDefaultFont"), 18))
        self.countdown_digits.place(relx=0.88, y=18, anchor="ne")

    def setup_qlc_controls(self):
        self.qlc_init_button = ctk.CTkButton(self, text="QLC+ initialisieren", command=self.init_qlc)
        self.qlc_init_button.grid(row=1, column=2, padx=10, pady=10, sticky="nw")

        self.artnet_interface_helperbutton = ctk.CTkButton(self, command=self.create_artnet_interface)
        self.project_loaded = False
        self.after(100,self.artnet_interface_helperbutton.invoke) # workaround, because async does not work in __init__

    def setup_roomlight_controls(self):
        self.roomlight_button = ctk.CTkButton(self.seq_crtl_frame, text="Raumlicht", command=lambda:self.set_roomlight_level(self.ROOMLIGHT_BRIGHT))
        self.roomlight_button.grid(row=7, column=0, padx=10, pady=10, sticky="s")

    def setup_monitor_controls(self):
        self.read_monitor_button = ctk.CTkButton(self, command=self.read_monitor_continuously)
        self.after(100,self.read_monitor_button.invoke)

    def setup_input_bindings(self):
        self.bind("<F20>", lambda e: self.set_scene_reaction(disturbing=True))

    def setup_check_window_state(self):
        self.position_window = None
        self.time_position_status = None

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
            scene_type = self.active_scene.get("Type")
            factor = self.settings["monitor_E_factor_diffus"] if scene_type == "Diffuse" else self.settings["monitor_E_factor_spot_1"]
            EM = self.monitor_I * factor
            EM = f"{EM:.2e}" # format E monitor in exponential notation for the table
            print(EM)
            self.sequence_table.update_cell(EM, "E Monitor")
            self.active_scene["E_monitor"] = EM
    
    def open_check_window(self, zeit=None):
        if zeit is not None:
            title, label = {
                "Evening": ("Subject position: sitting", "Subject is sitting"),
                "Night": ("Subject position: lying down", "Subject is lying down"),
            }[zeit]
            self.position_window = self.show_check_window(self.position_window, title, label)

    def show_check_window(self, window, title, label):
        if window is None or not window.winfo_exists():
            window = CheckWindow(self,title=title,label=label)
        else:
            window.focus()
        self.wait_window(window)
        return window
    
    def row_click(self,row_idx):
        if self.sequence_task is not None: # if task exists
            if self.sequence_task.done() is False: # if Task is running
                if not self.sequence_stop_event.is_set(): # if Task not stopped
                    print("Task is not stopped")
                    return
        else: # task does not exist
            if self.active_sequence is None: # if subject not loaded
                print("Proband not loaded")
                return
        self.current_scene_idx = row_idx
        self.sequence_table.select_row(self.current_scene_idx)

    def load_proband(self):
        phase = Phase(filedialog.askopenfilename(filetypes=[("Text file", "*.txt"),("All files", "*.*")]))
        if phase.phase_type == "E_Block":
            self.phase_e_block = phase
            self.create_e_block_staircases()
            self.learning_block_button.enable()
            self.e_block_button.disable()
            self.active_phase = None
            self.active_sequence = None
            self.proband_label.configure(text="Proband {id}: E_Block loaded".format(id=self.phase_e_block["ID"]))
            self.sequence_scene_label.configure(text="Select Learning Block")
            self.sequence_table.update_table([])
            self.sequence_start_reset_button.configure(state="disabled")
        elif phase.phase_type == "Combination_Block":
            self.phase_combination_block = phase
            self.combination_block_button.enable()
            self.set_phase(self.phase_combination_block)
        else:
            print(f"Unsupported phase type: {phase.phase_type}")

    def create_e_block_staircases(self):
        self.staircase_direct_evening = AdaptiveStaircase(Phase="E_Block", time="evening", combination_factor=1)
        self.staircase_diffuse_evening = AdaptiveStaircase(Phase="E_Block", time="evening", combination_factor=0)
        self.staircase_direct_night = AdaptiveStaircase(Phase="E_Block", time="night", combination_factor=1)
        self.staircase_diffuse_night = AdaptiveStaircase(Phase="E_Block", time="night", combination_factor=0)

    def get_active_e_block_staircases(self):
        staircases = []

        if self.active_sequence["Time"] == "Evening":
            staircases = [
                self.staircase_direct_evening,
                self.staircase_diffuse_evening,
            ]

        elif self.active_sequence["Time"] == "Night":
            staircases = [
                self.staircase_direct_night,
                self.staircase_diffuse_night,
            ]

        else:
            print(f"Unsupported E Block time: {self.active_sequence['Time']}")

        return staircases

    def load_learning_block(self):
        learn_file = self.settings["learn_proband_file"]
        if not exists(learn_file):
            print(f"Learning block file not found: {learn_file}")
            return
        self.phase_learning_block = Phase(learn_file)
        self.set_phase(self.phase_learning_block)

    def select_e_block(self):
        if self.phase_e_block is None:
            return
        if self.phase_learning_block is None or self.phase_learning_block.check_completion() is not True:
            print("Complete the Learning Block before starting E Block.")
            return
        self.set_phase(self.phase_e_block)

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
        self.change_sequence(1)
    
    def set_prev_sequence(self):
        self.change_sequence(-1)

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
        self.proband_label.configure(text="Proband {id}: {phase}".format(id=self.active_phase["ID"], phase=self.active_phase["Phase"]))
    
    def set_sequence_scene_label(self):
        if self.active_sequence is None:
            return
        scenes = self.active_sequence["Scenes"]
        if self.active_phase.phase_type == "E_Block":
            progress = self.current_scene_idx - self.table_scene_offset + 1 if self.current_scene_idx is not None else 0
            scene_count = self.settings["adaptive_batch_scene_limit"]
        else:
            progress = self.current_scene_idx + 1 if self.current_scene_idx is not None else 0
            scene_count = len(scenes)
        label = "Durchgang {did}: {time}, Trial {pgr}/{num}".format(did=self.active_sequence["ID"],
                                                                                time=self.active_sequence["Time"],
                                                                                pgr=progress,
                                                                                num=scene_count)
        self.sequence_scene_label.configure(text=label)
        
    def set_sequence(self):
        self.active_sequence = self.active_phase.get_current_sequence()
        scenes = self.active_sequence["Scenes"]
        if self.active_phase.phase_type == "E_Block":
            scene_limit = self.settings["adaptive_batch_scene_limit"]
            visible_scenes = scenes[self.table_scene_offset:self.table_scene_offset + scene_limit]
            seq_values = [[self.table_scene_offset + idx + 1, s.get("Combination_Factor"), s.get("Type"), s.get("E"), s.get("E_monitor"), s.get("Disturbed"), s.get("Reaction Time")] for idx, s in enumerate(visible_scenes)]
        else:
            seq_values = [[idx + 1, s.get("Combination_Factor"), s.get("Type"), s.get("E"), s.get("E_monitor"), s.get("Disturbed"), s.get("Reaction Time")] for idx, s in enumerate(scenes)]
        self.sequence_table.update_table(seq_values)

        self.set_sequence_scene_label()
        e_block_can_start = self.active_phase.phase_type == "E_Block" and not self.active_sequence.get("Adaptive_Completed", False)
        self.sequence_start_reset_button.configure(state="normal" if scenes or e_block_can_start else "disabled")
    
    def stop_sequence(self):
        self.set_sequence_paused(True)
        self.sequence_stop_event.set()
        
    def continue_sequence(self):
        self.set_sequence_paused(False)
        self.sequence_continue_event.set()

    def set_sequence_paused(self, paused):
        if paused:
            self.sequence_stop_continue_button.configure(text="Continue Durchgang",
                                                      command=self.continue_sequence,
                                                      fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"])
            self.roomlight_button.configure(state="normal")
            self.set_roomlight_level(self.ROOMLIGHT_DIM)
        else:
            self.sequence_stop_continue_button.configure(text="Pause Durchgang", command=self.stop_sequence, fg_color="red")
            self.roomlight_button.configure(state="disabled")
            self.set_roomlight_level(self.ROOMLIGHT_OFF)
        
    def reset_sequence(self):
        self.pause_stop_event.set()
        self.sequence_task.cancel()

    async def run_sequence_task(self):
        pause_duration = self.settings["sequence_pause_duration"]
        try:
            if self.active_phase.phase_type == "E_Block":
                await self.run_e_block_sequence_loop()
            else:
                scenes, cur_next_scenes = await self.prepare_sequence_run()
                if scenes:
                    await self.run_scene_loop(scenes, cur_next_scenes)
        finally:
            await self.cleanup_after_sequence(pause_duration)

    def create_e_block_scene(self, staircase):
        return create_scene(
            combination_factor=staircase.combination_factor,
            type=staircase.type_of_illumination,
            E=staircase.current_value,
            disturbed=None,
            reaction_time=None,
        )

    def update_e_block_scene_row(self, scene):
        table_row_idx = self.current_scene_idx - self.table_scene_offset
        row_values = [
            self.current_scene_idx + 1,
            scene.get("Combination_Factor"),
            scene.get("Type"),
            scene.get("E"),
            scene.get("E_monitor"),
            scene.get("Disturbed"),
            scene.get("Reaction Time"),
        ]
        self.sequence_table.update_row(row_values, table_row_idx)
        self.set_sequence_scene_label()

    async def run_e_block_sequence_loop(self):
        self.check_sequence_setup()
        self.set_reading_light(self.time_position_status == "Evening")
        self.set_roomlight_level(self.ROOMLIGHT_OFF)
        await self.run_initial_isi()

        scenes = self.active_sequence["Scenes"]
        self.table_scene_offset = len(scenes)
        scene_limit = self.settings["adaptive_batch_scene_limit"]

        for _ in range(scene_limit):
            staircases = self.get_active_e_block_staircases()
            staircase = self.select_random_staircase(staircases)

            if staircase is None:
                self.active_sequence["Adaptive_Completed"] = True
                self.active_phase.save()
                break

            scene = self.create_e_block_scene(staircase)
            scenes.append(scene)
            self.active_staircase = staircase
            self.current_scene_idx = len(scenes) - 1
            self.update_e_block_scene_row(scene)
            self.set_scene(scene)

            await self.run_single_scene(scene)
            await self.await_e_block_interstimulus_interval()
            if self.sequence_stop_event.is_set():
                continue

            self.set_scene_reaction(disturbing=False)
            self.active_staircase = None
            self.sequence_table.deselect_row()

        if self.select_random_staircase(self.get_active_e_block_staircases()) is None:
            self.active_sequence["Adaptive_Completed"] = True
            self.active_phase.save()

    async def await_e_block_interstimulus_interval(self):
        isi_duration = self.settings["inter-stimulus-interval"]
        isi_fade_duration = self.settings["isi_fade_duration"]
        await self.await_countdown_timer(start_time=isi_duration,
                                         end_time=isi_fade_duration,
                                         stop_event=self.sequence_stop_event,
                                         label="ISI")
        if self.sequence_stop_event.is_set():
            self.active_scene = None
            await self.sequence_continue_event.wait()
            self.sequence_continue_event.clear()
            self.sequence_stop_event.clear()

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

        self.set_reading_light(self.time_position_status == "Evening")
        self.set_roomlight_level(self.ROOMLIGHT_OFF)
        await self.run_initial_isi()
        return scenes, cur_next_scenes

    def check_sequence_setup(self):
        if self.time_position_status != self.active_sequence["Time"]:
            print("Time Position Status: ", self.time_position_status)
            print("Active Sequence Time: ", self.active_sequence["Time"])
            self.time_position_status = self.active_sequence["Time"]
            self.open_check_window(zeit=self.time_position_status)

    async def run_initial_isi(self):
        isi_duration = self.settings["inter-stimulus-interval"]
        isi_fade_duration = self.settings["isi_fade_duration"]
        self.activate_isi()
        await self.await_countdown_timer(start_time=isi_duration * 2,
                                         end_time=isi_fade_duration,
                                         stop_event=self.sequence_stop_event,
                                         label="ISI")
        self.fade_isi()
        await self.await_countdown_timer(label="ISI")

    async def run_scene_loop(self, scenes, cur_next_scenes):
        while self.current_scene_idx < len(scenes):
            scene,next_scene = cur_next_scenes[self.current_scene_idx]
            await self.run_single_scene(scene)
            paused = await self.run_interstimulus_interval(cur_next_scenes)
            if paused:
                continue

            if next_scene is not None:
                self.set_scene(next_scene)
            self.fade_isi()
            await self.await_countdown_timer(stop_event=self.sequence_stop_event,label="ISI")
            if self.sequence_stop_event.is_set():
                continue

            self.set_scene_reaction(disturbing=False)
            self.sequence_table.deselect_row()
            self.current_scene_idx += 1

    async def run_single_scene(self, scene):
        scene_duration = self.settings["scene_duration"]
        scene_fade_duration = self.settings["scene_fade_duration"]
        table_row_idx = self.current_scene_idx - self.table_scene_offset
        self.sequence_table.select_row(table_row_idx)
        self.set_sequence_scene_label()
        self.activate_scene()
        self.active_scene = scene
        self.scene_disturbing.clear()
        self.scene_start_timestamp = timer()
        await self.await_countdown_timer(start_time=scene_duration,
                                         end_time=scene_fade_duration,
                                         stop_event=self.sequence_stop_event,
                                         label="Szene")
        if not self.sequence_stop_event.is_set():
            self.set_scene_monitor()
        self.fade_scene()
        await self.await_countdown_timer(label="Szene")
        self.activate_isi()

    async def run_interstimulus_interval(self, cur_next_scenes):
        isi_duration = self.settings["inter-stimulus-interval"]
        isi_fade_duration = self.settings["isi_fade_duration"]
        await self.await_countdown_timer(start_time=isi_duration,
                                         end_time=isi_fade_duration,
                                         stop_event=self.sequence_stop_event,
                                         label="ISI")
        if self.sequence_stop_event.is_set():
            await self.wait_for_sequence_continue(cur_next_scenes, isi_fade_duration)
            return True
        return False

    async def wait_for_sequence_continue(self, cur_next_scenes, isi_fade_duration):
        self.active_scene = None
        await self.sequence_continue_event.wait()
        self.sequence_continue_event.clear()
        self.sequence_stop_event.clear()
        scene,_ = cur_next_scenes[self.current_scene_idx]
        self.set_scene(scene)
        self.fade_isi()
        await asyncio.sleep(isi_fade_duration)

    async def cleanup_after_sequence(self, pause_duration):
        self.set_roomlight_level(self.ROOMLIGHT_DIM)
        self.reading_light_intensity.set_values([0]) #turn off reading light during pause
        self.sequence_table.deselect_row()
        self.sequence_stop_event.clear()
        self.sequence_start_reset_button.configure(text="Durchgang starten", command=self.run_sequence)
        self.sequence_stop_continue_button.configure(text="Durchgang anhalten", command=self.stop_sequence,
                                                    state="disabled", fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"])
        self.load_proband_button.configure(state="normal")
        self.roomlight_button.configure(state="normal")

        self.countdown_timer_var.set(0)
        self.active_scene = None
        self.current_scene_idx = None
        self.set_sequence_scene_label()
        self.update_phase_buttons_after_sequence()

        await self.await_countdown_timer(start_time=pause_duration,
                                         stop_event=self.pause_stop_event,
                                         label="Pause")
        self.pause_stop_event.clear()

    def update_phase_buttons_after_sequence(self):
        if self.phase_learning_block is not None and self.phase_learning_block.check_completion() == True:
            self.learning_block_button.turn_on()
            if self.phase_e_block is not None:
                self.e_block_button.enable()
        if self.phase_e_block is not None and self.phase_e_block.check_completion() == True:
            self.e_block_button.turn_on()
        if self.phase_combination_block is not None and self.phase_combination_block.check_completion() == True:
            self.combination_block_button.turn_on()
        for button in [self.learning_block_button, self.e_block_button, self.combination_block_button]:
            if button.selected:
                button.enable_children()

    @async_handler
    async def run_sequence(self):
        if self.timer_running: # pause timer running
            return
        self.sequence_task = asyncio.create_task(self.run_sequence_task(), name="run_sequence")
        # switch button to stop sequence
        self.sequence_stop_continue_button.configure(state='normal',fg_color="red")
        self.sequence_start_reset_button.configure(text="Durchgang zurücksetzen", command=self.reset_sequence)
        self.load_proband_button.configure(state="disabled")
        # disable sequence change buttons
        self.learning_block_button.disable_children()
        self.e_block_button.disable_children()
        self.combination_block_button.disable_children()
        for button in [self.learning_block_button, self.e_block_button, self.combination_block_button]:
            if not button.selected:
                button.disable()
        
        # disable room light button
        self.roomlight_button.configure(state="disabled")
        
        await self.sequence_task

    def print_countdown_timer(self, *args):
        self.countdown_digits.configure(text="{:04.1f}".format(self.countdown_timer_var.get()))
    
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
        self.after(100, self.countdown_timer_cb) # starts the timer
        if stop_event is not None:
            await asyncio.wait(
                [asyncio.create_task(self.scene_countdown_finished.wait()),
                asyncio.create_task(stop_event.wait())],return_when=asyncio.FIRST_COMPLETED)
            if stop_event.is_set():
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
        timer_value = self.countdown_timer_var.get()
        timer_value -= 0.1
        if timer_value > self.scene_countdown_end:
            self.countdown_timer_var.set(round(timer_value,1))
            self.after(100, self.countdown_timer_cb)  # decrement countdown every 100 ms
        else:
            self.scene_countdown_finished.set()
    
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
            self.szene_ctc.set_values([245])
            self.spot_color.set_values([255,255,255,255])
            self.room_light_level.set_values([255])

    def set_roomlight_level(self,lvl):
        if lvl == self.ROOMLIGHT_BRIGHT:
            # Turn on the bright ceiling light
            self.room_light_level.set_values([255])

            # Set button color to green
            self.roomlight_button.configure(fg_color="green",hover_color="green",command=lambda:self.set_roomlight_level(self.ROOMLIGHT_DIM))
            self.roomlight_button.hover = False
        else:
            self.roomlight_button.configure(fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"],
                                            hover_color=ctk.ThemeManager.theme["CTkButton"]["hover_color"],
                                            command=lambda:self.set_roomlight_level(self.ROOMLIGHT_BRIGHT))
            self.roomlight_button.hover = True
            if lvl == self.ROOMLIGHT_DIM:
                # Turn on the dim ceiling light
                self.room_light_level.set_values([127])
            if lvl == self.ROOMLIGHT_OFF:
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

        self.spot1_intensity    = self.qlc_input.add_channel(start=1, width=2) #  0:0
        self.isi_intensity      = self.qlc_input.add_channel(start=9, width=2) # Master ISI intensity
        self.spot_color         = self.qlc_input.add_channel(start=11, width=4) # R,G,B,L
        self.isi_color          = self.qlc_input.add_channel(start=15, width=4) # R,G,B,L
        self.szene_ctc          = self.qlc_input.add_channel(start=19, width=1) # CTC
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
        scene_type = scene["Type"]
        E = scene["E"]

        diffus = scene_type == "Diffuse"
        if diffus:
            self.set_diffus_scene(E)
            return

        center_pixel_dmx, other_pixel_dmx = self.calculate_spot_dmx(E)
        self.spot1_intensity.set_values(center_pixel_dmx.to_bytes(2,'big'))
        self.pixel2_7_intensity.set_values([other_pixel_dmx])

    def set_diffus_scene(self, E):
        dmx16_max = 2**16 - 1
        maxE = self.settings["maxE_diffus"]
        E = min(E, maxE)
        intensity = round((E / maxE) * dmx16_max)
        self.spot1_intensity.set_values(intensity.to_bytes(2,'big'))
        self.pixel2_7_intensity.set_values([255])

    def calculate_spot_dmx(self, E):
        dmx8_max = 2**8 - 1
        dmx16_max = 2**16 - 1
        maxE = self.settings["maxE_spot1"]
        E_factor = E / maxE
        one_pixel_max_factor = self.settings["maxAussteuerung_faktor_pixel1"]
        if E_factor > one_pixel_max_factor:
            center_pixel_factor = one_pixel_max_factor
            other_pixel_factor = (E_factor - center_pixel_factor) / one_pixel_max_factor / 6
        else:
            center_pixel_factor = E_factor
            other_pixel_factor = 0

        print("center_pixel_factor",center_pixel_factor)
        print("other_pixel_factor",other_pixel_factor)
        center_pixel_dmx = round(center_pixel_factor * dmx16_max)
        other_pixel_dmx = round(other_pixel_factor * dmx8_max)
        print("center_pixel_dmx",center_pixel_dmx)
        print("other_pixel_dmx",other_pixel_dmx)
        return center_pixel_dmx, other_pixel_dmx
        
    def set_all_intensities(self,i):
        self.spot1_intensity.set_values(i.to_bytes(2,'big'))

    def set_isi(self):
        brightness = 2500
        self.isi_intensity.set_values(brightness.to_bytes(2,'big'))
        self.isi_color.set_values([255,0,0,0])
        self.pixel2_7_intensity.set_values([0])

app = App()
app.async_mainloop()
