import customtkinter
import numpy as np
import asyncio
from async_tkinter_loop import async_handler
import sys
import os

# ==========================================
# 1. ALGORITHM CLASS
# ==========================================
class AdaptiveStaircase:
    def __init__(self, Phase, time, **kwargs):

        #Actual Durchgang of the Experiment
        self.phase = kwargs.get("Phase", "E_threshold_determination_phase")  # Default to E_threshold_determination_phase if not provided
        self.combination_factor = kwargs.get("combination_factor", 1)
        self.time = kwargs.get("time", "evening")  # Default to evening if not provided

        #Stimilus values for the E threshold determination phase 
        self.stimuli_E_night  = [ 0.01, 0.0147, 0.0215, 0.0316, 0.0464, 0.0681, 
                    0.1, 0.147, 0.215, 0.316, 0.464, 0.681, 
                    1, 1.47, 2.15, 3.16, 4.64, 6.81, 
                    10, 14.7, 21.5, 31.6]
        self.stimuli_E_evening  = [ 0.1, 0.147, 0.215, 0.316, 0.464, 0.681, 
            1, 1.47, 2.15, 3.16, 4.64, 6.81, 
            10, 14.7, 21.5, 31.6, 46.4, 68.1, 
            100, 147, 215, 316]
        # Stimulus values for the combination threshold determination phase
        self.stimuli_combined = [0.0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 
                             0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0]

        if self.phase == "E_threshold_determination_phase":
            if self.time == "night":
                self.chosen_stimuli = self.stimuli_E_night
            elif self.time == "evening":
                self.chosen_stimuli = self.stimuli_E_evening

        elif self.phase == "combination_threshold_determination_phase":
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
        self.threshold = None

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
        

    def get_result(self):
        """Calculates the average result."""

        if not self.reversal_points:
                return print("No reversals recorded, threshold calculation not possible.")
        else:

                self.threshold = sum(self.reversal_points) / len(self.reversal_points)

                if self.phase == "E_threshold_determination_phase":

                    print(f"Confirmed direction changes (reversals): {'Direct' if self.combination_factor == 1 else 'Diffuse'}")
                    print(f" Reversals: {[round(x, 4) for x in self.reversal_points]} (Total {len(self.reversal_points)})")
                    print("\n")
                    print(f"Calculated threshold value for Illuminance (reversal average): {self.threshold: .4f} lx")

                elif self.phase == "combination_threshold_determination_phase":

                    print(f"Confirmed direction changes (reversals): {'Combined'}")
                    print(f" Reversals: {[round(x, 4) for x in self.reversal_points]} (Total {len(self.reversal_points)})")
                    print("\n")
                    print(f"Calculated threshold value for Combined Illumination (reversal average): {self.threshold: .4f}")

                print("\n")
                print("\nFull stimulus history:")
                print([round(x, 4) for x in self.history])
                
                print("\nFull response sequence history:")
                print(self.response_sequence_history)
                print("=" * 70)
            
        return self.threshold

    
    def get_status(self):

        if not self.is_finished():
            print('-'* 10)

            if self.phase == "E_threshold_determination_phase":
                print('Direct' if self.combination_factor == 1 else 'Diffuse')
                print('-'* 10)
                print(f"\n[Step {self.trial_count + 1}/{self.max_trials}] | Reversals: {len(self.reversal_points)}/{self.target_reversals}")
                print(f"Current stimulus intensity: {self.current_value:.2f} lx ")
            elif self.phase == "combination_threshold_determination_phase":
                print('Combined')
                print('-'* 10)
                print(f"\n[Step {self.trial_count + 1}/{self.max_trials}] | Reversals: {len(self.reversal_points)}/{self.target_reversals}")
                print(f"Current stimulus intensity: {self.current_value:.2f} ")
            
class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.title("Asenkron Zamanlı Buton")
        self.geometry("300x200")
                
        self.is_running = True 
        self.is_clicked = False

        self.current_durchgang = 1
        self.is_Durchgang_completed = False

        #self.is_E_threshold_determination_phase_completed = self.is_Durchgang_1_completed and self.is_Durchgang_2_completed
        #self.is_combination_threshold_determination_phase_completed = False

        self.available_staircases = None  # To keep track of the currently active staircase
        self.E_threshold_results =  []
        self.combination_threshold_results = []
        
        

        self.button_start = customtkinter.CTkButton(
            self, 
            text="Start", 
            command=self.start_app # Now it will run asynchronously thanks to the decorator
        )
        self.button_start.pack(expand=True)

        self.button_response = customtkinter.CTkButton(
            self, 
            text="Response", 
            command=self.click
        )
        self.button_response.pack(expand=True)

        self.protocol("WM_DELETE_WINDOW", self.stop)

    def create_staircases(self):
            if self.current_durchgang == 1:
                    self.staircase_direct_evening = AdaptiveStaircase(Phase="E_threshold_determination_phase", time="evening", combination_factor=1)
                    self.staircase_diffuse_evening = AdaptiveStaircase(Phase="E_threshold_determination_phase", time="evening", combination_factor=0)
                    self.available_staircases = [self.staircase_direct_evening, self.staircase_diffuse_evening]
            elif self.current_durchgang == 2:
                    self.staircase_direct_night = AdaptiveStaircase(Phase="E_threshold_determination_phase", time="night", combination_factor=1)
                    self.staircase_diffuse_night = AdaptiveStaircase(Phase="E_threshold_determination_phase", time="night", combination_factor=0)
                    self.available_staircases = [self.staircase_direct_night, self.staircase_diffuse_night]
            elif self.current_durchgang == 3:
                pass
            self.is_running = True

    @async_handler
    async def start_app(self):

        """Asynchronous experiment loop that runs when the Start button is pressed."""
        self.create_staircases()

        print("--- Deney Başlatıldı ---")
        self.button_start.configure(state="disabled")
        
        # Instead of a separate monitor_loop, the loop is handled directly in the button's async function
        while self.is_running:
            staircases = self.select_random_staircase()

            if staircases == "Completed": #end of the phase
                self.save_threshold_results()
                self.proceed_next_phase()
                return
            
            staircases.get_status()

            # Wait 3 seconds, checking for shutdown in 0.1-second intervals
            for _ in range(15): 
                if not self.is_running:
                    return
                await asyncio.sleep(0.1)
            
            if not self.is_running:
                return

            
            self.handle_response(staircases)
            
        # If the experiment finishes by itself (is_finished returns True), you can re-enable the button
        # self.button_start.configure(state="normal")
               
    def click(self):
        if not self.is_clicked:
            self.is_clicked = True   

    def select_random_staircase(self):

        seed = int.from_bytes(os.urandom(128), sys.byteorder)
        rng = np.random.default_rng(seed)
        
        available_staircases = []  # Reset the list each time we select a staircase
          # Reset the list each time we select a staircase
        """
        if not self.staircase_diffuse.is_finished():
            available_staircases.append(self.staircase_diffuse)
        """
        if not self.available_staircases[0].is_finished():
            available_staircases.append(self.available_staircases[0])
            print(self.available_staircases[0].time)
            
        if not available_staircases: #end of the durchgang
            self.is_Durchgang_completed = True
            print("Both staircases have finished")
            print('#' * 30)
            self.available_staircases[0].get_result()
            print('#' * 30)
            self.available_staircases[1].get_result()
            print('#' * 30)
            return "Completed"  # Return a special value to indicate that both staircases are finished

        index = int(rng.integers(0, len(available_staircases)))
        selected_staricase =    available_staircases[index]
        return selected_staricase
    """
    def save_threshold_results(self):
        if self.current_durchgang == 1:
            self.E_threshold_results.append(self.available_staircases[0].get_result())
            self.E_threshold_results.append(self.available_staircases[1].get_result())
        elif self.current_durchgang == 2:
            self.E_threshold_results.append(self.available_staircases[0].get_result())
            self.E_threshold_results.append(self.available_staircases[1].get_result())
        elif self.current_durchgang == 3:
            self.combination_threshold_results.append(self.available_staircases[0].get_result())
            self.combination_threshold_results.append(self.available_staircases[1].get_result())
            
        print(f"Durchgang {self.current_durchgang} completed.")
    """
    def proceed_next_phase(self):
            self.is_running = False
            self.is_Durchgang_completed = False
            self.current_durchgang += 1
            self.available_staircases = []  # Clear the list to indicate that both staircases are finished
            self.button_start.configure(state="normal")
        
    def handle_response(self, staircase):

        if self.is_clicked:
            staircase.update("+")
            self.is_clicked = False
            print("+ pressed")
        else:
            staircase.update("-")
            print("- pressed")

    def stop(self):
        self.is_running = False
        self.destroy()

    async def updater(self):
        """Main update loop required to keep the GUI responsive."""
        while self.is_running:
            try:
                self.update()
                await asyncio.sleep(0.01)
            except (RuntimeError):
                # CustomTkinter windows may raise TclError when closed, so catch it and exit
                break

async def main():
    app = App()
    # It is enough to gather/run only the GUI update loop.
    # The other loop will start by itself via @async_handler when the Start button is pressed.
    await app.updater()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        sys.exit(0)
    
