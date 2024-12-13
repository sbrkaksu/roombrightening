import serial
import time

def read_sensor():
    # Konfiguriere die serielle Verbindung
    ser = serial.Serial(
        port='COM3',       # COM-Port des Geräts
        baudrate=9600,     # Baudrate
        timeout=1          # Timeout für die Verbindung (in Sekunden)
    )

    try:
        # Öffne die Verbindung, falls nicht bereits geöffnet
        if not ser.is_open:
            ser.open()

        # Sende den Befehl "S1", um den Wert von Sensor 1 anzufordern
        command = "S1\r\n"  # "\r\n" für einen Zeilenumbruch, falls erforderlich
        ser.write(command.encode('utf-8'))
        
        # Warte kurz, um sicherzustellen, dass das Gerät antworten kann
        time.sleep(0.1)

        # Lese die Antwort
        response = ser.readlines()  # Liest alle Zeilen, die verfügbar sind
        

        # Gib den empfangenen Wert aus
        print(f"Messwert von Sensor 1: {response}")

    except serial.SerialException as e:
        print(f"Fehler beim Zugriff auf die serielle Schnittstelle: {e}")
    finally:
        # Schließe die serielle Verbindung
        if ser.is_open:
            ser.close()

if __name__ == "__main__":
    read_sensor()
