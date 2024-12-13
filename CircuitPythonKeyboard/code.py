import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode

import board
import digitalio
import time

# Initialisiere die Tastatur
kbd = Keyboard(usb_hid.devices)

# Konfiguriere den Button-Pin
button = digitalio.DigitalInOut(board.GP0)
button.switch_to_input(pull=digitalio.Pull.DOWN)

# Konfiguriere den LED-Pin als Open-Drain
led = digitalio.DigitalInOut(board.GP7)
led.switch_to_output(drive_mode=digitalio.DriveMode.OPEN_DRAIN)
led.value = True  # LED aus (Open-Drain: High bedeutet aus)

# Variable für den Button-Zustand
button_pressed_state = False  # Ob der Button gerade gedrückt ist
last_debounce_time = 0  # Zeitpunkt der letzten Zustandsänderung
debounce_delay = 0.05  # Entprellzeit in Sekunden (50 ms)

# Timer für LED-Steuerung
led_active = False  # Ob die LED aktuell aktiv sein sollte
led_timer_start = 0  # Zeitpunkt, zu dem die LED aktiviert wurde
led_on_duration = 0.3  # Dauer (in Sekunden), für die die LED eingeschaltet wird


def send_keypress():
    """Funktion, die ausgeführt wird, wenn der Button gedrückt wird."""
    kbd.send(Keycode.H)
    kbd.send(Keycode.I)
    kbd.send(Keycode.L)
    kbd.send(Keycode.F)
    kbd.send(Keycode.E)


while True:
    # Lese den aktuellen Zustand des Buttons
    current_button_state = button.value

    # Aktuelle Zeit abrufen
    current_time = time.monotonic()

    # Prüfen, ob der Zustand sich geändert hat und Entprellzeit abgelaufen ist
    if current_button_state != button_pressed_state:
        if current_time - last_debounce_time > debounce_delay:
            button_pressed_state = current_button_state
            last_debounce_time = current_time

            # Wenn der Button gerade gedrückt wurde
            if button_pressed_state:  # True = Button wird gedrückt
                send_keypress()

                # LED für 1 Sekunde einschalten
                led_active = True
                led_timer_start = current_time
                led.value = False  # LED an (Open-Drain: Low bedeutet an)

    # Überprüfen, ob die LED ausgeschaltet werden soll
    if led_active and current_time - led_timer_start >= led_on_duration:
        led.value = True  # LED aus (Open-Drain: High bedeutet aus)
        led_active = False

    # Kleine Pause, um die CPU-Last zu reduzieren
    time.sleep(0.01)
