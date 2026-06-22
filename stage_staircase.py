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
        self.threshold = None

    def get_dynamic_step_size(self, current_value):

        if self.combination_factor == 0: #if the illumination is pure direct 
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
            
        elif self.combination_factor == 1: #if the illumination is pure diffuse
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
        else:                           #combined illumination
            pass

    def is_finished(self):
        """Checks whether the target reversals or maximum trial count has been reached."""
        return self.trial_count >= self.max_trials or len(self.reversal_points) >= self.target_reversals
    
    def update(self, response):
        """Processes the response, calculates the dynamic step, and advances the algorithm."""
        if self.is_finished():
            return False, "" # Do nothing if the algorithm has finished
            
        self.trial_count += 1
        self.history.append(self.current_value)
        self.response_sequence_history.append(response)
        
        # Calculate the dynamic step
        step = self.get_dynamic_step_size(self.current_value)
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
            if self.trial_count < self.max_trials: #do not take account the last reversal if reversal behavior is not completed       
                self.reversal_points.append(self.history[-1])
                is_reversal = True
                
        self.last_direction = current_direction
        
        return is_reversal

    def get_threshold(self):
        """Calculates the average result."""
        if not self.reversal_points:
            return "No reversals recorded, threshold calculation not possible."

        else:

            self.threshold = sum(self.reversal_points) / len(self.reversal_points)

            print("Confirmed direction changes (reversals):")
            print(f"  {[round(x, 4) for x in self.reversal_points]} lx (Total {len(self.reversal_points)})")
            print("\n")
            print("-" * 70)
            print(f"Calculated threshold value (reversal average): {self.threshold: .4f} lx")

            print("\n")
            print("\nFull stimulus history:")
            print([round(x, 4) for x in self.history])
            
            print("\nFull response sequence history:")
            print(self.response_sequence_history)
            print("=" * 70)
        
        return self.threshold


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

    def start_algorithm(self):

        print("=" * 70)
        print("  DYNAMIC-STEP 1-UP / 1-DOWN ADAPTIVE STAIRCASE (OOP VERSION)")
        print("=" * 70)
        print("Keyboard instructions:")
        print("-> Light was disturbing / detected (+)        : [UP ARROW]")
        print("-> Light was not disturbing / not detected (-): [DOWN ARROW]")
        print("=" * 70)
        
        while not self.is_finished():
        
            # Calculate the current step size for display
            current_step = self.get_dynamic_step_size(self.current_value)
            
            
            print(f"\n[Step {self.trial_count + 1}/{self.max_trials}] | Reversals: {len(self.reversal_points)}/{self.target_reversals}")
            print(f"Current stimulus intensity: {self.current_value:.2f} lx (active step size: {current_step:.4f} lx)")

            response = self.get_arrow_key()
            
            # Send the response to the object and retrieve the results
            is_reversal = self.update(response)
            
            if is_reversal:
                print("   *** DIRECTION CHANGE (REVERSAL) DETECTED! ***")

        # ==========================================
        # 3. RESULTS
        # ==========================================

        if self.is_finished():
            
            print("\n" + "=" * 70)
            print("  EXPERIMENT COMPLETED!")
            print("=" * 70)
            
            self.get_threshold()

if __name__ == "__main__":
    staircase = AdaptiveStaircase(start_val=100, min_val=0.01, max_val=316, max_trials=30, target_reversals=6, combination_factor=1)
    staircase.start_algorithm()


    
