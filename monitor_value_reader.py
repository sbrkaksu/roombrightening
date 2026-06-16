import argparse
import asyncio
from re import compile

import serial


DEFAULT_PORT = "COM3"
DEFAULT_BAUD_RATE = 9600
READ_PERIOD_SECONDS = 2
DEFAULT_CHANGE_THRESHOLD = 0.10


MONITOR_VALUE_PATTERN = compile(r"[+-]\d+\.\d+ E[+-]\d\d")

def changed_enough(current_value, previous_value, threshold):
    if previous_value is None:
        return True
    if previous_value == 0:
        return current_value != 0

    relative_change = abs(current_value - previous_value) / abs(previous_value)
    return relative_change > threshold


async def read_monitor_continuously(port, baud_rate, period, change_threshold):
    latest_monitor_value = None
    last_printed_monitor_value = None

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
                        if changed_enough(
                            latest_monitor_value,
                            last_printed_monitor_value,
                            change_threshold,
                        ):
                            print(f"monitor_I = {latest_monitor_value:.6e}    raw = {raw_value}")
                            last_printed_monitor_value = latest_monitor_value

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
    parser.add_argument(
        "--change-threshold",
        type=float,
        default=DEFAULT_CHANGE_THRESHOLD,
        help=(
            "Relative change needed before printing again, "
            f"default: {DEFAULT_CHANGE_THRESHOLD} (10%)"
        ),
    )
    return parser.parse_args()


def main():
    args = parse_args()
    asyncio.run(
        read_monitor_continuously(
            args.port,
            args.baud_rate,
            args.period,
            args.change_threshold,
        )
    )


if __name__ == "__main__":
    main()
