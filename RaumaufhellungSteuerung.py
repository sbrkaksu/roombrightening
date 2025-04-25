from ast import literal_eval
from requests import post
from itertools import pairwise
from timeit import default_timer as timer
from os.path import splitext, exists
import serial
import string

from re import compile

import numpy as np

from tkinter import filedialog, font, DoubleVar
import customtkinter as ctk
from CTkMenuBar import CTkTitleMenu
from CTkTable import CTkTable
from pprint import PrettyPrinter
import asyncio
from async_tkinter_loop import async_handler
from async_tkinter_loop.mixins import AsyncCTk
import async_timer
# maybe use uvloop (fast / more time-accurate event loop)

import pyartnet as pan
from ProbandGenerator import erzeuge_proband_fein

class FormatPrinter(PrettyPrinter):
    def __init__(self, formats, *args, **kwargs):
        super(FormatPrinter, self).__init__(*args, **kwargs)
        self.formats = formats

    def format(self, obj, ctx, maxlvl, lvl):
        if type(obj) in self.formats:
            fmt = self.formats[type(obj)]
            if callable(fmt):
                return fmt(obj), 1, 0
            # else assume format string
            return fmt.format(obj), 1, 0
        return PrettyPrinter.format(self, obj, ctx, maxlvl, lvl)

printer = FormatPrinter({float: "{:.4e}"},sort_dicts=False)

superscript_map = { "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴", "5": "⁵",
                   "6": "⁶","7": "⁷", "8": "⁸", "9": "⁹","+": "⁺","-": "⁻"}
superscript_trans = str.maketrans(
    ''.join(superscript_map.keys()),
    ''.join(superscript_map.values()))
def pprint_scientific(f):
    b,e = np.format_float_scientific(f, precision=2, min_digits=2, exp_digits=1).split('e', 1)
    return "{} ⋅10{}".format(b, e.translate(superscript_trans))

table_printer = FormatPrinter({float: pprint_scientific, str: "{}"} )

class ClickableTable(ctk.CTkFrame):
    def __init__(self, *args, header_labels, row_num, callback = None, **kwargs):
        super().__init__(*args, **kwargs,fg_color="transparent")
        self.row_num = row_num
        self.col_num = len(header_labels)
        self.table_header = CTkTable(self, row=1, column=self.col_num, header_color='white', corner_radius=0, height=10, width=85)
        self.table_header.grid(row=0, column=0, padx=10, pady=0, sticky="n")
        self.table_header.update_values([header_labels])
        self.header_dict = dict(zip(header_labels, range(len(header_labels))))
        self.table = CTkTable(self, row=self.row_num, column=self.col_num, corner_radius=0, height=10, width=85)
        self.table.grid(row=1, column=0, padx=10, pady=(0,10), sticky="n")
        hover_color = ctk.ThemeManager.theme["CTkButton"]["hover_color"]
        for i in range(self.table.rows):
            self.table.edit_row(row=i,hover_color = hover_color)
        
        if callback is not None:
            self.set_callback(callback)
        
        self.selected_row = None
        #self.sequence_progressbar = ctk.CTkProgressBar(self, orientation="vertical", mode = "determinate", width = 6)
        #self.sequence_progressbar.grid(row=2, column=1, padx=0, pady=(0,1), sticky="nsw")
        #self.sequence_progressbar.configure(corner_radius=0)
        # swap progressbar colors, so it "fills" from top to bottom
        #self.sequence_progressbar.configure(progress_color=ctk.ThemeManager.theme["CTkProgressBar"]["fg_color"])
        #self.sequence_progressbar.configure(fg_color=ctk.ThemeManager.theme["CTkProgressBar"]["progress_color"])
        #self.sequence_progressbar.set(1)
    
    def set_callback(self, callback):
        for i in range(self.table.rows):
                self.table.edit_row(row=i, command = lambda i=i: callback(i))
    
    def select_row(self, row_idx):
        self.deselect_row()
        self.selected_row = row_idx
        self.table.select_row(self.selected_row)
            
    def deselect_row(self):
        if self.selected_row is not None:
            self.table.deselect_row(self.selected_row)

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

        #self.table.update_values(values)
        
    def update_cell(self,value, col, row_idx=None):
        if row_idx is None:
            row_idx = self.selected_row
        if isinstance(col, str):
            col = self.header_dict[col]
        self.table.insert(row_idx, col, str(table_printer.pformat(value)))
        
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

class SwitchButton(ctk.CTkButton):
    button_groups = {}
    def __init__(self , *args, on_color, group=None, command=None, toggleable=False, **kwargs):
        super().__init__(*args, command=self.on_click, hover=False, **kwargs)
        self.on_color = on_color
        self.off_color = super().cget("fg_color")
        self.border_color = super().cget("border_color")
        self.border_width = super().cget("border_width")
        self.selected = False
        self.toggleable = toggleable
        self.command = command
        self.group = group
        self.on_enter_id = None
        self.on_leave_id = None
        if group is not None:
            SwitchButton.button_groups.setdefault(group, []).append(self)
        if super().cget("state") == "disabled":
            self.enabled = True
            self.disable()
        else:
            self.enabled = False
            self.enalbe()
        # create label
        
    def on_enter(self, event):
        super().configure(border_color="white")
    def on_leave(self, event):
        super().configure(border_color=self.border_color)
    def add_enter_leave_interaction(self):
        if self.on_enter_id is None and self.on_leave_id is None:
            self.on_enter_id = super().bind("<Enter>", self.on_enter, add='+')
            self.on_leave_id = super().bind("<Leave>", self.on_leave, add='+')
    def remove_enter_leave_interaction(self):
        print("Remove Enter Leave")
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
        elif self.toggleable:
            self.turn_off()
    def turn_on(self):
        super().configure(fg_color=self.on_color)
    def turn_off(self):
        super().configure(fg_color=self.off_color)
    def enable(self):
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
    def disable(self):
        if self.enabled == True:
            super().configure(state="disabled", border_color="gray")
            self.remove_enter_leave_interaction()
            self.enabled = False
            self.disable_children()
    def disable_children(self):
        for child in all_children(self):
            print(child)
            if isinstance(child, ctk.CTkButton):
                print("is button!")
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

class Phase(dict):
    def __init__(self,proband_file, *args, **kwargs):
        __slots__ = ()
        self.filename = proband_file
        with open(self.filename, 'r') as f:
            s = f.read()
            super().__init__(literal_eval(s))
        self.phase_type = self["Abstufung"]
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
        reactions = [sz.get("Stoert") for s in self["Durchgange"] for sz in s["Szenen"]]
        return True if None not in reactions else False
    
    def check_completion_test(self):
        return True

    def check_lowest_bothering_scenes(self):
        # loop over all scenes, filter them depending on the spot and the time of day
        # return the lowest bothering E value for every category (spot, time of day)
        bothering_scenes = {}
        for s in self["Durchgange"]:
            for sz in s["Szenen"]:
                if sz.get("Stoert") == "Ja":
                    E_value = sz.get("E")
                    spot = sz.get("Spot")
                    if spot in [1, 2, 3, 4]:
                        key = ("Spots", s.get("Zeit"))
                        current_minimum = bothering_scenes.setdefault(key, [None] * 4)[spot-1]
                        bothering_scenes[key][spot-1] = E_value if current_minimum is None else min(E_value,current_minimum)
                    else:
                        key = (spot, s.get("Zeit"))
                        if (key not in bothering_scenes):
                            bothering_scenes[key] = E_value
                        elif E_value < bothering_scenes[key]:
                            bothering_scenes[key] = E_value
        return bothering_scenes
    
    def save(self):
        filename_base = splitext(self.filename)[0]
        fname = self.filename
        with open(fname, 'w') as f:
            f.write(printer.pformat(self))

        
        if self.check_completion() == True:
            self.complete = True
            fname = f"{filename_base}_result_complete.txt"
            counter = 1
            while exists(fname):
                fname = f"{filename_base}_result_complete_{counter}.txt"
                counter += 1
        with open(fname, 'w') as f:
            f.write(printer.pformat(self))

class App(ctk.CTk, AsyncCTk):
    def __init__(self):
        super().__init__()
        ######## Setup the Window ########
        self.title("Studie Raumaufhellung")
        self.geometry("1200x800") 
        self.resizable(False, False)
        ##################################
        
        ######## Settings ########
        self.settings = {
            "qlc_address":              'localhost:9999',
            "qlc_project":              'VersuchsraumLeo.qxw',
            "monitor_serial_port":      'COM3',
            "monitor_baud_rate":        9600,
            "monitor_E_factor_spot_1":  2.41e7,
            "monitor_E_factor_spot_2":  2.41e7,
            "monitor_E_factor_spot_3":  3.63e7,
            "monitor_E_factor_spot_4":  2.70e7,
            "monitor_E_factor_diffus":  1.26e7,
            "scene_duration":           4.5, #4.5, # seconds
            "scene_fade_duration":      0.2, # seconds QLC fades in 100 ms
            "inter-stimulus-interval":  2.5, #2.5, #seconds
            "isi_fade_duration" :       0.5, # seconds. QLC fades in 300 ms
            "sequence_pause_duration":  45.0, # 45 seconds
            "maxE_spot1": 168.9,
            "maxE_spot2": 116.9,
            "maxE_spot3": 192.4,
            "maxE_spot4": 88,
            "maxE_diffus": 610,
            "DMX_brightness_reading": 255,
            "DMX_brightness_roomlight": 255,
            "learn_proband_file": "ProbandLernen.txt" 
        }
        self.monitor_I = None

        self.scene_start_timestamp = None
        self.current_scene_idx = None
        
        self.active_phase = None
        self.active_sequence = None
        self.active_scene = None
        self.sequence_task = None
        #self.grid_columnconfigure((0, 1), weight=1)
        #self.grid_rowconfigure((0, 1), weight=1)
        
        self.phase_lernen = Phase(self.settings["learn_proband_file"])
        self.phase_lernen.save = lambda: None # do not save learning sequence
        self.phase_grob = None
        self.phase_fein = None
        
        ######## Frame to simulate Input on Light Szene, bothering or not? ########
        self.inquery_frame = ctk.CTkFrame(self)
        self.inquery_frame.grid(row=0, column=2, padx=10, pady=10, sticky="nw")

        self.inquery_label = ctk.CTkLabel(self.inquery_frame, text="Ist die Szene störend?").grid(row=0, column=0, padx=10, pady=10, sticky="w")

        self.stoer_button = ctk.CTkButton(self.inquery_frame, text="Jo", command=lambda: self.set_scene_reaction(disturbing=True))
        self.stoer_button.grid(row=1, column=0, padx=10, pady=10, sticky="w")

        ######## Frame to control the sequences ########
        self.seq_crtl_frame = ctk.CTkFrame(self, width=150)
        self.seq_crtl_frame.grid(row=0, column=0, padx=10, pady=10, sticky="wn")
        
        phase_buttons_settings = {"height":90, "anchor":"n", "border_width":2, "text_color":"black", "border_color":"black",
                                     "fg_color":"transparent", "hover_color":"light blue"}
        sequence_buttons_settings = {"height":25, "border_width":1, "text_color":"black", "border_color":"black",
                                        "fg_color":"transparent", "hover_color":"light blue"}
        
        self.load_proband_button = ctk.CTkButton(self.seq_crtl_frame, text="Proband-Phase laden", command=self.load_proband)
        self.load_proband_button.grid(row=0, column=0, padx=10, pady=10, sticky="n")
        
        self.lern_phase_button = SwitchButton(self.seq_crtl_frame, group="phase", on_color="green", text="Lernphase", **phase_buttons_settings, command=lambda:self.set_phase(self.phase_lernen), state="disabled")
        self.lern_phase_button.grid(row=1, column=0, padx=10, pady=10, sticky="n")
        
        self.grob_phase_button = SwitchButton(self.seq_crtl_frame, group="phase", on_color="green", text="Phase grobes Raster", **phase_buttons_settings, command=lambda:self.set_phase(self.phase_grob), state="disabled")
        self.grob_phase_button.grid(row=2, column=0, padx=10, pady=10, sticky="n")
        
        self.grob_next_seq_button = ctk.CTkButton(self.grob_phase_button, **sequence_buttons_settings, width=30, text=">", command=self.set_next_sequence, state="disabled")
        self.grob_next_seq_button.place(relx=0.7, rely=0.6, anchor="center")
        self.grob_prev_seq_button = ctk.CTkButton(self.grob_phase_button, **sequence_buttons_settings, width=30, text="<", command=self.set_prev_sequence, state="disabled")
        self.grob_prev_seq_button.place(relx=0.3, rely=0.6, anchor="center")
        
        self.fein_phase_button = SwitchButton(self.seq_crtl_frame, group="phase", on_color="green", text="Phase feines Raster", **phase_buttons_settings, command=lambda:self.set_phase(self.phase_fein), state="disabled")
        self.fein_phase_button.grid(row=3, column=0, padx=10, pady=10, sticky="n")
        
        self.fein_next_seq_button = ctk.CTkButton(self.fein_phase_button, **sequence_buttons_settings, width=30, text=">", command=self.set_next_sequence,state="disabled")
        self.fein_next_seq_button.place(relx=0.7, rely=0.6, anchor="center")
        self.fein_prev_seq_button = ctk.CTkButton(self.fein_phase_button, **sequence_buttons_settings, width=30, text="<", command=self.set_prev_sequence, state="disabled")
        self.fein_prev_seq_button.place(relx=0.3, rely=0.6, anchor="center")
        
        self.sequence_start_reset_button = ctk.CTkButton(self.seq_crtl_frame, text="Durchgang starten", command=self.run_sequence, state="disabled")
        self.sequence_start_reset_button.grid(row=4, column=0, padx=10, pady=10, sticky="n")
        
        self.sequence_stop_continue_button = ctk.CTkButton(self.seq_crtl_frame, text="Durchgang anhalten", command=self.stop_sequence, state="disabled")
        self.sequence_stop_continue_button.grid(row=5, column=0, padx=10, pady=10, sticky="n")
        
        self.sequence_stop_event = asyncio.Event()
        self.sequence_continue_event = asyncio.Event()
        self.pause_stop_event = asyncio.Event()
        
        # second column
        self.table_frame = ctk.CTkFrame(self,fg_color="transparent")
        self.table_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nw")
        self.proband_label = ctk.CTkLabel(self.table_frame, text="Proband", anchor="w", font=(font.nametofont("TkDefaultFont"), 18))
        self.proband_label.grid(row=0, column=0, padx=10, pady=(10,0),sticky='w')
        self.sequence_scene_label = ctk.CTkLabel(self.table_frame, text="Durchgang", anchor="w", font=(font.nametofont("TkDefaultFont"), 18))
        self.sequence_scene_label.grid(row=1, column=0, padx=10, pady=0, sticky='w')
        
        self.sequence_table = ClickableTable(self.table_frame, header_labels=["Szene", "Spot", "E","E Monitor","Störend", "Reaktionszeit"], row_num=25)
        self.sequence_table.grid(row=2, column=0, padx=0, pady=10, sticky="w")
        self.sequence_table.set_callback(self.row_click)
        
        ########   Countdown Timer  ########
        self.timer_running = False
        self.countdown_timer_var = DoubleVar()
        self.countdown_timer_var.trace_add('write', self.print_countdown_timer)
        self.scene_countdown_end = 0.0
        self.scene_countdown_finished = asyncio.Event()
        self.countdown_label  = ctk.CTkLabel(self.table_frame, text="Test", font=(font.nametofont("TkDefaultFont"), 18))
        self.countdown_label.place(relx=0.89, y=18, anchor="nw")
        self.countdown_digits = ctk.CTkLabel(self.table_frame, text="00.0", font=(font.nametofont("TkDefaultFont"), 18))
        self.countdown_digits.place(relx=0.88, y=18, anchor="ne")
        
        ########    QLC+ Control    ########
        # automatically connect to QLC+ on startup / start the program if necessary
        self.qlc_init_button = ctk.CTkButton(self, text="QLC+ initialisieren", command=self.init_qlc)
        self.qlc_init_button.grid(row=1, column=2, padx=10, pady=10, sticky="nw")
        
        self.artnet_interface_helperbutton = ctk.CTkButton(self, command=self.create_artnet_interface)
        self.project_loaded = False
        
        self.after(100,self.artnet_interface_helperbutton.invoke) # workaround, because async does not work in __init__

        ######## Room light ########
        self.roomlight_button = ctk.CTkButton(self.seq_crtl_frame, text="Raumlicht", command=lambda:self.set_roomlight_level(2))
        self.roomlight_button.grid(row=7, column=0, padx=10, pady=10, sticky="s")

        ######## E_Monitor ########
        self.read_monitor_button = ctk.CTkButton(self, command=self.read_monitor_continuously)
        self.after(100,self.read_monitor_button.invoke)
        ######## User Input Key ########
        self.bind("<F20>", lambda e: self.set_scene_reaction(disturbing=True))
        self.scene_disturbing = asyncio.Event()
        
        ######## Check Window ########
        self.diffus_window = None
        self.position_window = None
        self.diffus_status = None
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
                    if ser.in_waiting > 0:  # Prüfen, ob Daten verfügbar sind
                        raw_text += ser.read(ser.in_waiting).decode('ascii')  # Alle verfügbaren Bytes 
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
            spot = self.active_scene.get("Spot")
            factor = self.settings.get("monitor_E_factor_spot_{}".format(spot)) if spot in [1,2,3,4] else self.settings.get("monitor_E_factor_diffus")
            EM = self.monitor_I * factor
            EM = f"{EM:.2e}" #E Monitor anpassen auf exponentielle Schreibweise für die Tabelle
            print(EM)
            self.sequence_table.update_cell(EM, "E Monitor")
            self.active_scene["E_monitor"] = EM
    
    def open_check_window(self,diffus = None, zeit = None):
        if diffus is not None:
            if diffus == True:
                title="Diffuse Scheibe einsetzen"
                label="Diffuse Scheibe ist eingesetzt"
            if diffus == False:
                title="Diffuse Scheibe entfernen"
                label="Diffuse Scheibe ist entfernt"
            if self.diffus_window is None or not self.diffus_window.winfo_exists():
                self.diffus_window = CheckWindow(self,title=title,label=label)  # create window if its None or destroyed
            else:
                self.diffus_window.focus()  # if window exists focus it
            self.wait_window(self.diffus_window)
        if zeit is not None:
            if zeit == "Abend":
                title="Probandenposition sitzend"
                label="Proband sitzt"
            if zeit == "Nacht":
                title="Probandenposition liegend"
                label="Proband liegt"
            if self.position_window is None or not self.position_window.winfo_exists():
                self.position_window = CheckWindow(self,title=title,label=label)
            else:
                self.position_window.focus()  # if window exists focus it
            self.wait_window(self.position_window)
    
    def row_click(self,row_idx):
        if self.sequence_task is not None: # if task exists
            if self.sequence_task.done() is False: # if Task is running
                if not self.sequence_stop_event.is_set(): # if Task not stopped
                    print("Task is not stopped")
                    return
        else: # task does not exist
            if self.active_sequence is None: # if proband not loaded
                print("Proband not loaded")
                return
        self.current_scene_idx = row_idx
        self.sequence_table.select_row(self.current_scene_idx)

    def load_proband(self):
        phase = Phase(filedialog.askopenfilename(filetypes=[("Text file", "*.txt"),("All files", "*.*")]))
        if phase.phase_type == "grob":
            self.phase_grob = phase
            if self.phase_grob["Lerndurchgang"] == True:
                self.lern_phase_button.turn_on()
                self.grob_phase_button.enable()
            if self.phase_grob.check_completion() == True:
                self.grob_phase_button.turn_on()
                self.generate_and_load_phase_fein()
            
            self.lern_phase_button.enable()
        if phase.phase_type == "fein":
            pass # maybe implement later
        
    def generate_and_load_phase_fein(self):
        prid = self.phase_grob["ID"]
        th = self.phase_grob.check_lowest_bothering_scenes()
        fein_file = erzeuge_proband_fein(prid, th.get(('Spots','Abend')),
                                               th.get(('Spots','Nacht')),
                                               th.get(('diffus','Abend')),
                                               th.get(('diffus','Nacht')))
        self.phase_fein = Phase(fein_file)
        self.fein_phase_button.enable()
        
    def set_next_sequence(self):
        if self.active_phase is None:
            return
        self.active_phase.next_sequence()
        self.set_sequence()
    
    def set_prev_sequence(self):
        if self.active_phase is None:
            return
        self.active_phase.prev_sequence()
        self.set_sequence()
        
    def set_phase(self,phase):
        self.active_phase = phase
        self.set_sequence()
        self.proband_label.configure(text="Proband {id}: {stufung}".format(id=self.active_phase["ID"], stufung=self.active_phase["Abstufung"]))
    
    def set_sequence_scene_label(self):
        if self.active_sequence is None:
            return
        progress = sum(s.get("Stoert") is not None for s in self.active_sequence["Szenen"])
        label = "Durchgang {did}: {Zeit} | {diffus}, Fortschritt {pgr}/{num}".format(did=self.active_sequence["ID"],
                                                                                Zeit=self.active_sequence["Zeit"],
                                                                                diffus="Diffus" if self.active_sequence["Diffus"] else "Gerichtet",
                                                                                pgr=progress,
                                                                                num=len(self.active_sequence["Szenen"]))
        self.sequence_scene_label.configure(text=label)
        
    def set_sequence(self):
        self.active_sequence = self.active_phase.get_current_sequence()
        seq_values = [[s.get("ID"),s.get("Spot"),s.get("E"), s.get("E_monitor"),s.get("Stoert"),s.get("Reaktionszeit")] for s in self.active_sequence["Szenen"]]
        self.sequence_table.update_table(seq_values)

        self.set_sequence_scene_label()
        #self.sequence_label.configure(text="Durchgang {id}".format(id=self.active_sequence["ID"]))
        #self.sequence_table.update_title_proband("Proband {id}: {stufung}".format(id=self.proband["ID"], stufung=self.proband["Abstufung"]))
        self.sequence_start_reset_button.configure(state="normal")
    
    def stop_sequence(self):
        self.sequence_stop_continue_button.configure(text="Durchgang fortsetzen",
                                                  command=self.continue_sequence,
                                                  fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"])
        self.sequence_stop_event.set()
        self.roomlight_button.configure(state="normal")
        self.set_roomlight_level(1)
        
    def continue_sequence(self):
        self.sequence_stop_continue_button.configure(text="Durchgang anhalten", command=self.stop_sequence, fg_color="red")
        self.sequence_continue_event.set()
        self.roomlight_button.configure(state="disabled")
        self.set_roomlight_level(0)
        
    def reset_sequence(self):
        self.sequence_task.cancel()

    async def run_sequence_task(self):
        try:
            # open check windows for current sequence: window diffusor and subject position
            if self.diffus_status != self.active_sequence["Diffus"]:
                self.diffus_status = self.active_sequence["Diffus"]
                self.open_check_window(diffus=self.diffus_status)
                
            if self.time_position_status != self.active_sequence["Zeit"]:
                print("Time Position Status: ", self.time_position_status)
                print("Active Sequence Zeit: ", self.active_sequence["Zeit"])
                self.time_position_status = self.active_sequence["Zeit"]
                self.open_check_window(zeit=self.time_position_status)

            # prepare scenes
            scenes = self.active_sequence["Szenen"]
            scene_num = len(scenes)
            scene_duration = self.settings["scene_duration"]
            scene_fade_duration = self.settings["scene_fade_duration"]
            isi_duration = self.settings["inter-stimulus-interval"]
            isi_fade_duration = self.settings["isi_fade_duration"]
            pause_duration = self.settings["sequence_pause_duration"]
            if self.current_scene_idx is None:
                self.current_scene_idx = 0
            self.set_scene(scenes[self.current_scene_idx])
            self.sequence_table.select_row(self.current_scene_idx)
            cur_next_scenes = [cur_next for cur_next in pairwise([*scenes,None])]
            
            # setup the lighting for the room
            self.set_reading_light(self.time_position_status == "Abend")
            self.set_roomlight_level(0) # turn off dim pause light
            # display isi light for twice the duration before a sequence starts
            # time for the proband to get accustomed to the light
            self.activate_isi()
            await self.await_countdown_timer(start_time=isi_duration * 2,
                                                 end_time=isi_fade_duration,
                                                 stop_event=self.sequence_stop_event,
                                                 label="ISI")
            self.fade_isi()
            await self.await_countdown_timer(label="ISI")
            
            # loop over all scenes. only advances scene if run to completion
            while self.current_scene_idx < (scene_num):
                scene,next_scene  = cur_next_scenes[self.current_scene_idx]
                
                self.sequence_table.select_row(self.current_scene_idx)
                
                # configure label
                self.set_sequence_scene_label()

                self.activate_scene()
                self.active_scene = scene
                #self.clear_scene_reaction()
                self.scene_disturbing.clear() # reset disturbing flag, ready for new input
                self.scene_start_timestamp = timer()
                await self.await_countdown_timer(start_time=scene_duration,
                                                 end_time=scene_fade_duration,
                                                 stop_event=self.sequence_stop_event,
                                                 label="Szene")
                if not self.sequence_stop_event.is_set():
                    self.set_scene_monitor()
                # set inter-stimulus lighting
                self.fade_scene()
                await self.await_countdown_timer(label="Szene") # rest is fade duration, not interruptable to prevent flashing
                self.activate_isi()
                
                await self.await_countdown_timer(start_time=isi_duration,
                                                 end_time=isi_fade_duration,
                                                 stop_event=self.sequence_stop_event,
                                                 label="ISI")
                if self.sequence_stop_event.is_set(): # if stopped, keep interstimulus lighting
                    self.active_scene = None # No scene is active
                    await self.sequence_continue_event.wait() # wait for continue event
                    self.sequence_continue_event.clear()
                    self.sequence_stop_event.clear()
                    scene,_  = cur_next_scenes[self.current_scene_idx] # update scene, in case different index was chosen
                    self.set_scene(scene)
                    self.fade_isi()
                    await asyncio.sleep(isi_fade_duration)
                    continue

                if next_scene is not None:
                    self.set_scene(next_scene) 
                self.fade_isi()
                await self.await_countdown_timer(stop_event=self.sequence_stop_event,label="ISI") # count down rest of the timer
                if self.sequence_stop_event.is_set():
                    continue
                
                self.set_scene_reaction(disturbing=False)
                
                self.sequence_table.deselect_row()
                self.current_scene_idx += 1
        finally:
            #self.activate_isi() No ISI inbetween sequences
            self.set_roomlight_level(1) # turn on dim pause light
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
            
            # if phase is complete, enable next phase
            self.lern_phase_button.enable()
            if self.phase_lernen.check_completion() == True:
                self.phase_grob["Lerndurchgang"] = True
            if self.phase_grob["Lerndurchgang"] == True:
                self.lern_phase_button.turn_on()
                self.grob_phase_button.enable()
            if self.phase_grob.check_completion() == True:
                self.grob_phase_button.turn_on()
                self.generate_and_load_phase_fein()
            for button in [self.lern_phase_button, self.grob_phase_button,self.fein_phase_button]:
                if button.selected:
                    button.enable_children()
            
            # wait for the pause duration here. stop event can be set from the run_sequence function, after aquisition of a popup
            await self.await_countdown_timer(start_time=pause_duration,
                                             stop_event=self.pause_stop_event,
                                             label="Pause")

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
        self.grob_phase_button.disable_children()
        self.fein_phase_button.disable_children()
        for button in [self.lern_phase_button, self.grob_phase_button,self.fein_phase_button]:
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
            self.after(100, self.countdown_timer_cb)  # Countdown alle 100ms dekrementieren
        else:
            self.scene_countdown_finished.set()
    
    def set_scene_reaction(self, disturbing):
        if self.active_scene is None: # are we even running a scene?
            print("No scene running")
            return
        if disturbing is True:
            if self.scene_disturbing.is_set():
                print("Already set to disturbing")
                return
            self.scene_disturbing.set()
            stoert = "Ja"
            reaction_timestamp = timer()
            reaction_time = round(reaction_timestamp - self.scene_start_timestamp,3)
        else:
            # only set default not disturbing, if not already set to disturbing
            if self.scene_disturbing.is_set():
                return
            stoert = "Nein"
            reaction_time = ""

        self.active_scene["Stoert"] = stoert
        self.sequence_table.update_cell(stoert, "Störend")
        self.active_scene["Reaktionszeit"] = reaction_time
        self.sequence_table.update_cell(reaction_time,"Reaktionszeit")
        # save current results to file and check the progress
        if self.active_phase is not None:
            self.active_phase.save()
        
    def clear_scene_reaction(self):
        if self.active_scene is not None: # are we even running a scene?
            self.active_scene["Stoert"] = ""
            self.sequence_table.update_cell("", "Störend")
            self.active_scene["Reaktionszeit"] = ""
            self.sequence_table.update_cell("","Reaktionszeit")

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

        self.spot1_intensity    = self.qlc_input.add_channel(start=1, width=2) #  0:0
        self.spot2_intensity    = self.qlc_input.add_channel(start=3, width=2) #  0:47
        self.spot3_intensity    = self.qlc_input.add_channel(start=5, width=2) # 47:0
        self.spot4_intensity    = self.qlc_input.add_channel(start=7, width=2) # 47:47
        self.isi_intensity      = self.qlc_input.add_channel(start=9, width=2) # Master ISI intensity
        self.spot_color         = self.qlc_input.add_channel(start=11, width=4) # R,G,B,L
        self.isi_color          = self.qlc_input.add_channel(start=15, width=4) # R,G,B,L
        self.szene_ctc           = self.qlc_input.add_channel(start=19, width=1) # CTC
        self.isi_ctc            = self.qlc_input.add_channel(start=20, width=1) # CTC
        self.qlc_init_channel    = self.qlc_input.add_channel(start=21, width=1) # Init-Button
        self.sequence_control   = self.qlc_input.add_channel(start=22, width=1) # Control the Sequence of Szene and ISI
        self.pixel2_7_intensity = self.qlc_input.add_channel(start=23, width=1) # Pixel 2-7 intensity
        self.reading_light_intensity = self.qlc_input.add_channel(start=24, width=1) # Reading light intensity
        self.room_light_level = self.qlc_input.add_channel(start=25, width=1) # Room light

    def activate_isi(self):
        self.sequence_control.set_values([0])
    
    def fade_isi(self):
        self.sequence_control.set_values([255])
    
    def activate_scene(self):
        self.sequence_control.set_values([160])
    
    def fade_scene(self):
        self.sequence_control.set_values([96])

    def set_scene(self, scene):
        self.set_all_intensities(0)
        self.pixel2_7_intensity.set_values([0])
        dmx_max = 2**16 - 1
        spot = scene["Spot"]
        E = scene["E"] 
        if spot == 1:
            maxE = self.settings["maxE_spot1"]
            E = min( E, maxE )
            i = round((E / maxE) * dmx_max)
            self.spot1_intensity.set_values(i.to_bytes(2,'big'))

        elif spot == 2: 
            maxE = self.settings["maxE_spot2"]
            E = min( E, maxE )
            i = round((E / maxE) * dmx_max)
            self.spot2_intensity.set_values(i.to_bytes(2,'big'))
            
        elif spot == 3:
            maxE = self.settings["maxE_spot3"]
            E = min( E, maxE )
            i = round((E / maxE) * dmx_max)
            self.spot3_intensity.set_values(i.to_bytes(2,'big'))
            
        elif spot == 4:
            maxE = self.settings["maxE_spot4"]
            E = min( E, maxE )
            i = round((E / maxE) * dmx_max)
            self.spot4_intensity.set_values(i.to_bytes(2,'big'))
        elif spot == "diffus":
            maxE = self.settings["maxE_diffus"]
            E = min( E, maxE )
            i = round((E / maxE) * dmx_max)
            self.spot1_intensity.set_values(i.to_bytes(2,'big'))
            # also enable Pixel 2-7
            self.pixel2_7_intensity.set_values([255])

    def set_all_intensities(self,i):
        self.spot1_intensity.set_values(i.to_bytes(2,'big'))
        self.spot2_intensity.set_values(i.to_bytes(2,'big'))
        self.spot3_intensity.set_values(i.to_bytes(2,'big'))
        self.spot4_intensity.set_values(i.to_bytes(2,'big'))

    def set_isi(self):
        brightness = 2500
        self.isi_intensity.set_values(brightness.to_bytes(2,'big'))
        self.isi_color.set_values([255,0,0,0])
        self.pixel2_7_intensity.set_values([0])

class QLCArtNetInterface:
    def __init__(self):
        self.qlc_node = pan.ArtNetNode('127.0.0.1', 6454)
        self.qlc_input = self.qlc_node.add_universe(10)

        self.spot1_intensity    = self.qlc_input.add_channel(start=1, width=2) #  0:0
        self.spot2_intensity    = self.qlc_input.add_channel(start=3, width=2) #  0:47
        self.spot3_intensity    = self.qlc_input.add_channel(start=5, width=2) # 47:0
        self.spot4_intensity    = self.qlc_input.add_channel(start=7, width=2) # 47:47
        self.isi_intensity      = self.qlc_input.add_channel(start=9, width=2) # Master ISI intensity
        self.spot_color         = self.qlc_input.add_channel(start=11, width=4) # R,G,B,L
        self.isi_color          = self.qlc_input.add_channel(start=15, width=4) # R,G,B,L
        self.spot_ctc           = self.qlc_input.add_channel(start=19, width=1) # CTC
        self.isi_ctc            = self.qlc_input.add_channel(start=20, width=1) # CTC
        self.qlc_init_channel   = self.qlc_input.add_channel(start=21, width=1) # Init-Button
        self.sequence_control   = self.qlc_input.add_channel(start=22, width=1) # Control the Sequence of Szene and ISI
        self.pixel2_7_intensity = self.qlc_input.add_channel(start=23, width=1) # Pixel 2-7 intensity
        self.reading_light_intensity = self.qlc_input.add_channel(start=24, width=1) # Reading light intensity
        self.room_light = self.qlc_input.add_channel(start=25, width=1) # Room light

app = App()
app.async_mainloop()



