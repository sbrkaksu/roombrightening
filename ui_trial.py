import customtkinter
import asyncio
from async_tkinter_loop import async_handler
import sys
from Formatter import printer
from ast import literal_eval

steps_E_values = [ 0.01, 0.0147, 0.0215, 0.0316, 0.0464, 0.0681, 
                          0.1, 0.147, 0.215, 0.316, 0.464, 0.681, 
                          1.0, 1.47, 2.15, 3.16, 4.64, 6.81, 
                          10.0, 14.7, 21.5, 31.6, 46.4, 68.1, 
                          100.0, 147.0, 215.0, 316.0]

  #'{:.4e}'.format(3.14159) = '3.1416e+00' - formats E


formatted_E = printer.pformat(3.1600e+02)
#printer.pformat(steps_E_values)
print(literal_eval(formatted_E) + 5)  # prints the formatted list of floats