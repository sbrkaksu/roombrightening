import customtkinter
import asyncio
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
        self.step = None
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
        if not self.is_finished():
           
            self.trial_count += 1
            self.history.append(self.current_value)
            self.response_sequence_history.append(response)
            
            # Calculate the dynamic step
            self.step = self.get_dynamic_step_size(self.current_value)

            
            # 1-Up / 1-Down rule
            if response == "+":
                self.current_value -= self.step
                current_direction = "decreased"

            elif response == "-":
                self.current_value += self.step
                current_direction = "increased"

            # Safety limits
            if self.current_value < self.min_val:
                self.current_value = self.min_val
            elif self.current_value > self.max_val:
                self.current_value = self.max_val
                
            # Direction change (reversal) and final-step lock
            if self.last_direction and self.last_direction != current_direction:
                if self.trial_count < self.max_trials: #do not take account the last reversal if reversal behavior is not completed       
                    self.reversal_points.append(self.history[-1])
                    
            self.last_direction = current_direction

            if self.is_finished():
                self.get_result()
        return


    def get_result(self):
        """Calculates the average result."""
        if not self.reversal_points:
            return print("No reversals recorded, threshold calculation not possible.")
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

    
    def get_status(self):
        if not self.is_finished():
            self.step = self.get_dynamic_step_size(self.current_value)
            
            print(f"\n[Step {self.trial_count + 1}/{self.max_trials}] | Reversals: {len(self.reversal_points)}/{self.target_reversals}")
            print(f"Current stimulus intensity: {self.current_value:.2f} lx (active step size: {self.step:.4f} lx)")
 
            
class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.title("Asynchronous Timed Button")
        self.geometry("300x200")

        self.is_clicked = False
        self.turn_count = 1
        
        # Flag indicating whether the application is running
        self.is_running = True

        self.button = customtkinter.CTkButton(
            self, 
            text="Click! (Async 2s)", 
            command=self.button_clicked
        )
        self.button.pack(expand=True)

        # Bind the function triggered when the window's close button is pressed
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def button_clicked(self):
        if not self.is_clicked:
            self.is_clicked = True
            print(f"button clicked")

    def on_closing(self):
        # Stop the loops and destroy the window when the close button is pressed
        self.is_running = False
        self.destroy()
        print("Application is closing; execution has stopped.")

    async def monitor_loop(self):
        # Keep this loop running only while the application is active
        while self.is_running:
            self.is_clicked = False
            
            # Sleeping in short intervals makes it safer to check whether the
            # application was closed during the two-second waiting period
            for _ in range(20): # 20 * 0.1 seconds = 2 seconds
                if not self.is_running:
                    return
                await asyncio.sleep(0.1) #time.sleep olsa program donardi, 2 sn tek parca uyumak yerine
                                         #2 sen 0.1 parcali uyu kapatinca 2 sn bekleme
            
            if not self.is_running:
                return

            if not self.is_clicked:
                print(f"[Round {self.turn_count}] button not clicked")
            
            self.turn_count += 1

    async def updater(self):
        while self.is_running:
            try:
                self.update()
                await asyncio.sleep(0.01)
            except (customtkinter.TclError, RuntimeError):
                # Catch errors that may occur when the window closes and exit
                break

async def main():
    app = App()
    
    # Run the loops
    await asyncio.gather(
        app.updater(),
        app.monitor_loop()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        # Release the terminal completely and exit when everything is finished
        sys.exit(0)



    
