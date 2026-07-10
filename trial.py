# ==========================================
# 1. ALGORITHM CLASS
# ==========================================
class AdaptiveStaircase:
    def __init__(self, Phase, time, **kwargs):

        #Actual Durchgang of the Experiment
        self.phase = Phase
        self.time = time
        self.combination_factor = kwargs.get("combination_factor", 1)
        self.type_of_illumination = "Direct" if self.combination_factor == 1 else "Diffuse" if self.combination_factor == 0 else "Combined"  

        #Stimilus values for the E threshold determination phase 
        self.stimuli_E_night  = [ 0.01, 0.0147, 0.0215, 0.0316, 0.0464, 0.0681, 
                    0.1, 0.147, 0.215, 0.316, 0.464, 0.681, 
                    1.0, 1.47, 2.15, 3.16, 4.64, 6.81, 
                    10.0, 14.7, 21.5, 31.6]
        self.stimuli_E_evening  = [ 0.1, 0.147, 0.215, 0.316, 0.464, 0.681, 
            1.0, 1.47, 2.15, 3.16, 4.64, 6.81, 
            10.0, 14.7, 21.5, 31.6, 46.4, 68.1, 
            100.0, 147.0, 215.0, 316.0]
        # Stimulus values for the combination threshold determination phase
        self.stimuli_combined = [0.0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 
                             0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0]

        if self.phase == "E_Block":
            if self.time == "night":
                self.chosen_stimuli = self.stimuli_E_night
            elif self.time == "evening":
                self.chosen_stimuli = self.stimuli_E_evening

        elif self.phase == "Combination_Block":
            self.chosen_stimuli = self.stimuli_combined

        # Parameters
        self.current_value_index = len(self.chosen_stimuli) - 1
        self.current_value = self.chosen_stimuli[self.current_value_index]
        self.min_val = self.chosen_stimuli[0]
        self.max_val = self.chosen_stimuli[-1]
        self.max_trials = 32
        self.target_reversals = 6
        
        
        # Memory (state)
        self.history = []
        self.reversal_points = []
        self.response_sequence_history = []
        self.last_direction = None
        self.trial_count = 0
        self.is_staircase_completed = False

    def is_finished(self):
        """Checks whether the target reversals or maximum trial count has been reached."""
        return self.trial_count >= self.max_trials or len(self.reversal_points) >= self.target_reversals
    
    def update(self, response):
        """Processes the response, calculates the dynamic step, and advances the algorithm."""
        
           
        self.trial_count += 1
        self.history.append(self.current_value)
        self.response_sequence_history.append(response)

        
        # 1-Up / 1-Down rule
        if response == "+":
            self.current_value_index -= 1
            current_direction = "decreased"

        elif response == "-":
            self.current_value_index += 1
            current_direction = "increased"

        # Safety limits
        self.current_value_index = max(0, min(self.current_value_index, len(self.chosen_stimuli) - 1))
        self.current_value = self.chosen_stimuli[self.current_value_index]
            
        # Direction change (reversal) and final-step lock
        if self.last_direction and self.last_direction != current_direction:
            if self.trial_count < self.max_trials: #do not take account the last reversal if reversal behavior is not completed       
                self.reversal_points.append(self.history[-1])
                
        self.last_direction = current_direction
        

    def get_threshold(self):
        """Returns the calculated threshold value."""
        self.threshold = sum(self.reversal_points) / len(self.reversal_points)
        return self.threshold

    def get_result(self):
        """Calculates the average result."""

        if not self.reversal_points:
                print("No reversals recorded, threshold calculation not possible.")
        else:

                self.get_threshold()
                self.is_staircase_completed = True

                print(f"Confirmed direction changes (reversals): {self.type_of_illumination}")
                print(f" Reversals: {[round(x, 4) for x in self.reversal_points]} (Total {len(self.reversal_points)})")
                print("\n")
                print(f"Calculated threshold value for Illuminance (reversal average): {self.get_threshold(): .4f} lx")

                print("\n")
                print("\nFull stimulus history:")
                print([round(x, 4) for x in self.history])
                
                print("\nFull response sequence history:")
                print(self.response_sequence_history)
                print("=" * 70)
        return self.is_staircase_completed
            
        

    
    def get_status(self):

        if not self.is_finished():
            print('-'* 10)

            print(self.type_of_illumination)
            print('-'* 10)
            print(f"\n[Step {self.trial_count + 1}/{self.max_trials}] | Reversals: {len(self.reversal_points)}/{self.target_reversals}")
            print(f"Current stimulus intensity: {self.current_value:.2f} lx ")
