import ast
import itertools
from timeit import default_timer as timer
from os.path import splitext

import tkinter as tk
import customtkinter as ctk

import asyncio
from async_tkinter_loop import async_handler
from async_tkinter_loop.mixins import AsyncCTk
import async_timer
# maybe use uvloop (fast / more time-accurate event loop)

from CTkMenuBar import CTkTitleMenu
from CTkTable import CTkTable

import pyartnet as pan

import requests

class ClickableTable(ctk.CTkFrame):
    def __init__(self, *args, header_labels, row_num, callback = None, **kwargs):
        super().__init__(*args, **kwargs)
                ######## Frame to display the sequences in a table ########
        self.sequence_frame = ctk.CTkFrame(self)

        self.proband_label = ctk.CTkLabel(self, text="Proband", anchor="n")
        self.proband_label.grid(row=0, column=0, padx=0, pady=(5,0))
        self.durchgang_label = ctk.CTkLabel(self, text="", anchor="n")
        self.durchgang_label.grid(row=1, column=0, padx=0, pady=0)
        self.row_num = row_num
        self.col_num = len(header_labels)
        self.table_header = CTkTable(self, row=1, column=self.col_num, header_color='white', corner_radius=0, height=10, width=85)
        self.table_header.grid(row=2, column=0, padx=10, pady=0, sticky="n")
        self.table_header.update_values([header_labels])
        self.header_dict = dict(zip(header_labels, range(len(header_labels))))
        self.table = CTkTable(self, row=self.row_num, column=self.col_num, corner_radius=0, height=10, width=85)
        self.table.grid(row=3, column=0, padx=10, pady=(0,10), sticky="n")
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
                self.table.frame[i,j].configure(text=str(value),require_redraw=True)

        #self.table.update_values(values)
        
    def update_cell(self,value, col, row_idx=None):
        if row_idx is None:
            row_idx = self.selected_row
        if isinstance(col, str):
            col = self.header_dict[col]
        self.table.insert(row_idx, col, value)
        
    def update_title_proband(self, text):
        self.proband_label.configure(text=text)
        
    def update_title_durchgang(self, text):
        self.durchgang_label.configure(text=text)

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
    def __init__(self , *args, on_color, command=None, toggleable=False, **kwargs):
        super().__init__(*args, command=self.on_click, hover=False, **kwargs)
        self.on_color = on_color
        self.off_color = super().cget("fg_color")
        self.border_color = super().cget("border_color")
        self.border_width = super().cget("border_width")
        self.is_selected = False
        self.toggleable = toggleable
        self.command = command
        
        super().bind("<Enter>", self.on_enter, add='+')
        super().bind("<Leave>", self.on_leave, add='+')
    def on_enter(self, event):
        print("Enter")
        super().configure(border_color="white")
    def on_leave(self, event):
        print("Leave")
        super().configure(border_color=self.border_color)
    def on_click(self):
        if self.is_selected == False:
            self.select()
            if self.command is not None:
                self.command()
        elif self.toggleable:
            self.turn_off()
    def turn_on(self):
        super().configure(fg_color=self.on_color)
    def turn_off(self):
        super().configure(fg_color=self.off_color)
    def enalbe(self):
        super().configure(state="normal", border_color=self.border_color)
    def disable(self):
        super().configure(state="disabled", border_color="gray")
    def select(self):
        self.is_selected = True
        super().configure(border_color="white", border_width=self.border_width*2)
    def deselect(self):
        self.is_selected = False
        super().configure(border_color=self.border_color, border_width=self.border_width)


class App(ctk.CTk, AsyncCTk):
    def __init__(self):
        super().__init__()
        ######## Setup the Window ########
        self.title("Studie Raumaufhellung")
        self.geometry("1200x1000")
        self.resizable(False, False)
        ##################################
        
        ######## Settings ########
        self.settings = {
            "qlc_address":          'localhost:9999',
            "qlc_project":          'VersuchsraumLeo.qxw',
            "serial_port_monitor":  'COM4',
            "scene_duration":           4.5, # seconds
            "scene_fade_duration":      0.2, # seconds QLC fades in 100 ms
            "inter-stimulus-interval":  2.5, #seconds
            "isi_fade_duration" :       0.5, # seconds. QLC fades in 300 ms
            "maxE_spot1": 168.9,
            "maxE_spot2": 116.9,
            "maxE_spot3": 192.4,
            "maxE_spot4": 88,
            "maxE_diffus": 610,
            "DMX_brightness_reading": 255,
            "DMX_roomlight": 255
        }

        #self.grid_columnconfigure((0, 1), weight=1)
        #self.grid_rowconfigure((0, 1), weight=1)


        ######## Frame to simulate Input on Light Szene, bothering or not? ########
        self.inquery_frame = ctk.CTkFrame(self)
        self.inquery_frame.grid(row=0, column=2, padx=10, pady=10, sticky="nw")

        self.inquery_label = ctk.CTkLabel(self.inquery_frame, text="Ist die Szene störend?").grid(row=0, column=0, padx=10, pady=10, sticky="w")

        self.stoer_button = ctk.CTkButton(self.inquery_frame, text="Jo", command=lambda: self.set_scene_reaction(disturbing=True))
        self.stoer_button.grid(row=1, column=0, padx=10, pady=10, sticky="w")
        ###########################################################################
            
        self.proband = None
        self.active_scene = None
        self.scene_start_timestamp = None
        self.current_scene_idx = None
        self.active_sequence = None
        
        self.sequence_task = None

        ######## Frame to control the sequence ########
        self.seq_crtl_frame = ctk.CTkFrame(self, width=120)
        self.seq_crtl_frame.grid(row=0, column=0, padx=10, pady=10, sticky="wn")
        
        self.load_proband_button = ctk.CTkButton(self.seq_crtl_frame, text="Proband laden", command=self.load_proband)
        self.load_proband_button.grid(row=0, column=0, padx=10, pady=10, sticky="n")
        
        on_enter = lambda e: print("Enter")
        on_leave = lambda e: print("Leave")
        self.load_proband_button.bind("<Enter>", on_enter, add='+')
        self.load_proband_button.bind("<Leave>", on_leave, add='+')
        
        sequence_buttons_settings = {"height":90, "anchor":"n", "border_width":2, "text_color":"black", "border_color":"black",
                                     "fg_color":"transparent", "hover_color":"light blue"}
        
        self.test_sequence_button = SwitchButton(self.seq_crtl_frame, on_color="green", text="Testdurchgang", **sequence_buttons_settings, command=lambda:self.set_sequence("Test"))
        self.test_sequence_button.grid(row=1, column=0, padx=10, pady=10, sticky="n")
        
        self.grob_sequence_button = SwitchButton(self.seq_crtl_frame, on_color="green", text="Grobe Durchgänge", **sequence_buttons_settings, command=lambda:self.set_sequence("Grob"))
        self.grob_sequence_button.grid(row=2, column=0, padx=10, pady=10, sticky="n")
        
        self.fein_sequence_button = SwitchButton(self.seq_crtl_frame, on_color="green", text="Feine Durchgänge", **sequence_buttons_settings, command=lambda:self.set_sequence("Fein"))
        self.fein_sequence_button.grid(row=3, column=0, padx=10, pady=10, sticky="n")
        
        self.sequence_start_reset_button = ctk.CTkButton(self.seq_crtl_frame, text="Durchgang starten", command=self.run_sequence, state="disabled")
        self.sequence_start_reset_button.grid(row=6, column=0, padx=10, pady=10, sticky="s")
        
        self.sequence_stop_continue_button = ctk.CTkButton(self.seq_crtl_frame, text="Durchgang anhalten", command=self.stop_sequence, state="disabled")
        self.sequence_stop_continue_button.grid(row=7, column=0, padx=10, pady=10, sticky="s")
        
        self.seq_switch_label = ctk.CTkLabel(self.seq_crtl_frame, text="Durchgang wählen")
        self.seq_switch_label.grid(row=4, column=0, padx=0, pady=0, sticky="we")
        self.seq_switch_frame = ctk.CTkFrame(self.seq_crtl_frame, fg_color="transparent")
        self.seq_switch_frame.grid(row=5, column=0, padx=10, pady=0, sticky="wn")

        self.next_seq_button = ctk.CTkButton(self.seq_switch_frame, text=">", width=60, command=self.next_sequence, state="disabled")
        self.next_seq_button.grid(row=1, column=1, padx=10, pady=5, sticky="e")
        self.prev_seq_button = ctk.CTkButton(self.seq_switch_frame, text="<", width=60, command=self.prev_sequence, state="disabled")
        self.prev_seq_button.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        
        self.sequence_stop_event = asyncio.Event()
        self.sequence_continue_event = asyncio.Event()
        
        self.sequence_table = ClickableTable(self, header_labels=["Szene", "Spot", "E","E Monitor","Störend", "Reaktionszeit"], row_num=40)
        self.sequence_table.grid(row=0, column=1, padx=10, pady=10, sticky="w")
        self.sequence_table.set_callback(self.row_click)
        
        ########   Countdown Timer  ########
        self.scene_countdown_timer =  tk.DoubleVar()
        self.scene_countdown_timer.trace_add('write', self.print_scene_countdown)
        self.scene_countdown_end = 0.0
        self.scene_countdown_finished = asyncio.Event()
        self.scene_countdown_label = ctk.CTkLabel(self, text="", font=("Helvetica", 30))
        self.scene_countdown_label.grid(row=1, column=3, padx=10, pady=20)
        
        #self.scene_label = ctk.CTkLabel(self, text="Szene")
        #self.scene_label.grid(row=1, column=2, padx=10, pady=10, sticky="nw")
        
        ########    QLC+ Control    ########
        # automatically connect to QLC+ on startup / start the program if necessary
        self.qlc_init_button = ctk.CTkButton(self, text="QLC+ initialisieren", command=self.init_qlc)
        self.qlc_init_button.grid(row=1, column=2, padx=10, pady=10, sticky="nw")
        
        self.artnet_interface_helperbutton = ctk.CTkButton(self, text="ArtNet Interface laden", command=self.create_artnet_interface)
        self.project_loaded = False
        
        self.after(100,self.artnet_interface_helperbutton.invoke) # workaround, because async does not work in __init__

        ######## Room light ########
        self.room_light_on = False
        self.room_light_button = ctk.CTkButton(self.seq_crtl_frame, text="Raumlicht", command=self.toggle_roomlight)
        self.room_light_button.grid(row=9, column=0, padx=10, pady=10, sticky="s")


        ########    User Input Key  ########
        self.bind("<F20>", lambda e: self.set_scene_reaction(disturbing=True))
        self.scene_disturbing = asyncio.Event()
        
        ########    Check Window    ########
        self.diffuse_window = None
        self.position_window = None
        self.diffuse_status = None
        self.position_status = None
        
    def open_check_window(self,diffuse = None, position = None):
        if diffuse is not None:
            if diffuse == True:
                title="Diffuse Scheibe einsetzen"
                label="Diffuse Scheibe ist eingesetzt"
            if diffuse == False:
                title="Diffuse Scheibe entfernen"
                label="Diffuse Scheibe ist entfernt"
            if self.diffuse_window is None or not self.diffuse_window.winfo_exists():
                self.diffuse_window = CheckWindow(self,title=title,label=label)  # create window if its None or destroyed
            else:
                self.diffuse_window.focus()  # if window exists focus it
            self.wait_window(self.diffuse_window)
        if position is not None:
            if position == "Sitzen":
                title="Probandenposition sitzend"
                label="Proband sitzt"
            if position == "Liegen":
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
            if self.proband is None: # if proband not loaded
                print("Proband not loaded")
                return
        self.current_scene_idx = row_idx
        self.sequence_table.select_row(self.current_scene_idx)
    
    def load_proband(self):
        self.filename = tk.filedialog.askopenfilename(filetypes=[("Text file", "*.txt"),("All files", "*.*")])
        with open(self.filename, 'r') as f:
            s = f.read()
            self.proband = ast.literal_eval(s)
        self.seq_num = len(self.proband["Durchgange"])
        self.seq_idx = 0
        self.set_sequence()
        self.sequence_start_reset_button.configure(state="normal")
        self.next_seq_button.configure(state="normal")
        self.prev_seq_button.configure(state="normal")
        
        self.sequence_table.update_title_proband("Proband {id}: {stufung}".format(id=self.proband["ID"], stufung=self.proband["Abstufung"]))
        
    def save_proband(self):
        filename_base = splitext(self.filename)[0]
        with open(filename_base + '_result.txt', 'w') as f:
            print(self.proband, file=f)
        
    def next_sequence(self):
        self.seq_idx += 1
        if self.seq_idx >= self.seq_num:
            self.seq_idx -= self.seq_num
        self.set_sequence()
    
    def prev_sequence(self):
        self.seq_idx -= 1
        if self.seq_idx < 0:
            self.seq_idx += self.seq_num
        self.set_sequence()

    def set_sequence(self):
        if self.proband is not None:
            self.active_sequence = self.proband["Durchgange"][self.seq_idx]
        seq_values = [[s.get("ID"),s.get("Spot"),"{:6.3f}".format(s.get("E")), s.get("E_monitor"),s.get("Stoert"),s.get("Reaktionszeit")] for s in self.active_sequence["Szenen"]]
        self.sequence_table.update_table(seq_values)
        
        #self.sequence_label.configure(text="Durchgang {id}".format(id=self.active_sequence["ID"]))
    
    def stop_sequence(self):
        self.sequence_stop_continue_button.configure(text="Durchgang fortsetzen",
                                                  command=self.continue_sequence,
                                                  fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"])
        self.sequence_stop_event.set()
        self.room_light_button.configure(state="normal")
    

    def continue_sequence(self):
        self.sequence_stop_continue_button.configure(text="Durchgang anhalten",
                                                  command=self.stop_sequence,
                                                  fg_color="red")
        self.sequence_continue_event.set()
        self.room_light_button.configure(state="disabled")
        self.set_roomlight(False)
        
        
    def reset_sequence(self):
        self.sequence_task.cancel()
        self.room_light_button.configure(state="normal")

    async def run_sequence_task(self):
        try:
            # open check windows for current sequence: window diffusor and subject position
            if self.diffuse_status is not self.active_sequence["Diffus"]:
                self.diffuse_status = self.active_sequence["Diffus"]
                self.open_check_window(diffuse=self.diffuse_status)
                
            if self.position_status is not self.active_sequence["Position"]:
                self.position_status = self.active_sequence["Position"]
                self.open_check_window(position=self.position_status)
                # turn the lamp on or off for this run
                # leselicht einschalten

            self.light_intensity_reading.set_values([self.settings["DMX_brightness_reading"] if self.position_status == "Sitzen" else 0])
                #self.light_intensity_reading.set_values([120])
                
            
            scenes = self.active_sequence["Szenen"]
            scene_num = len(scenes)
            
            # prepare first scene
            scene_duration = self.settings["scene_duration"]
            scene_fade_duration = self.settings["scene_fade_duration"]
            isi_duration = self.settings["inter-stimulus-interval"]
            isi_fade_duration = self.settings["isi_fade_duration"]
            
            if self.current_scene_idx is None:
                self.current_scene_idx = 0
            
            self.set_scene(scenes[self.current_scene_idx])
            self.sequence_table.select_row(self.current_scene_idx)
            self.fade_isi()
            await asyncio.sleep(isi_fade_duration)
            # loop over all scenes. only advances scene if run to completion
            cur_next_scenes = [cur_next for cur_next in itertools.pairwise([*scenes,None])]
            while self.current_scene_idx < (scene_num):
                scene,next_scene  = cur_next_scenes[self.current_scene_idx]
                
                self.sequence_table.select_row(self.current_scene_idx)
                #self.scene_label.configure(text="Szene {id}/{num}".format(id=scene["ID"], num=scene_num))

                self.activate_scene()
                self.active_scene = scene
                self.clear_scene_reaction()
                self.scene_disturbing.clear() # reset disturbing flag, ready for new input
                self.scene_start_timestamp = timer()
                await self.await_countdown_timer(start_time=scene_duration,
                                                 end_time=scene_fade_duration,
                                                 stop_event=self.sequence_stop_event)
                
                # set inter-stimulus lighting
                self.fade_scene()
                await self.await_countdown_timer() # rest is fade duration, not interruptable to prevent flashing
                self.activate_isi()
                
                await self.await_countdown_timer(start_time=isi_duration,
                                                 end_time=isi_fade_duration,
                                                 stop_event=self.sequence_stop_event)
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
                await self.await_countdown_timer(stop_event=self.sequence_stop_event) # count down rest of the timer
                if self.sequence_stop_event.is_set():
                    continue
                
                self.set_scene_reaction(disturbing=False)
                self.sequence_table.deselect_row()
                self.current_scene_idx += 1
        finally:
            self.activate_isi()
            self.sequence_table.deselect_row()
            self.sequence_stop_event.clear()
            #self.scene_disturbing.clear()
            self.scene_countdown_timer.set(0)
            self.active_scene = None
            self.current_scene_idx = None
            self.sequence_start_reset_button.configure(text="Durchgang starten", command=self.run_sequence)
            self.sequence_stop_continue_button.configure(text="Durchgang anhalten", command=self.stop_sequence,
                                                        state="disabled", fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"])
            #self.scene_label.configure(text="Szene")
            self.next_seq_button.configure(state="normal")
            self.prev_seq_button.configure(state="normal")
            

    @async_handler
    async def run_sequence(self):
        self.sequence_task = asyncio.create_task(self.run_sequence_task(), name="run_sequence")
        # switch button to stop sequence
        self.sequence_stop_continue_button.configure(state='normal',fg_color="red")
        self.sequence_start_reset_button.configure(text="Durchgang zurücksetzen", command=self.reset_sequence)
        
        self.next_seq_button.configure(state="disabled")
        self.prev_seq_button.configure(state="disabled")
        self.room_light_button.configure(state="disabled")
        self.set_roomlight(False)
        #self.room_light_on = False  # Schaltet das Raumlicht aus
        #self.roomlight(self.room_light_on)  # Aktualisiert den Zustand basierend auf der Variable
        await self.sequence_task


    

    def print_scene_countdown(self, *args):
        self.scene_countdown_label.configure(text="{:04.1f}".format(self.scene_countdown_timer.get()))
    
    async def await_countdown_timer(self, start_time = None, end_time = None, stop_event = None):
        if(end_time == None):
            end_time = 0
        self.scene_countdown_end = end_time
        self.scene_countdown_finished.clear()
        if(start_time != None):
            self.scene_countdown_timer.set(start_time)
        self.after(100, self.countdown_timer_cb) # starts the timer
        if stop_event is not None:
            await asyncio.wait(
                [asyncio.create_task(self.scene_countdown_finished.wait()),
                asyncio.create_task(stop_event.wait())],return_when=asyncio.FIRST_COMPLETED)
            if stop_event.is_set():
                self.scene_countdown_timer.set(0) # reset to zero
                return
        else:
            await self.scene_countdown_finished.wait()
            
        self.scene_countdown_timer.set(self.scene_countdown_end) # leave it at end_time


    def countdown_timer_cb(self):
        timer_value = self.scene_countdown_timer.get()
        timer_value -= 0.1
        if timer_value > self.scene_countdown_end:
            self.scene_countdown_timer.set(round(timer_value,1))
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
                #self.scene_disturbing.clear()
                return
            stoert = "Nein"
            reaction_time = ""
            
        self.active_scene["Stoert"] = stoert
        self.sequence_table.update_cell(stoert, "Störend")
        self.active_scene["Reaktionszeit"] = reaction_time
        self.sequence_table.update_cell(reaction_time,"Reaktionszeit")
        # save current results to file
        self.save_proband()
            
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
                r = requests.post("http://{addr}/loadProject".format(addr = self.settings["qlc_address"]), files={'qlcprj': f})
            r = True
        finally:
            return r
    
    @async_handler
    async def init_qlc(self):
        if self.load_qlc_project() == True:
            self.qlc_init_button.configure(text="QLC+ initialisiert", fg_color="green", state="disabled")
            await asyncio.sleep(0.2) # wait for project to load
            self.pixel2_7_intensity.set_values([0])
    
            self.qlc_init_channel.set_values([255])
            self.set_all_intensities(0)
            self.set_isi()
            self.spot_color.set_values([255,255,255,255])
            self.activate_isi()


    def toggle_roomlight(self):
        self.room_light_on = not self.room_light_on
        self.set_roomlight(self.room_light_on)


    def set_roomlight(self,state):
        if state == True:
            # Turn on the light
            self.room_light.set_values([self.settings["DMX_roomlight"]])
            # Set button color to green
            self.room_light_button.configure(fg_color="green")
            self.room_light_button.hover = False       
        else:
            # Turn off the light
            self.room_light.set_values([0])
            # Set button color to blue
            self.room_light_button.configure(fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"])
            self.room_light_button.hover = True



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
        self.spot_ctc           = self.qlc_input.add_channel(start=19, width=1) # CTC
        self.isi_ctc            = self.qlc_input.add_channel(start=20, width=1) # CTC
        self.qlc_init_channel    = self.qlc_input.add_channel(start=21, width=1) # Init-Button
        self.sequence_control   = self.qlc_input.add_channel(start=22, width=1) # Control the Sequence of Szene and ISI
        self.pixel2_7_intensity = self.qlc_input.add_channel(start=23, width=1) # Pixel 2-7 intensity
        self.light_intensity_reading = self.qlc_input.add_channel(start=24, width=1) # Reading light intensity
        self.room_light = self.qlc_input.add_channel(start=25, width=1) # Room light

    def activate_isi(self):
        self.sequence_control.set_values([255])
    
    def fade_isi(self):
        self.sequence_control.set_values([160])
    
    def activate_scene(self):
        self.sequence_control.set_values([96])
    
    def fade_scene(self):
        self.sequence_control.set_values([0])

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
        self.light_intensity_reading = self.qlc_input.add_channel(start=24, width=1) # Reading light intensity
        self.room_light = self.qlc_input.add_channel(start=25, width=1) # Room light

app = App()
app.async_mainloop()



