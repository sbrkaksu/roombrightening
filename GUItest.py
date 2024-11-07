import tkinter as tk
import customtkinter as ctk

import asyncio
from async_tkinter_loop import async_handler
from async_tkinter_loop.mixins import AsyncCTk

from websockets.asyncio import client as ws
from websockets import ConnectionClosed as ExceptionConnectionClosed

import requests

class App(ctk.CTk, AsyncCTk):
    def __init__(self):
        super().__init__()

        self.title("Studie Raumaufhellung")
        self.geometry("600x400")
        self.grid_columnconfigure((0, 1), weight=1)
        #self.grid_rowconfigure((0, 1), weight=1)


        # Build Frame to query if the lighting scene was bothering or not
        self.inquery_frame = ctk.CTkFrame(self)
        self.inquery_frame.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        self.inquery_label = ctk.CTkLabel(self.inquery_frame, text="Ist die Szene störend?").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.radio_var = tk.StringVar(value="")
        self.radio_yes = ctk.CTkRadioButton(self.inquery_frame, text="Ja (J)", command=self.radio_cb, variable=self.radio_var, value="Ja")
        self.radio_yes.grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.radio_yes.configure(state="disabled")
        self.radio_no = ctk.CTkRadioButton(self.inquery_frame, text="Nein (N)", command=self.radio_cb, variable=self.radio_var, value="Nein")
        self.radio_no.grid(row=2, column=0, padx=10, pady=10, sticky="w")
        self.radio_no.configure(state="disabled")

        self.button_next = ctk.CTkButton(self, text="Start (↵)", command=self.button_next_first_cb)
        self.button_next.grid(row=0, column=1, padx=10, pady=10, sticky="w")
        
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
        pass

app = App()
app.async_mainloop()