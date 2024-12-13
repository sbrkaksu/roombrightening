import serial
import time
import tkinter as tk
from tkinter import ttk
import re
import arrow


class SensorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Sensor Messwert")

        # Serielle Verbindung konfigurieren
        self.ser = serial.Serial(
            port='COM3',       # COM-Port des Geräts
            baudrate=9600,     # Baudrate
            timeout=2          # Timeout für die Verbindung (in Sekunden)
        )

        # GUI-Komponenten
        self.output_label = ttk.Label(root, text="Messwert von Sensor 1 wird hier angezeigt")
        self.output_label.pack(pady=10)

        self.read_button = ttk.Button(root, text="S1 Befehl senden", command=self.read_sensor)
        self.read_button.pack(pady=10)

        self.close_button = ttk.Button(root, text="Beenden", command=self.close_program)
        self.close_button.pack(pady=10)

    def read_sensor(self):
        try:
            if not self.ser.is_open:
                self.ser.open()

            self.ser.reset_input_buffer()
            while self.ser.in_waiting > 0:
                self.ser.read(self.ser.in_waiting)
            
            # Sende den Befehl "S1"
            command = "S1\r\n"
            self.ser.write(command.encode('utf-8'))

            time.sleep(0.1)

            # Lese die Antwort
            response = self.ser.readlines()

            if response:
                # Versuche, die Antwort zu dekodieren
                try:
                    decoded_response = "\n".join([line.decode('latin-1').strip() for line in response])
                except UnicodeDecodeError as e:
                    print(f"UnicodeDecodeError: {e}")
                    decoded_response = "Dekodierung fehlgeschlagen, Rohdaten siehe Konsole."
                
                # Parse die Antwort
                realtime, lux, temp = self.parse_sensor_output(decoded_response)

                # Zeige die Ergebnisse in der GUI an
                self.output_label.config(
                    text=f"Messzeit: {realtime}\nLux: {lux}\nTemperatur: {temp}"
                )

                # Debugging-Ausgabe
                print(response)
                print(decoded_response)
                print(f"Messzeit: {realtime}, Lux: {lux}, Temperatur: {temp}")
            else:
                self.output_label.config(text="Keine Antwort erhalten")

        except serial.SerialException as e:
            self.output_label.config(text=f"Fehler: {e}")

    def parse_sensor_output(self, output):
        # Muster für die Zeit, Lux-Wert (hinter "00") und Temperatur (hinter "04")
        time_pattern = r"^(\d{2}:\d{2}:\d{2})"
        lux_pattern = r"00: \+([-\d.]+) lx"
        temp_pattern = r"04: \+([-\d.]+) øC"

        # Extrahiere die Zeit mit Arrow
        realtime_match = re.search(time_pattern, output)
        if realtime_match:
            try:
                # Parse die Zeit mit Arrow
                realtime = arrow.get(realtime_match.group(1), "HH:mm:ss").format("HH:mm:ss")
            except Exception as e:
                print(f"Fehler beim Parsen der Uhrzeit: {e}")
                realtime = None
        else:
            realtime = None

        # Extrahiere Lux und Temperatur
        lux_match = re.search(lux_pattern, output)
        temp_match = re.search(temp_pattern, output)

        lux = lux_match.group(1) if lux_match else None
        temp = temp_match.group(1) if temp_match else None

        return realtime, lux, temp


    def close_program(self):
        # Serielle Verbindung schließen und Programm beenden
        if self.ser.is_open:
            self.ser.close()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    gui = SensorGUI(root)
    root.mainloop()
