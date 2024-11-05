import tkinter
import customtkinter

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.title("my app")
        self.geometry("600x400")
        self.grid_columnconfigure((0, 1), weight=1)
        #self.grid_rowconfigure((0, 1), weight=1)


        # Build Frame to query if the lighting scene was bothering or not
        self.inquery_frame = customtkinter.CTkFrame(self)
        self.inquery_frame.grid(row=1, column=0, padx=10, pady=10, sticky="w")
        
        self.inquery_label = customtkinter.CTkLabel(self.inquery_frame, text="Ist die Szene störend?").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.radio_var = tkinter.StringVar(value="")
        self.radio_yes = customtkinter.CTkRadioButton(self.inquery_frame, text="Ja (J)", command=self.radio_cb, variable=self.radio_var, value="Ja")
        self.radio_yes.grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.radio_yes.configure(state="disabled")
        self.radio_no = customtkinter.CTkRadioButton(self.inquery_frame, text="Nein (N)", command=self.radio_cb, variable=self.radio_var, value="Nein")
        self.radio_no.grid(row=2, column=0, padx=10, pady=10, sticky="w")
        self.radio_no.configure(state="disabled")

        self.button_next = customtkinter.CTkButton(self, text="Start (↵)", command=self.button_next_first_cb)
        self.button_next.grid(row=1, column=1, padx=10, pady=10, sticky="w")
    
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
app.mainloop()