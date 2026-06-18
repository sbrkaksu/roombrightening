import sys

# ==========================================
# 1. PARAMETERS AND LIMITS
# ==========================================
MIN_VAL = 0.0100
MAX_VAL = 316.0
MAX_TRIALS = 30
TARGET_REVERSALS = 6
START_VAL = 100.0  # Reasonable middle value to start the test

current_value = START_VAL
history = []
reversal_points = []
last_direction = None
response_sequence_history = []

print("=" * 70)
print("  DYNAMIC-STEP 1-UP / 1-DOWN ADAPTIVE STAIRCASE")
print("=" * 70)
print(f"Range: {MIN_VAL} lx - {MAX_VAL} lx | Target: {TARGET_REVERSALS} reversals (max 30 steps)")
print("-" * 70)
print("Keyboard instructions:")
print("-> Light was disturbing / detected (+)        : [UP ARROW]")
print("-> Light was not disturbing / not detected (-): [DOWN ARROW]")
print("=" * 70)


def get_arrow_key():
    """Capture up/down arrow key presses from the terminal."""
    if sys.platform == "win32":
        import msvcrt
        while True:
            ch = msvcrt.getch()
            if ch in (b'\x00', b'\xe0'):
                ch = msvcrt.getch()
                if ch == b'H':
                    return "+"
                if ch == b'P':
                    return "-"
    else:
        import tty, termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
            if ch == '\x1b':
                sys.stdin.read(1)
                ch3 = sys.stdin.read(1)
                if ch3 == 'A':
                    return "+"
                if ch3 == 'B':
                    return "-"
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def get_dynamic_step_size(val):
    """Determine the dynamic step size from the sensitivity table."""
    if val > 100.0:
        return 30.0  # Discrimination threshold is 30 lx between 100 and 316 lx.
    elif val > 10.0:
        return 10.0  # Discrimination threshold is 10 lx between 10 and 68.1 lx.
    elif val > 3.16:
        return 3.0   # Discrimination threshold is 3 lx between 1 and 6.81 lx.
    elif val > 1.0:
        return 1.0   # Discrimination threshold is 3 lx between 1 and 6.81 lx.
    else:
        return val/2.154  # Small step for the highly sensitive range between 0.01 and 0.681 lx.


# ==========================================
# 2. EXPERIMENT LOOP
# ==========================================
trial = 1
while trial <= MAX_TRIALS and len(reversal_points) < TARGET_REVERSALS:
    history.append(current_value)

    # Calculate the step size dynamically from the current illuminance value.
    step = get_dynamic_step_size(current_value)

    print(f"\n[Step {trial}/{MAX_TRIALS}] | Reversals: {len(reversal_points)}/{TARGET_REVERSALS}")
    print(f"Current stimulus intensity: {current_value:.2f} lx (active step size: {step} lx)")

    response = get_arrow_key()
    response_sequence_history.append(response)


    # 1-up / 1-down rule: every response immediately changes the direction.
    if response == "+":
        print("-> Response: (+) light was too strong / detected -> decreasing intensity.")
        current_value -= step

        # Record a reversal, while avoiding an incomplete final-trial reversal.
        if last_direction == "increased" and trial < MAX_TRIALS:
            reversal_points.append(history[-1])
            print("   *** DIRECTION CHANGE (REVERSAL) DETECTED! ***")
        last_direction = "decreased"

    elif response == "-":
        print("-> Response: (-) light was too weak / not detected -> increasing intensity.")
        current_value += step

        # Record a reversal, while avoiding an incomplete final-trial reversal.
        if last_direction == "decreased" and trial < MAX_TRIALS:
            reversal_points.append(history[-1])
            print("   *** DIRECTION CHANGE (REVERSAL) DETECTED! ***")
        last_direction = "increased"

    # Safety limits: keep the stimulus within the absolute allowed range.
    if current_value < MIN_VAL:
        current_value = MIN_VAL
    elif current_value > MAX_VAL:
        current_value = MAX_VAL

    trial += 1


# ==========================================
# 3. RESULTS AND THRESHOLD CALCULATION
# ==========================================
print("\n" + "=" * 70)
print("  EXPERIMENT COMPLETED!")
print("=" * 70)

print("Confirmed direction changes (reversals):")
if reversal_points:
    print(f"  {[round(x, 4) for x in reversal_points]} lx (Total {len(reversal_points)})")
    print("-" * 70)

    # Use the average of the available confirmed reversals.
    threshold = sum(reversal_points) / len(reversal_points)
    print(f"Calculated threshold value (reversal average): {threshold:.4f} lx")
else:
    print("  No direction changes occurred.")
    threshold = sum(history[-5:]) / 5
    print(f"Calculated threshold value (average of the last 5 steps): {threshold:.4f} lx")


print("\nFull stimulus history:")
print(history)
print("\nFull response sequence history:")
print(response_sequence_history)
print("=" * 70)
