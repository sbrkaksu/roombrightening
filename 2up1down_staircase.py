import sys

# ==========================================
# 1. PARAMETERS AND CONFIGURATION
# ==========================================
MIN_VAL = 0
MAX_VAL = 100
TOTAL_TRIALS = 30
START_VAL = 70  

STEP_SIZES = [8] * 10 + [4] * 10 + [2] * 10

current_value = START_VAL
history = []           
reversal_points = []   
last_direction = None    
response_sequence = []
response_sequence_history = []

print("=" * 65)
print("1-DOWN / 1-UP ADAPTIVE STAIRCASE METHOD")
print("=" * 65)
print(f"Range: {MIN_VAL}-{MAX_VAL} lx | Start: {START_VAL} lx | Total Steps: {TOTAL_TRIALS}")
print("-" * 65)

def get_arrow_key():
    if sys.platform == "win32":
        import msvcrt
        while True:
            ch = msvcrt.getch()
            if ch in (b'\x00', b'\xe0'):  
                ch = msvcrt.getch()
                if ch == b'H': return "+"
                if ch == b'P': return "-"
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
                if ch3 == 'A': return "+"
                if ch3 == 'B': return "-"
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

# ==========================================
# 2. EXPERIMENT LOOP
# ==========================================
for trial in range(1, TOTAL_TRIALS + 1):
    history.append(current_value)
    step = STEP_SIZES[trial - 1] 
    
    print(f"\n[Step {trial}/{TOTAL_TRIALS}]")
    print(f"Current stimulus intensity: {current_value:.2f} lx")
    print("Waiting for participant response (Up Arrow: +, Down Arrow: -)...")
    
    response = get_arrow_key()
    response_sequence.append(response)
    response_sequence_history.append(response)

    # Rule 1: Two consecutive positive responses (++) -> decrease intensity
    if response_sequence == ["+", "+"]:
        print("-> Response combination: [ + + ] -> Decreasing intensity.")
        current_value -= step
        response_sequence = [] 
        
        # Safety guard: if this is the final trial, do not add an incomplete reversal
        if last_direction == "increased" and trial < TOTAL_TRIALS:
            reversal_points.append(history[-1])
            print("   *** DIRECTION CHANGE (REVERSAL) DETECTED! ***")
        last_direction = "decreased"

    # Rule 2: A single negative response (-) -> increase intensity
    elif response_sequence == ["-"]:
        print("-> Response combination: [ - ] -> Increasing intensity.")
        current_value += step
        response_sequence = [] 
        
        # Safety guard: if this is the final trial, do not add an incomplete reversal
        if last_direction == "decreased" and trial < TOTAL_TRIALS:
            reversal_points.append(history[-1])
            print("   *** DIRECTION CHANGE (REVERSAL) DETECTED! ***")
        last_direction = "increased"
        
    # Rule 3: One positive followed by one negative response (+ -) -> increase intensity
    elif response_sequence == ["+", "-"]:
        print("-> Response combination: [ + - ] -> Increasing intensity.")
        current_value += step
        response_sequence = [] 
        
        # Safety guard: if this is the final trial, do not add an incomplete reversal
        if last_direction == "decreased" and trial < TOTAL_TRIALS:
            reversal_points.append(history[-1])
            print("   *** DIRECTION CHANGE (REVERSAL) DETECTED! ***")
        last_direction = "increased"
        
    else:
        print("-> Response combination: [ + ] -> Waiting for result, intensity kept constant.")

    if current_value < MIN_VAL: current_value = MIN_VAL
    elif current_value > MAX_VAL: current_value = MAX_VAL

# ==========================================
# 3. RESULT AND VALIDATED THRESHOLD CALCULATION
# ==========================================
print("\n" + "=" * 65)
print("  EXPERIMENT COMPLETED!")
print("=" * 65)

print("Confirmed direction changes (reversals):")
if reversal_points:
    print(f"  {[round(x, 2) for x in reversal_points]} lx (Total {len(reversal_points)})")
    print("-" * 65)
    
    if len(reversal_points) >= 6:
        final_reversals = reversal_points[-6:]
        print("-> Status: 6 or more reversals found. Using the last 6:")
    else:
        final_reversals = reversal_points
        print(f"-> Status: Less than 6 reversals found. Using all available reversals ({len(reversal_points)}):")
        
    print(f"   Reversals used for calculation: {[round(x, 2) for x in final_reversals]} lx") #2 digit after comma 
    
    threshold = sum(final_reversals) / len(final_reversals)
    print(f"\nCalculated reliable threshold value (70.7% threshold rate): {threshold:.2f} lx")
    
else:
    print("  No direction changes occurred.")
    threshold = sum(history[-5:]) / 5
    print(f"\nCalculated threshold value (average of the last 5 steps): {threshold:.2f} lx")

print("\n")
print(history)
print("\n")
print(response_sequence_history)

print("=" * 65)
