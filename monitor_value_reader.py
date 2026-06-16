import argparse
import asyncio
from re import compile

import serial


DEFAULT_PORT = "COM3"
DEFAULT_BAUD_RATE = 9600
READ_PERIOD_SECONDS = 0.2


MONITOR_VALUE_PATTERN = compile(r"[+-]\d+\.\d+ E[+-]\d\d")


async def read_monitor_continuously(port, baud_rate, period):
    latest_monitor_value = None

    try:
        with serial.Serial(port, baud_rate, timeout=1) as ser:
            ser.dtr = True
            raw_text = ""

            print(f"Reading monitor on {port} at {baud_rate} baud.")
            print(f"Polling every {period} s. Press Ctrl+C to stop.\n")

            while True:
                if ser.in_waiting > 0:
                    chunk = ser.read(ser.in_waiting).decode("ascii", errors="ignore")
                    raw_text += chunk

                    while True:
                        match = MONITOR_VALUE_PATTERN.search(raw_text)
                        if not match:
                            break

                        raw_value = match.group()
                        raw_text = raw_text[match.end():]

                        latest_monitor_value = float(raw_value.replace(" ", ""))
                        print(f"monitor_I = {latest_monitor_value:.6e}    raw = {raw_value}")

                await asyncio.sleep(period)

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
        "--period",
        type=float,
        default=READ_PERIOD_SECONDS,
        help=f"Polling period in seconds, default: {READ_PERIOD_SECONDS}",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    asyncio.run(read_monitor_continuously(args.port, args.baud_rate, args.period))


if __name__ == "__main__":
    main()
