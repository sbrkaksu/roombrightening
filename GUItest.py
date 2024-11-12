import tkinter as tk
import customtkinter as ctk

import asyncio
from async_tkinter_loop import async_handler
from async_tkinter_loop.mixins import AsyncCTk

from websockets.asyncio import client as ws
from websockets import ConnectionClosed as ExceptionConnectionClosed

import requests
import time

class App(ctk.CTk, AsyncCTk):
    def __init__(self):
        #self.root = root
        super().__init__()

        self.title("Studie Raumaufhellung")
        self.geometry("600x400")
        self.grid_columnconfigure((0, 1), weight=1)
        #self.grid_rowconfigure((0, 1), weight=1)


        # Build Frame to query if the lighting scene was bothering or not
        self.inquery_frame = ctk.CTkFrame(self)
        #self.inquery_frame.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        self.inquery_label = ctk.CTkLabel(self, text="Ist die Szene störend?").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.radio_var = tk.StringVar(value="")
        self.stoer_var = tk.StringVar(value="Nein")
        self.status_var = tk.StringVar(value="")
        self.reiz_size = tk.IntVar(value=3)
        self.isi_size = tk.IntVar(value=1)


        self.clock_label = ctk.CTkLabel(self, text="", font=("Helvetica", 30))
        self.clock_label.grid(row=3, column=3, padx=10, pady=20)
        self.status_label = ctk.CTkLabel(self, text="", font=("Helvetica", 30))
        self.status_label.grid(row=3, column=3, padx=10, pady=20)
        self.start_button = ctk.CTkButton(self, text="Start Countdown", command=lambda: self.countdown_timer(10))
       # self.start_button = ctk.CTkButton(self, text="Start", command=self.handle_action)
        self.start_button.grid(row=1, column=3, padx=10, pady=10, sticky="w")

        self.stoer_yes = ctk.CTkButton(self, text="Jo", command=self.radio_cb)
        self.stoer_yes.grid(row=1, column=0, padx=10, pady=10, sticky="w")

      #  self.button_next = ctk.CTkButton(self, text="Start (↵)", command=self.button_next_first_cb)
      #  self.button_next.grid(row=0, column=1, padx=10, pady=10, sticky="w")
        
        self.qlc_queue = asyncio.Queue(maxsize = 100)
        self.button_connect_qlc = ctk.CTkButton(self, text="Connect to QLC+", command=self.connect_qlc)
        self.button_connect_qlc.grid(row=1, column=1, padx=10, pady=10, sticky="w")

        self.dmx_channel = ctk.CTkEntry(self, placeholder_text="DMX Channel")
        self.dmx_channel.grid(row=2, column=0, padx=10, pady=10, sticky="w")
        self.dmx_value = ctk.CTkEntry(self, placeholder_text="DMX Value")
        self.dmx_value.grid(row=3, column=0, padx=10, pady=10, sticky="w")
        
        self.button_set_dmx_channel = ctk.CTkButton(self, text="Set DMX Channel",
                                                    command= lambda: self.set_dmx_channel(int(self.dmx_channel.get()),
                                                                                          int(self.dmx_value.get())))
        self.button_set_dmx_channel.grid(row=2, column=1, padx=10, pady=10, sticky="w")
        
        self.button_load_qlc_project = ctk.CTkButton(self, text="Load QLC+ Project", command= self.load_qlc_project)
        self.button_load_qlc_project.grid(row=3, column=1, padx=10, pady=10, sticky="w")
        

    def countdown_timer(self, seconds):
        if seconds > 0:
            mins, secs = divmod(seconds, 60)  # Minuten und Sekunden berechnen
            timer_format = f'{mins:02d}:{secs:02d}'
            self.clock_label.configure(text=timer_format)  # Timer-Wert im Label anzeigen
            self.after(1000, self.countdown_timer, seconds - 1)  # Countdown alle 1000ms aktualisieren
        else:
            self.clock_label.configure(text="abgelaufen!")

#    def handle_action(self, status):





    def load_qlc_project(self):
        filename = tk.filedialog.askopenfilename(filetypes=[("QLC+ files", "*.qxw"),("All files", "*.*")])
        with open(filename, 'rb') as f:
            r = requests.post('http://127.0.0.1:9999/loadProject', files={'qlcprj': f})

    @async_handler
    async def set_dmx_channel(self,channel,value):
        print("put in queue: ", "CH|{ch}|{v}".format(ch=channel, v=value))
        self.qlc_queue.put_nowait("CH|{ch}|{v}".format(ch=channel, v=value))
    
    @async_handler
    async def connect_qlc(self):
        # connect to QLC+ with auto-reconnect on connection closed
        async for qlcsocket in ws.connect('ws://localhost:9999/qlcplusWS'):
            self.button_connect_qlc.configure(fg_color="green")
            self.button_connect_qlc.configure(state="disabled")
            print("connected to QLC+")
            try:
                while True:
                    msg = await self.qlc_queue.get()
                    await qlcsocket.send(msg)
            except ExceptionConnectionClosed:
                continue
    
    
    def button_next_first_cb(self):
        self.radio_yes.configure(state="normal")
        self.radio_no.configure(state="normal")
        self.radio_var.trace("w", self.radio_var_cb)
        self.button_next.configure(text="nächste Szene (↵)")
        self.button_next.configure(command=self.button_next_cb)

    def button_next_cb(self):
        print("scene bothering? -> ", self.radio_var.get())
        self.radio_var.set("")
        
    def radio_var_cb(self, *args):
        if self.radio_var.get() == "":
            self.button_next.configure(state="disabled")
        else:
            self.button_next.configure(state="normal")
        
    def radio_cb(self):
        print("Knopf gedrückt")
        self.stoer_var.set("Ja")
        print("Variabel ->", self.stoer_var.get())


app = App()
app.async_mainloop()