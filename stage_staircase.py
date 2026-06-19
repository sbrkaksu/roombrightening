import sys

# ==========================================
# 1. ALGORITHM CLASS
# ==========================================
class AdaptiveStaircase:
    def __init__(self, start_val, min_val, max_val, max_trials, target_reversals, combination_factor):
        # Parameters
        self.current_value = start_val
        self.min_val = min_val
        self.max_val = max_val
        self.max_trials = max_trials
        self.target_reversals = target_reversals
        self.combination_factor = combination_factor
        
        # Memory (state)
        self.history = []
        self.reversal_points = []
        self.response_sequence_history = []
        self.last_direction = None
        self.trial_count = 0
        self.active_step = 0.0 # Stores the current step for display

    def _get_dynamic_step_size(self, current_value):
        """Determines the dynamic step size based on the sensitivity table."""
        if self.combination_factor == 0:
            if current_value > 100.0:
                return 30.0  
            elif current_value > 10.0:
                return 10.0  
            elif current_value > 3.16:
                return 3.0   
            elif current_value > 1.0:
                return 1.0   
            else:
                return current_value / 2.154  
            
        elif self.combination_factor == 1:
            if current_value > 100.0:
                return 40.0  
            elif current_value > 10.0:
                return 13.0  
            elif current_value > 3.16:
                return 4.0   
            elif current_value > 1.0:
                return 1.0   
            else:
                return current_value / 2.154  

    def update(self, response):
        """Processes the response, calculates the dynamic step, and advances the algorithm."""
        if self.is_finished():
            return False, "" # Do nothing if the algorithm has finished
            
        self.trial_count += 1
        self.history.append(self.current_value)
        self.response_sequence_history.append(response)
        
        # Calculate the dynamic step
        step = self._get_dynamic_step_size(self.current_value)
        self.active_step = step
        

        is_reversal = False
        
        # 1-Up / 1-Down rule
        if response == "+":
            self.current_value -= step
            current_direction = "decreased"

        elif response == "-":
            self.current_value += step
            current_direction = "increased"

        else:
            return False, "Invalid response"
            
        # Safety limits
        if self.current_value < self.min_val:
            self.current_value = self.min_val
        elif self.current_value > self.max_val:
            self.current_value = self.max_val
            
        # Direction change (reversal) and final-step lock
        if self.last_direction and self.last_direction != current_direction:
            if self.trial_count < self.max_trials:
                self.reversal_points.append(self.history[-1])
                is_reversal = True
                
        self.last_direction = current_direction
        
        return is_reversal

    def is_finished(self):
        """Checks whether the target reversals or maximum trial count has been reached."""
        return self.trial_count >= self.max_trials or len(self.reversal_points) >= self.target_reversals

    def get_threshold(self):
        """Calculates the average result."""
        if self.reversal_points:
            return sum(self.reversal_points) / len(self.reversal_points)
        else:
            return sum(self.history[-5:]) / 5 if self.history else 0.0


    # ==========================================
    # 2. INTERFACE AND EXPERIMENT EXECUTION (MAIN)
    # ==========================================
    def get_arrow_key(self):
        """Captures the up/down arrow keys from the terminal."""
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

if __name__ == "__main__":
    print("=" * 70)
    print("  DYNAMIC-STEP 1-UP / 1-DOWN ADAPTIVE STAIRCASE (OOP VERSION)")
    print("=" * 70)
    print("Keyboard instructions:")
    print("-> Light was disturbing / detected (+)        : [UP ARROW]")
    print("-> Light was not disturbing / not detected (-): [DOWN ARROW]")
    print("=" * 70)

    # Create the staircase object
    staircase = AdaptiveStaircase(start_val=147.0, min_val=0.0100, max_val=316.0, max_trials=30, target_reversals=6 , combination_factor=1)

    # The experiment loop runs until the staircase is finished
    while not staircase.is_finished():
        
        # Calculate the current step size for display
        current_step = staircase._get_dynamic_step_size(staircase.current_value)
        
        print(f"\n[Step {staircase.trial_count + 1}/{staircase.max_trials}] | Reversals: {len(staircase.reversal_points)}/{staircase.target_reversals}")
        print(f"Current stimulus intensity: {staircase.current_value:.2f} lx (active step size: {current_step:.4f} lx)")

        response = staircase.get_arrow_key()
        
        # Send the response to the object and retrieve the results
        is_reversal = staircase.update(response)
        
        if is_reversal:
            print("   *** DIRECTION CHANGE (REVERSAL) DETECTED! ***")

    # ==========================================
    # 3. RESULTS
    # ==========================================
    print("\n" + "=" * 70)
    print("  EXPERIMENT COMPLETED!")
    print("=" * 70)

    print("Confirmed direction changes (reversals):")
    if staircase.reversal_points:
        print(f"  {[round(x, 4) for x in staircase.reversal_points]} lx (Total {len(staircase.reversal_points)})")
        print("-" * 70)
        print(f"Calculated threshold value (reversal average): {staircase.get_threshold():.4f} lx")
    else:
        print("  No direction changes occurred.")
        print(f"Calculated threshold value (average of the last 5 steps): {staircase.get_threshold():.4f} lx")

    print("\nFull stimulus history:")
    print([round(x, 4) for x in staircase.history])
    
    print("\nFull response sequence history:")
    print(staircase.response_sequence_history)
    print("=" * 70)
