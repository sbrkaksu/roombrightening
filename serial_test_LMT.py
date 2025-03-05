import serial
import time
import re

# Einstellungen für den seriellen Port
port = 'COM3'
baudrate = 9600

# Regulärer Ausdruck für gültige Werte (Exponent muss E-0x sein)
value_pattern = re.compile(r'[+-]\d+\.\d+ E-0\d')

try:
    with serial.Serial(port, baudrate, timeout=1) as ser:
        print(f"Verbunden mit {port}. Warte auf Initialisierung...")
        time.sleep(2)  # Warten, bis das Gerät bereit ist
        
        # DTR dauerhaft aktiv setzen
        ser.dtr = True
        print("DTR gesetzt. Warte auf Daten...\n")
        
        while True:
            if ser.in_waiting > 0:  # Prüfen, ob Daten verfügbar sind
                raw_data = ser.read(ser.in_waiting)  # Alle verfügbaren Bytes lesen
                raw_text = raw_data.decode('utf-8', errors='ignore')  # Ignoriere fehlerhafte Bytes
                
                matches = value_pattern.findall(raw_text)  # Nur gültige Werte finden
                for match in matches:
                    print(f"Gefundener gültiger Messwert: {match}")  # Gültigen Wert ausgeben
except serial.SerialException as e:
    print(f"Fehler beim Zugriff auf {port}: {e}")
except KeyboardInterrupt:
    print("\nProgramm beendet.")
