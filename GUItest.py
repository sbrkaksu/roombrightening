import ast
import itertools
from collections import deque

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

class App(ctk.CTk, AsyncCTk):
    def __init__(self):
        super().__init__()
        ######## Setup the Window ########
        self.title("Studie Raumaufhellung")
        self.geometry("750x600")
        ##################################
        
        ######## Settings ########
        self.settings = {
            "qlc_address": 'localhost:9999',
            "szene_duration": 4.5, # seconds
            "inter-stimulus-interval": 2.5, #seconds
            "isi-fade-duration" : 0.6, # seconds. QLC fades in 300 ms
            "maxE_spot1": 143.0,
            "maxE_spot2": 92.2,
            "maxE_spot3": 164.6,
            "maxE_spot4": 72.2,
        }

        #self.grid_columnconfigure((0, 1), weight=1)
        #self.grid_rowconfigure((0, 1), weight=1)


        ######## Frame to simulate Input on Light Szene, bothering or not? ########
        self.inquery_frame = ctk.CTkFrame(self)
        self.inquery_frame.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        self.inquery_label = ctk.CTkLabel(self.inquery_frame, text="Ist die Szene störend?").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.stoer_var = tk.StringVar(value="Nein")
        self.stoer_button = ctk.CTkButton(self.inquery_frame, text="Jo", command=lambda: self.stoer_var.set("Ja"))
        self.stoer_button.grid(row=1, column=0, padx=10, pady=10, sticky="w")
        ###########################################################################
            
        self.proband = None
        self.active_scene = None
        self.active_scene_idx = None
        self.active_sequence = None
        
        ######## Frame to display the sequences in a table ########
        self.sequence_frame = ctk.CTkFrame(self)
        self.sequence_frame.grid(row=1, column=1, padx=10, pady=10, sticky="w")
        
        self.sequence_label = ctk.CTkLabel(self.sequence_frame, text="Durchgang", anchor="nw")
        self.sequence_label.grid(row=0, column=0, padx=0, pady=0)
        
        self.scene_label = ctk.CTkLabel(self, text="Szene")
        self.scene_label.grid(row=1, column=2, padx=10, pady=10, sticky="nw")
        
        self.sequence_table_header = CTkTable(self.sequence_frame, row=1, column=4, header_color='white', corner_radius=0, height =12, width=60)
        self.sequence_table_header.grid(row=1, column=0, padx=10, pady=0, sticky="n")
        self.sequence_table_header.update_values([["Szene", "Spot", "E","Störend"]])
        self.scene_rows = 10
        self.sequence_table = CTkTable(self.sequence_frame, row=self.scene_rows, column=4, corner_radius=0, height =12, width=60)
        self.sequence_table.grid(row=2, column=0, padx=10, pady=(0,10), sticky="n")
        hover_color = ctk.ThemeManager.theme["CTkButton"]["hover_color"]
        for i in range(self.sequence_table.rows):
            self.sequence_table.edit_row(row=i,hover_color = hover_color,
                                         command = lambda i=i: self.row_click(i))

        
        self.sequence_progressbar = ctk.CTkProgressBar(self.sequence_frame, orientation="vertical", mode = "determinate", width = 6)
        self.sequence_progressbar.grid(row=2, column=1, padx=0, pady=(0,1), sticky="nsw")
        self.sequence_progressbar.configure(corner_radius=0)
        # swap progressbar colors, so it "fills" from top to bottom
        self.sequence_progressbar.configure(progress_color=ctk.ThemeManager.theme["CTkProgressBar"]["fg_color"])
        self.sequence_progressbar.configure(fg_color=ctk.ThemeManager.theme["CTkProgressBar"]["progress_color"])
        self.sequence_progressbar.set(1)

        ######## Frame to control the sequence ########
        self.seq_crtl_frame = ctk.CTkFrame(self)
        self.seq_crtl_frame.grid(row=1, column=0, padx=10, pady=10, sticky="wn")
        self.load_proband_button = ctk.CTkButton(self.seq_crtl_frame, text="Proband laden", command=self.load_proband)
        self.load_proband_button.grid(row=0, column=0, padx=10, pady=10, sticky="n")
        self.sequence_start_reset_button = ctk.CTkButton(self.seq_crtl_frame, text="Durchgang starten", command=self.run_sequence, state="disabled")
        self.sequence_start_reset_button.grid(row=2, column=0, padx=10, pady=10, sticky="s")
        
        self.sequence_stop_continue_button = ctk.CTkButton(self.seq_crtl_frame, text="Durchgang anhalten", command=self.stop_sequence, state="disabled")
        self.sequence_stop_continue_button.grid(row=3, column=0, padx=10, pady=10, sticky="s")
        
        self.sequence_stop_event = asyncio.Event()
        self.sequence_continue_event = asyncio.Event()

        self.seq_switch_frame = ctk.CTkFrame(self.seq_crtl_frame, fg_color="transparent")
        self.seq_switch_frame.grid(row=1, column=0, padx=0, pady=0, sticky="wn")
        self.next_seq_button = ctk.CTkButton(self.seq_switch_frame, text=">", width=60, command=self.next_sequence)
        self.next_seq_button.grid(row=0, column=1, padx=10, pady=10, sticky="e")
        self.prev_seq_button = ctk.CTkButton(self.seq_switch_frame, text="<", width=60, command=self.prev_sequence)
        self.prev_seq_button.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        ########   Countdown Timer  ########
        self.scene_countdown_timer =  tk.DoubleVar()
        self.scene_countdown_timer.trace_add('write', self.print_scene_countdown)
        self.scene_countdown_end = 0.0
        self.scene_countdown_finished = asyncio.Event()
        self.scene_countdown_label = ctk.CTkLabel(self, text="", font=("Helvetica", 30))
        self.scene_countdown_label.grid(row=1, column=3, padx=10, pady=20)
        
        ########    QLC+ Control    ########
        self.button_connect_qlc = ctk.CTkButton(self, text="QLC initialisieren", command=self.init_qlc)
        self.button_connect_qlc.grid(row=1, column=2, padx=10, pady=10, sticky="nw")
        self.project_loaded = False

        ########    User Input Key  ########
        self.szene_disturbing_key_event = asyncio.Event()
        self.bind("y", self.disturbing_key_pressed)
        
    def disturbing_key_pressed(self):
        self.szene_disturbing_key_event.set()
        if self.active_scene is not None:
            self.active_scene["Stoert"] = "Ja"

    def row_click(self,row_idx):
        if self.sequence_stop_event.is_set():
            self.sequence_table.deselect_row(self.active_scene_idx)
            self.active_scene_idx = row_idx
            self.sequence_table.select_row(self.active_scene_idx)

    def load_qlc_project(self):
        r = False
        try:
            filename = tk.filedialog.askopenfilename(filetypes=[("QLC+ files", "*.qxw"),("All files", "*.*")])
            with open(filename, 'rb') as f:
                r = requests.post("http://{add}/loadProject".format(add = self.settings["qlc_address"]), files={'qlcprj': f})
            r = True
        finally:
            return r

    def load_proband(self):
        filename = tk.filedialog.askopenfilename(filetypes=[("Text file", "*.txt"),("All files", "*.*")])
        with open(filename, 'r') as f:
            s = f.read()
            self.proband = ast.literal_eval(s)
        self.seq_num = len(self.proband["Durchgange"])
        self.seq_idx = 0
        self.set_sequence()
        self.sequence_start_reset_button.configure(state="normal")
        
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
        seq_values = [[s["ID"],s["Spot"],s["E"]] for s in self.active_sequence["Szenen"]]
        
        # setup table: fill with values
        self.sequence_table.update_values(seq_values)
        
        self.sequence_label.configure(text="Durchgang {id}".format(id=self.active_sequence["ID"]))
    
    
    def stop_sequence(self):
        self.sequence_stop_continue_button.configure(text="Durchgang fortsetzen",
                                                  command=self.continue_sequence,
                                                  fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"])
        self.sequence_stop_event.set()
    

    def continue_sequence(self):
        self.sequence_stop_continue_button.configure(text="Durchgang anhalten",
                                                  command=self.stop_sequence,
                                                  fg_color="red")
        self.sequence_continue_event.set()
        
    def reset_sequence(self):
        self.sequence_task.cancel()
    
    def deselect_table(self):
        for i in range(self.sequence_table.rows):
            self.sequence_table.deselect_row(i)
    # evaluate if button was pressed (for previous scene)
    #self.sequence_stop_event.is_set() 
    #self.szene_disturbing_key_event.is_set():
    #self.sequence_table.insert(scene_idx, 3, "Ja")
    #self.szene_disturbing_key_event.clear()
    #self.sequence_table.insert(scene_idx, 3, "Nein")
    async def run_sequence_task(self):
        try:
            # switch button to stop sequence
            self.sequence_stop_continue_button.configure(state='normal',fg_color="red")
            self.sequence_start_reset_button.configure(text="Durchgang zurücksetzen", command=self.reset_sequence)

            scenes = self.active_sequence["Szenen"]
            scene_num = len(scenes)
            
            # prepare first scene
            isi_duration = self.settings["inter-stimulus-interval"]
            isi_fade_duration = self.settings["isi-fade-duration"]

            self.set_scene(scenes[0])
            self.sequence_table.select_row(0)
            #self.scene_label.configure(text="Szene {id}/{num}".format(id=scene["ID"], num=scene_num))
            self.fade_isi()
            await asyncio.sleep(isi_fade_duration)

            cur_next_scenes = [cur_next for cur_next in itertools.pairwise([*scenes,None])]
            self.active_scene_idx = 0
            while self.active_scene_idx < (scene_num):
                scene,next_scene  = cur_next_scenes[self.active_scene_idx]
                #self.active_scene = scene
                self.sequence_table.select_row(self.active_scene_idx)
                self.scene_label.configure(text="Szene {id}/{num}".format(id=scene["ID"], num=scene_num))

                self.activate_scene()
                self.szene_disturbing_key_event.clear()
                await self.await_countdown_timer(self.settings["szene_duration"])
                
                # set inter-stimulus lighting
                self.activate_isi()
                
                await self.await_countdown_timer(isi_duration,isi_fade_duration)
                if self.sequence_stop_event.is_set(): # if stopped, keep interstimulus lighting
                    await self.sequence_continue_event.wait() # wait for continue event
                    self.sequence_continue_event.clear()
                    self.sequence_stop_event.clear()
                    scene,_  = cur_next_scenes[self.active_scene_idx] # update scene, in case different index was chosen
                    self.set_scene(scene)
                    self.fade_isi()
                    await asyncio.sleep(isi_fade_duration)
                    continue

                self.set_scene(next_scene) # prepare scene values
                self.fade_isi()
                await self.await_countdown_timer() # count down rest of the timer
                if self.sequence_stop_event.is_set():
                    print("continue from isi fade")
                    continue
                self.sequence_table.deselect_row(self.active_scene_idx)
                self.active_scene_idx += 1
        finally:
            self.activate_isi()
            self.deselect_table()
            self.sequence_start_reset_button.configure(text="Durchgang starten", command=self.run_sequence)
            self.sequence_stop_continue_button.configure(text="Durchgang anhalten", command=self.stop_sequence,
                                                        state="disabled", fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"])
            self.sequence_stop_event.clear()
            self.scene_label.configure(text="Szene")
            self.scene_countdown_timer.set(0)
            

    @async_handler
    async def run_sequence(self):
        self.sequence_task = asyncio.create_task(self.run_sequence_task(), name="run_sequence")
        await self.sequence_task
            

    def print_scene_countdown(self, *args):
        self.scene_countdown_label.configure(text="{:04.1f}".format(self.scene_countdown_timer.get()))
    
    async def await_countdown_timer(self, start_time = None, end_time = None):
        if(end_time == None):
            end_time = 0
        self.scene_countdown_end = end_time
        self.scene_countdown_finished.clear()
        if(start_time != None):
            self.scene_countdown_timer.set(start_time)
        self.after(100, self.countdown_timer_cb) # starts the timer
        await asyncio.wait(
            [asyncio.create_task(self.scene_countdown_finished.wait()),
             asyncio.create_task(self.sequence_stop_event.wait())],return_when=asyncio.FIRST_COMPLETED)
        if self.sequence_stop_event.is_set():
            self.scene_countdown_timer.set(0) # reset to zero
        else:
            self.scene_countdown_timer.set(self.scene_countdown_end) # leave it at end_time

    def countdown_timer_cb(self):
        timer_value = self.scene_countdown_timer.get()
        timer_value -= 0.1
        if timer_value > self.scene_countdown_end:
            self.scene_countdown_timer.set(round(timer_value,1))
            self.after(100, self.countdown_timer_cb)  # Countdown alle 100ms dekrementieren
        else:
            self.scene_countdown_finished.set()

    @async_handler
    async def init_qlc(self):
        if self.project_loaded == False:
            self.project_loaded = self.load_qlc_project()
        if self.project_loaded == False:
            return
        
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
        self.qlc_init_button    = self.qlc_input.add_channel(start=21, width=1) # Init-Button
        self.sequence_control   = self.qlc_input.add_channel(start=22, width=1) # Control the Sequence of Szene and ISI
        await asyncio.sleep(1) # wait for project to load
        self.qlc_init_button.set_values([255])
        self.set_all_intensities(0)
        self.set_isi()
        self.spot_color.set_values([255,255,255,255])
        await asyncio.sleep(1) # wait for project to load
        self.activate_isi()
    
    def activate_isi(self):
        self.sequence_control.set_values([255])
    
    def fade_isi(self):
        self.sequence_control.set_values([127])
    
    def activate_scene(self):
        self.sequence_control.set_values([0])
    
    def set_scene(self, scene):
        self.set_all_intensities(0)
        dmx_max = 2**16 - 1
        
        spot = scene["Spot"]
        print("setting spot", spot)
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

    def set_all_intensities(self,i):
        self.spot1_intensity.set_values(i.to_bytes(2,'big'))
        self.spot2_intensity.set_values(i.to_bytes(2,'big'))
        self.spot3_intensity.set_values(i.to_bytes(2,'big'))
        self.spot4_intensity.set_values(i.to_bytes(2,'big'))

    def set_isi(self):
        brightness = 2500
        self.isi_intensity.set_values(brightness.to_bytes(2,'big'))
        self.isi_color.set_values([255,0,0,0])

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
        self.qlc_init_button    = self.qlc_input.add_channel(start=21, width=1) # Init-Button
        self.sequence_control   = self.qlc_input.add_channel(start=22, width=1) # Control the Sequence of Szene and ISI


app = App()
app.async_mainloop()

proband = {
            "ID": 1,
            "Durchgange":[
                {
                    "ID" : 1,
                    "Matt": False,
                    "Szenen" : [
                        {"ID": 1, "Spot" : 1, "E" : 30},
                        {"ID": 2, "Spot" : 2, "E" : 1},
                        {"ID": 3, "Spot" : 1, "E" : 6},
                        {"ID": 4, "Spot" : 2, "E" : 0.1},
                        {"ID": 5, "Spot" : 4, "E" : 30},
                        {"ID": 6, "Spot" : 4, "E" : 100}
                        ]
                },
                {
                    "ID" : 2,
                    "Matt": False,
                    "Szenen" : [
                        {"ID": 1, "Spot" : 1, "E" : 30},
                        {"ID": 2, "Spot" : 3, "E" : 1},
                        {"ID": 3, "Spot" : 4, "E" : 6},
                        {"ID": 4, "Spot" : 2, "E" : 0.3},
                        {"ID": 5, "Spot" : 4, "E" : 10},
                        {"ID": 6, "Spot" : 3, "E" : 60}
                        ]
                },
                {
                    "ID" : 3,
                    "Matt": True,
                    "Szenen" : [
                        {"ID": 1, "Spot" : 4, "E" : 30},
                        {"ID": 2, "Spot" : 2, "E" : 1},
                        {"ID": 3, "Spot" : 4, "E" : 6},
                        {"ID": 4, "Spot" : 2, "E" : 0.1},
                        {"ID": 5, "Spot" : 4, "E" : 30},
                        {"ID": 6, "Spot" : 1, "E" : 100}
                        ]
                }
            ]
        }

