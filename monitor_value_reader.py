import argparse
import asyncio
import msvcrt
from time import monotonic
from re import compile

import serial


DEFAULT_PORT = "COM3"
DEFAULT_BAUD_RATE = 9600
DEFAULT_PRINT_INTERVAL_SECONDS = 0.5


MONITOR_VALUE_PATTERN = compile(r"[+-]\d+\.\d+ E[+-]\d\d")


def update_printing_enabled(printing_enabled):
    if not msvcrt.kbhit():
        return printing_enabled

    key = msvcrt.getch()
    if key not in (b"\x00", b"\xe0"):
        return printing_enabled

    arrow_key = msvcrt.getch()
    if arrow_key == b"P":
        if printing_enabled:
            print("Printing paused. Press Up arrow to continue.")
        return False
    if arrow_key == b"H":
        if not printing_enabled:
            print("Printing resumed. Press Down arrow to pause.")
        return True

    return printing_enabled


async def read_monitor_continuously(port, baud_rate, print_interval):
    latest_monitor_value = None
    latest_raw_value = None
    last_print_time = 0
    printing_enabled = True

    try:
        with serial.Serial(port, baud_rate, timeout=0) as ser:
            ser.dtr = True
            raw_text = ""

            print(f"Reading monitor on {port} at {baud_rate} baud.")
            print(f"Printing every {print_interval} s.")
            print("Down arrow pauses printing. Up arrow resumes printing.")
            print("Press Ctrl+C to stop.\n")

            while True:
                printing_enabled = update_printing_enabled(printing_enabled)

                chunk_bytes = ser.read(ser.in_waiting)
                if chunk_bytes:
                    chunk = chunk_bytes.decode("ascii", errors="ignore")
                    raw_text += chunk

                    while True:
                        match = MONITOR_VALUE_PATTERN.search(raw_text)
                        if not match:
                            break

                        raw_value = match.group()
                        raw_text = raw_text[match.end():]

                        latest_monitor_value = float(raw_value.replace(" ", ""))
                        latest_raw_value = raw_value

                now = monotonic()
                if (
                    printing_enabled
                    and latest_monitor_value is not None
                    and now - last_print_time >= print_interval
                ):
                    print(f"monitor_I = {latest_monitor_value:.6e}    raw = {latest_raw_value}")
                    last_print_time = now

                await asyncio.sleep(0.01)

    except serial.SerialException as exc:
        print(f"Could not access serial port {port}: {exc}")
    except KeyboardInterrupt:
        print("\nStopped.")

    return latest_monitor_value


def parse_args():
    parser = argparse.ArgumentParser(
        description="Read the illumination monitor value exactly like RaumaufhellungSteuerung.py."
    )
    parser.add_argument("--port", default=DEFAULT_PORT, help=f"Serial port, default: {DEFAULT_PORT}")
    parser.add_argument(
        "--baud-rate",
        type=int,
        default=DEFAULT_BAUD_RATE,
        help=f"Serial baud rate, default: {DEFAULT_BAUD_RATE}",
    )
    parser.add_argument(
        "--print-interval",
        type=float,
        default=DEFAULT_PRINT_INTERVAL_SECONDS,
        help=f"Print interval in seconds, default: {DEFAULT_PRINT_INTERVAL_SECONDS}",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    asyncio.run(
        read_monitor_continuously(
            args.port,
            args.baud_rate,
            args.print_interval,
        )
    )


if __name__ == "__main__":
    main()
