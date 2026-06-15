import sys

# ==========================================
# 1. PARAMETRELER VE KONFİGÜRASYON
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
print("  2-DOWN / 1-UP CUSTOM ADAPTIVE STAIRCASE (FIXED VERSION)")
print("=" * 65)
print(f"Menzil: {MIN_VAL}-{MAX_VAL} lx | Başlangıç: {START_VAL} lx | Toplam Adım: {TOTAL_TRIALS}")
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
# 2. DENEY DÖNGÜSÜ
# ==========================================
for trial in range(1, TOTAL_TRIALS + 1):
    history.append(current_value)
    step = STEP_SIZES[trial - 1] 
    
    print(f"\n[Adım {trial}/{TOTAL_TRIALS}]")
    print(f"Şu anki Uyaran Şiddeti: {current_value:.2f} lx")
    print("Katılımcı tepkisi bekleniyor (Yukarı Ok: +, Aşağı Ok: -)...")
    
    response = get_arrow_key()
    response_sequence.append(response)
    response_sequence_history.append(response)

    # Kural 1: Üst üste iki pozitif yanıt (++) -> Şiddeti azalt
    if response_sequence == ["+", "+"]:
        print("-> Tepki Kombinasyonu: [ + + ] -> Şiddet azaltılıyor.")
        current_value -= step
        response_sequence = [] 
        
        # GÜVENLİK KİLİDİ: Son trial ise yarım kalan reversal'ı listeye ekleme
        if last_direction == "increased" and trial < TOTAL_TRIALS:
            reversal_points.append(history[-1])
            print("   *** YÖN DEĞİŞİMİ (REVERSAL) TESPİT EDİLDİ! ***")
        last_direction = "decreased"

    # Kural 2: Tek bir negatif yanıt (-) -> Şiddeti artır
    elif response_sequence == ["-"]:
        print("-> Tepki Kombinasyonu: [ - ] -> Şiddet artırılıyor.")
        current_value += step
        response_sequence = [] 
        
        # GÜVENLİK KİLİDİ: Son trial ise yarım kalan reversal'ı listeye ekleme
        if last_direction == "decreased" and trial < TOTAL_TRIALS:
            reversal_points.append(history[-1])
            print("   *** YÖN DEĞİŞİMİ (REVERSAL) TESPİT EDİLDİ! ***")
        last_direction = "increased"
        
    # Kural 3: Bir pozitif, bir negatif yanıt (+ -) dizisi -> Şiddeti artır
    elif response_sequence == ["+", "-"]:
        print("-> Tepki Kombinasyonu: [ + - ] -> Şiddet artırılıyor.")
        current_value += step
        response_sequence = [] 
        
        # GÜVENLİK KİLİDİ: Son trial ise yarım kalan reversal'ı listeye ekleme
        if last_direction == "decreased" and trial < TOTAL_TRIALS:
            reversal_points.append(history[-1])
            print("   *** YÖN DEĞİŞİMİ (REVERSAL) TESPİT EDİLDİ! ***")
        last_direction = "increased"
        
    else:
        print("-> Tepki Kombinasyonu: [ + ] -> Sonuç bekleniyor, şiddet sabit tutuldu.")

    if current_value < MIN_VAL: current_value = MIN_VAL
    elif current_value > MAX_VAL: current_value = MAX_VAL

# ==========================================
# 3. SONUÇ VE DOĞRULANMIŞ THRESHOLD HESABI
# ==========================================
print("\n" + "=" * 65)
print("  DENEY TAMAMLANDI!")
print("=" * 65)

print("Gerçekleşen DOĞRULANMIŞ Yön Değişimleri (Reversals):")
if reversal_points:
    print(f"  {[round(x, 2) for x in reversal_points]} lx (Toplam {len(reversal_points)} adet)")
    print("-" * 65)
    
    if len(reversal_points) >= 6:
        final_reversals = reversal_points[-6:]
        print(f"-> Durum: 6 veya daha fazla reversal var. SON 6 tanesi işleme alınıyor:")
    else:
        final_reversals = reversal_points
        print(f"-> Durum: 6'dan az reversal var. MEVCUT TÜMÜ ({len(reversal_points)} adet) işleme alınıyor:")
        
    print(f"   İşleme Alınan Reversal'lar: {[round(x, 2) for x in final_reversals]} lx")
    
    threshold = sum(final_reversals) / len(final_reversals)
    print(f"\nHesaplanan Güvenilir Eşik Değeri (%70.7 Eşik Oranı): {threshold:.2f} lx")
    
else:
    print("  Hiç yön değişimi gerçekleşmedi.")
    threshold = sum(history[-5:]) / 5
    print(f"\nHesaplanan Eşik Değeri (Son 5 adımın ortalaması): {threshold:.2f} lx")

print("\n")
print(history)
print("\n")
print(response_sequence_history)

print("=" * 65)