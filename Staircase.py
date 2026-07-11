# ==========================================
# 1. ALGORITHM CLASS
# ==========================================
class AdaptiveStaircase:
    def __init__(self, phase, time, **kwargs):

        #Actual Durchgang of the Experiment
        self.phase = phase
        self.time = time
        self.combination_factor = kwargs.get("combination_factor", 1)
        self.type_of_illumination = self.get_type_from_combination_factor()

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
        self.max_trials = 32
        self.target_reversals = 6
        
        
        # Memory (state)
        self.history = []
        self.reversal_points = []
        self.response_sequence_history = []
        self.last_direction = None
        self.trial_count = 0
        self.threshold = None

    def get_type_from_combination_factor(self):
        if self.combination_factor == 0:
            return "Diffuse"
        if self.combination_factor == 1:
            return "Direct"
        return "Combined"

    def is_finished(self):
        """Checks whether the target reversals or maximum trial count has been reached."""
        return self.trial_count >= self.max_trials or len(self.reversal_points) >= self.target_reversals
    
    def update(self, response):
        """Processes the response, calculates the dynamic step, and advances the algorithm."""
        
           
        self.trial_count += 1
        self.history.append(self.current_value)
        self.response_sequence_history.append(response)

        previous_value_index = self.current_value_index
        
        # 1-Up / 1-Down rule
        if response == "+":
            self.current_value_index -= 1

        elif response == "-":
            self.current_value_index += 1

        # Safety limits
        self.current_value_index = max(0, min(self.current_value_index, len(self.chosen_stimuli) - 1))
        self.current_value = self.chosen_stimuli[self.current_value_index]

        if self.current_value_index == previous_value_index:
            return

        if self.current_value_index < previous_value_index:
            current_direction = "decreased"
        else:
            current_direction = "increased"
            
        # Direction change (reversal) and final-step lock
        if self.last_direction and self.last_direction != current_direction:
            self.reversal_points.append(self.history[-1])
                
        self.last_direction = current_direction
        

    def get_threshold(self):
        """Returns the calculated threshold value."""
        if not self.reversal_points:
            self.threshold = None
            return self.threshold

        self.threshold = sum(self.reversal_points) / len(self.reversal_points)
        return self.threshold
