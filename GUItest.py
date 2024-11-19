import ast

import tkinter as tk
import customtkinter as ctk

import asyncio
from async_tkinter_loop import async_handler
from async_tkinter_loop.mixins import AsyncCTk
import async_timer
# maybe use uvloop (fast / more time-accurate event loop)


from CTkMenuBar import CTkTitleMenu
from CTkTable import CTkTable

from websockets.asyncio import client as ws
from websockets import ConnectionClosed as ExceptionConnectionClosed

import requests


import numpy as np

class App(ctk.CTk, AsyncCTk):
    def __init__(self):
        super().__init__()
        ######## Setup the Window ########
        self.title("Studie Raumaufhellung")
        self.geometry("750x700")
        ##################################
        
        ######## Settings ########
        self.settings = {
            "szene_duration": 2.7, # seconds
            "inter-stimulus-interval": 2.0, #seconds
            "maxE_spot1": 143,
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
        self.scene_rows = 16
        self.sequence_table = CTkTable(self.sequence_frame, row=self.scene_rows, column=4, corner_radius=0, height =12, width=60)
        self.sequence_table.grid(row=2, column=0, padx=10, pady=(0,10), sticky="n")
        
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
        
        
        ######## Countdown Timer ########
        self.scene_countdown_timer =  tk.DoubleVar()
        self.scene_countdown_timer.trace_add('write', self.print_scene_countdown)
        self.scene_countdown_finished = asyncio.Event()
        self.scene_countdown_label = ctk.CTkLabel(self, text="", font=("Helvetica", 30))
        self.scene_countdown_label.grid(row=2, column=3, padx=10, pady=20)
        
        self.qlc_queue = asyncio.Queue(maxsize = 100)
        self.button_connect_qlc = ctk.CTkButton(self, text="Connect & Initialize", command=self.connect_qlc)
        self.button_connect_qlc.grid(row=1, column=2, padx=10, pady=10, sticky="nw")

        self.dmx_channel = ctk.CTkEntry(self, placeholder_text="DMX Channel")
        self.dmx_channel.grid(row=2, column=0, padx=10, pady=10, sticky="w")
        self.dmx_value = ctk.CTkEntry(self, placeholder_text="DMX Value")
        self.dmx_value.grid(row=3, column=0, padx=10, pady=10, sticky="w")
        
        self.button_set_dmx_channel = ctk.CTkButton(self, text="Set DMX Channel",
                                                    command= lambda: self.set_dmx_channel(int(self.dmx_channel.get()),
                                                                                          int(self.dmx_value.get())))
        self.button_set_dmx_channel.grid(row=2, column=2, padx=10, pady=10, sticky="w")
        
       # self.button_load_qlc_project = ctk.CTkButton(self, text="Load QLC+ Project", command= self.load_qlc_project)
       # self.button_load_qlc_project.grid(row=3, column=2, padx=10, pady=10, sticky="w")

    def load_qlc_project(self):
        filename = tk.filedialog.askopenfilename(filetypes=[("QLC+ files", "*.qxw"),("All files", "*.*")])
        with open(filename, 'rb') as f:
            r = requests.post('http://127.0.0.1:9999/loadProject', files={'qlcprj': f})
    
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
            self.sequence = self.proband["Durchgange"][self.seq_idx]
        seq_values = [[s["ID"],s["Spot"],s["E"]] for s in self.sequence["Szenen"]]
        
        self.sequence_table.update_values(seq_values)
        self.sequence_label.configure(text="Durchgang {id}".format(id=self.sequence["ID"]))
    
    
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
        for i in range(len(self.sequence["Szenen"])):
            self.sequence_table.deselect_row(i)
    
    async def run_sequence_task(self):
        try:
            # switch button to stop sequence
            self.sequence_stop_continue_button.configure(state='normal',fg_color="red")
            self.sequence_start_reset_button.configure(text="Durchgang zurücksetzen", command=self.reset_sequence)
            scene_num = len(self.sequence["Szenen"])
            
            for scene_idx, scene in enumerate(self.sequence["Szenen"]):
                next_scene = False
                while not next_scene:
                    # set scene label
                    self.sequence_table.select_row(scene_idx)
                    self.scene_label.configure(text="Szene {id}/{num}".format(id=scene["ID"], num=scene_num))
                    # highlight scene row in table
                    # set scene DMX values
                    self.set_scene(scene)
                    # wait for scene duration
                    
                    await self.await_countdown_timer(self.settings["szene_duration"])

                    # set inter-stimulus lighting
                    print("setting inter-stimulus lighting...")
                    self.isi_red_all()


                    # wait for inter-stimulus interval
                    await self.await_countdown_timer(self.settings["inter-stimulus-interval"])
                    if self.sequence_stop_event.is_set(): # if stopped, keep interstimulus lighting
                        await self.sequence_continue_event.wait() # wait for continue event
                        self.sequence_continue_event.clear()
                        self.sequence_stop_event.clear()
                        continue
                    next_scene = True
                    self.sequence_table.deselect_row(scene_idx)
                    # evaluate if button was pressed
                    # use a asyncio Event
        finally:
            self.deselect_table()
            self.sequence_start_reset_button.configure(text="Durchgang starten", command=self.run_sequence)
            self.sequence_stop_continue_button.configure(text="Durchgang anhalten", command=self.stop_sequence,
                                                        state="disabled", fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"])
            self.sequence_stop_event.clear()
            self.scene_label.configure(text="Szene")
            self.scene_countdown_timer.set(0)
            self.sequence_stop_continue_button.configure(state="disabled")
            self.sequence_start_reset_button.configure(state="normal")

    @async_handler
    async def run_sequence(self):
        self.sequence_task = asyncio.create_task(self.run_sequence_task(), name="run_sequence")
        await self.sequence_task
            

    def print_scene_countdown(self, *args):
        self.scene_countdown_label.configure(text="{:04.1f}".format(self.scene_countdown_timer.get()))
        
    def set_progressbar(self, *args):
        pass
        #self.scene_rows
        #self.scene_countdown_timer.get()
        #self.scene_idx
        #self.sequence_progressbar.set(1-)
        
    def countdown_timer(self):
        timer_value = self.scene_countdown_timer.get()
        timer_value -= 0.1
        if timer_value > 0:
            self.scene_countdown_timer.set(np.round(timer_value,decimals=1))
            self.after(100, self.countdown_timer)  # Countdown alle 100ms aktualisieren
        else:
            self.scene_countdown_finished.set()

    async def await_countdown_timer(self, time):
        self.scene_countdown_finished.clear()
        self.scene_countdown_timer.set(time)
        self.after(100, self.countdown_timer) # starts the timer
        await asyncio.wait(
            [asyncio.create_task(self.scene_countdown_finished.wait()),
             asyncio.create_task(self.sequence_stop_event.wait())],return_when=asyncio.FIRST_COMPLETED)
        self.scene_countdown_timer.set(0)
        

    def set_dmx_channel(self,channel,value):
        self.qlc_queue.put_nowait("CH|{ch}|{v}".format(ch=channel, v=value))
        #print("habe DMX Wert gesetzt")
    

    def set_qlc_widget(self,id,value):
        self.qlc_queue.put_nowait("{id}|{val}".format(id=id, val=value))
        print("Moving Heads Positionen gesetzt")
    
    def step_cue_list(self,id,index):
        self.qlc_queue.put_nowait("{id}|STEP|{idx}".format(id=id, idx=index))
    
    @async_handler
    async def connect_qlc(self):
        # connect to QLC+ with auto-reconnect on connection closed
        async for qlcsocket in ws.connect('ws://localhost:9999/qlcplusWS'):
            self.button_connect_qlc.configure(fg_color="green")
            self.button_connect_qlc.configure(state="disabled")
            print("connected to QLC+")
            self.load_qlc_project()
            self.set_qlc_widget(0,255) #Initialize Movingheads positions
            try:
                while True:
                    msg = await self.qlc_queue.get()
                    await qlcsocket.send(msg)
            except ExceptionConnectionClosed:
                continue
            
    def set_scene(self, scene):
        self.blackout_all()
        dmx_max = 65535
        spot = scene["Spot"]
        if spot == 1:
            maxE = self.settings["maxE_spot1"]
            dmx_channel_grob = 5
            dmx_channel_fein = 6
            dmx_channel_green = 13
            dmx_channel_blue = 14
            dmx_channel_lime = 15
            print("Spot1")

        elif spot == 2: 
            maxE = self.settings["maxE_spot2"]
            dmx_channel_grob = 517
            dmx_channel_fein = 518
            dmx_channel_green = 525
            dmx_channel_blue = 526
            dmx_channel_lime = 527
            print("Spot2")

        elif spot == 3:
            maxE = self.settings["maxE_spot3"]
            dmx_channel_grob = 1029
            dmx_channel_fein = 1030
            dmx_channel_green = 1037
            dmx_channel_blue = 1038
            dmx_channel_lime = 1039
            print("Spot3")

        elif spot == 4:
            maxE = self.settings["maxE_spot4"]
            dmx_channel_grob = 1541
            dmx_channel_fein = 1542
            dmx_channel_green = 1549
            dmx_channel_blue = 1550
            dmx_channel_lime = 1551
            print("Spot4")

        dmx_val = np.round((scene["E"] / maxE) * dmx_max).astype('int')
        dmx_val_fein = dmx_val & 0xFF
        dmx_val_grob = dmx_val >> 8

        print(scene["E"])
        print(f"Grober DMX-Wert: {dmx_val_grob}, Feiner DMX-Wert: {dmx_val_fein}")

        self.set_dmx_channel(dmx_channel_green, 255)
        self.set_dmx_channel(dmx_channel_blue, 255)
        self.set_dmx_channel(dmx_channel_lime, 255)
        self.set_dmx_channel(dmx_channel_grob, dmx_val_grob)
        self.set_dmx_channel(dmx_channel_fein, dmx_val_fein)


    def blackout_all(self):
        self.set_dmx_channel(5, 0)
        self.set_dmx_channel(6, 0)
        self.set_dmx_channel(517, 0)
        self.set_dmx_channel(518, 0)
        self.set_dmx_channel(1029, 0)
        self.set_dmx_channel(1030, 0)
        self.set_dmx_channel(1541, 0)
        self.set_dmx_channel(1542, 0)
        print("Alle Schweinwerfer Helligkeit 0")

    def isi_red_all(self):
        brightness = 10

        self.set_dmx_channel(5, brightness)
        self.set_dmx_channel(6, 0)
        self.set_dmx_channel(13, 0)
        self.set_dmx_channel(14, 0)
        self.set_dmx_channel(15, 0)

        self.set_dmx_channel(517, brightness)
        self.set_dmx_channel(518, 0)
        self.set_dmx_channel(525, 0)
        self.set_dmx_channel(526, 0)
        self.set_dmx_channel(527, 0)

        self.set_dmx_channel(1029, brightness)
        self.set_dmx_channel(1030, 0)
        self.set_dmx_channel(1037, 0)
        self.set_dmx_channel(1038, 0)
        self.set_dmx_channel(1039, 0)

        self.set_dmx_channel(1541, brightness)
        self.set_dmx_channel(1542, 0)
        self.set_dmx_channel(1549, 0)
        self.set_dmx_channel(1550, 0)
        self.set_dmx_channel(1551, 0)
        print("Alle Schweinwerfer Rot Helligkeit 10")

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