import sys

# ==========================================
# 1. PARAMETRELER VE KONFİGÜRASYON
# ==========================================
MIN_VAL = 0
MAX_VAL = 100
TOTAL_TRIALS = 30
START_VAL = 70  

# Adım boyutları: ilk 10 adım 20, sonraki 10 adım 10, son 10 adım 5 lx
STEP_SIZES = [8] * 10 + [4] * 10 + [2] * 10

current_value = START_VAL
history = []           
reversal_points = []   
last_direction = None    

# Yanıt kombinasyonlarını takip etmek için hafıza dizisi
response_sequence = []

print("=" * 65)
print("  2-DOWN / 1-UP CUSTOM ADAPTIVE STAIRCASE ALGORITHM")
print("=" * 65)
print(f"Menzil: {MIN_VAL}-{MAX_VAL} lx | Başlangıç: {START_VAL} lx | Toplam Adım: {TOTAL_TRIALS}")
print("-" * 65)
print("Klavye Talimatları:")
print("-> (+) POZİTİF Yanıt (Işık rahatsız etti)      : [YUKARI OK] tuşu")
print("-> (-) NEGATİF Yanıt (Işık rahatsız etmedi)   : [AŞAĞI OK] tuşu")
print("=" * 65)

def get_arrow_key():
    """Terminalden yukarı veya aşağı ok tuşunu Enter gerektirmeden yakalar."""
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
# 2. DENEY DÖNGÜSÜ (TAM 30 ADIM)
# ==========================================
for trial in range(1, TOTAL_TRIALS + 1):
    history.append(current_value)
    step = STEP_SIZES[trial - 1] 
    
    print(f"\n[Adım {trial}/{TOTAL_TRIALS}]")
    print(f"Şu anki Uyaran Şiddeti: {current_value:.2f} lx")
    print(f"Mevcut Yanıt Dizisi  : {' '.join(response_sequence) if response_sequence else 'Boş'}")
    print("Katılımcı tepkisi bekleniyor (Yukarı Ok: +, Aşağı Ok: -)...")
    
    response = get_arrow_key()
    response_sequence.append(response)
    
    # Kural 1: Üst üste iki pozitif yanıt (++) -> Şiddeti azalt
    if response_sequence == ["+", "+"]:
        print("-> Tepki Kombinasyonu: [ + + ] -> Şiddet azaltılıyor.")
        current_value -= step
        response_sequence = [] 
        
        if last_direction == "increased":
            reversal_points.append(history[-1])
            print("   *** YÖN DEĞİŞİMİ (REVERSAL) TESPİT EDİLDİ! ***")
        last_direction = "decreased"

    # Kural 2: Tek bir negatif yanıt (-) -> Şiddeti artır
    elif response_sequence == ["-"]:
        print("-> Tepki Kombinasyonu: [ - ] -> Şiddet artırılıyor.")
        current_value += step
        response_sequence = [] 
        
        if last_direction == "decreased":
            reversal_points.append(history[-1])
            print("   *** YÖN DEĞİŞİMİ (REVERSAL) TESPİT EDİLDİ! ***")
        last_direction = "increased"
        
    # Kural 3: Bir pozitif, bir negatif yanıt (+ -) dizisi -> Şiddeti artır
    elif response_sequence == ["+", "-"]:
        print("-> Tepki Kombinasyonu: [ + - ] -> Şiddet artırılıyor.")
        current_value += step
        response_sequence = [] 
        
        if last_direction == "decreased":
            reversal_points.append(history[-1])
            print("   *** YÖN DEĞİŞİMİ (REVERSAL) TESPİT EDİLDİ! ***")
        last_direction = "increased"
        
    else:
        print("-> Tepki Kombinasyonu: [ + ] -> Sonuç bekleniyor, şiddet sabit tutuldu.")

    if current_value < MIN_VAL:
        current_value = MIN_VAL
    elif current_value > MAX_VAL:
        current_value = MAX_VAL

# ==========================================
# 3. YENİLENEN SONUÇ VE THRESHOLD HESAPLAMA
# ==========================================
print("\n" + "=" * 65)
print("  DENEY TAMAMLANDI!")
print("=" * 65)

# 1. Bütün Reversal'ları ekrana yazdırıyoruz
print("Gerçekleşen BÜTÜN Yön Değişimleri (Reversals):")
if reversal_points:
    print(f"  {[round(x, 2) for x in reversal_points]} lx (Toplam {len(reversal_points)} adet)")
    print("-" * 65)
    
    # 2. Reversal sayısına göre filtreleme mantığı
    if len(reversal_points) >= 6:
        # Python'da [-6:] listenin son 6 elemanını alır
        final_reversals = reversal_points[-6:]
        print(f"-> Durum: 6 veya daha fazla reversal var. SON 6 tanesi işleme alınıyor:")
    else:
        final_reversals = reversal_points
        print(f"-> Durum: 6'dan az reversal var. MEVCUT TÜMÜ ({len(reversal_points)} adet) işleme alınıyor:")
        
    print(f"   İşleme Alınan Reversal'lar: {[round(x, 2) for x in final_reversals]} lx")
    
    # 3. Threshold (Ortalama) Hesaplama
    threshold = sum(final_reversals) / len(final_reversals)
    print(f"\nHesaplanan Eşik Değeri (%70.7 Eşik Oranı): {threshold:.2f} lx")
    
else:
    # Katılımcı çok sıra dışı/tutarsız davrandıysa ve hiç reversal oluşmadıysa güvenlik önlemi
    print("  Hiç yön değişimi gerçekleşmedi.")
    threshold = sum(history[-5:]) / 5
    print(f"\nHesaplanan Eşik Değeri (Son 5 adımın ortalaması): {threshold:.2f} lx")

print("=" * 65)