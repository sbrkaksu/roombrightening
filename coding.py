import os
import sys
import numpy as np
import customtkinter


seed = int.from_bytes(os.urandom(128), sys.byteorder)
rng = np.random.default_rng(seed)

scenes = {'Szenen': []}



app = customtkinter.CTk()
app.geometry("400x150")

i = 0
def random_scene():
    global i
    combination_factor = int(rng.integers(0,2))
    
    scenes['Szenen'].append({'Combination Factor': combination_factor})
    print(scenes['Szenen'][i])
    i += 1
    

button = customtkinter.CTkButton(app, text="+", command=random_scene)
button.pack(pady=10)

app.mainloop()

