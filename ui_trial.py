import customtkinter
import asyncio
import sys

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.title("Asenkron Zamanlı Buton")
        self.geometry("300x200")

        self.is_clicked = False
        self.turn_count = 1
        
        # Uygulamanın çalışıp çalışmadığını kontrol eden bayrak
        self.is_running = True

        self.button = customtkinter.CTkButton(
            self, 
            text="Tıkla! (Async 2s)", 
            command=self.button_clicked
        )
        self.button.pack(expand=True)

        # Çarpı butonuna basıldığında tetiklenecek fonksiyonu bağlıyoruz
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def button_clicked(self):
        if not self.is_clicked:
            self.is_clicked = True
            print(f"button clicked")

    def on_closing(self):
        # Çarpıya basıldığında döngüleri durdur ve pencereyi yok et
        self.is_running = False
        self.destroy()
        print("Uygulama kapatılıyor, execution durduruldu.")

    async def monitor_loop(self):
        # Sadece uygulama çalışıyorken bu döngü dönsün
        while self.is_running:
            self.is_clicked = False
            
            # 2 saniye beklerken uygulamanın kapatılıp kapatılmadığını 
            # kontrol etmek için küçük adımlarla uyumak daha güvenlidir
            for _ in range(20): # 20 * 0.1 saniye = 2 saniye
                if not self.is_running:
                    return
                await asyncio.sleep(0.1)
            
            if not self.is_running:
                return

            if not self.is_clicked:
                print(f"[Tur {self.turn_count}] button not clicked")
            
            self.turn_count += 1

    async def updater(self):
        while self.is_running:
            try:
                self.update()
                await asyncio.sleep(0.01)
            except (customtkinter.TclError, RuntimeError):
                # Pencere kapandığında oluşabilecek hataları yakala ve çık
                break

async def main():
    app = App()
    
    # Döngüleri çalıştırıyoruz
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
        # Her şey bittiğinde terminali tamamen serbest bırak ve çık
        sys.exit(0)