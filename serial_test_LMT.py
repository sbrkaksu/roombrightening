import serial
import re

# Einstellungen für den seriellen Port
port = 'COM3'
baudrate = 9600

# Regulärer Ausdruck für gültige Werte (Exponent muss E-0x sein)
value_pattern = re.compile(r'[+-]\d+\.\d+ E[+-]\d\d')

try:
    with serial.Serial(port, baudrate, timeout=1) as ser:
        print(f"Verbunden mit {port}. Warte auf Initialisierung...")
        time.sleep(2)  # Warten, bis das Gerät bereit ist
        
        # DTR dauerhaft aktiv setzen
        ser.dtr = True
        print("DTR gesetzt. Warte auf Daten...\n")
        raw_text = ''
        while True:
            if ser.in_waiting > 0:  # Prüfen, ob Daten verfügbar sind
                raw_text += ser.read(ser.in_waiting).decode('ascii')  # Alle verfügbaren Bytes 
                while True:
                    match = value_pattern.search(raw_text)
                    if match:
                        raw_text = raw_text[match.end():]
                        print(float(match.group().replace(' ', '')))
                        print(match.string)
                    else:
                        break
                

except serial.SerialException as e:
    print(f"Fehler beim Zugriff auf {port}: {e}")
except KeyboardInterrupt:
    print("\nProgramm beendet.")
