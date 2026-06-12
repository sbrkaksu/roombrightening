import sys

# ==========================================
# 1. PARAMETRELER VE AYARLAR
# ==========================================
MIN_VAL = 0
MAX_VAL = 100
TOTAL_TRIALS = 24
START_VAL = 90  # Testin başlayacağı orta nokta

# Katılımcı yaklaştıkça hassaslaşan dinamik adım boyutları
# İlk 10 adımda 10 lx, sonraki 10 adımda 5 lx, son 10 adımda 2 lx oynatacağız
STEP_SIZES = [10] * 8 + [5] * 8 + [2] * 8

current_value = START_VAL
history = []           # Test boyunca uğranan tüm lüks değerleri
reversal_points = []   # Yön değişimlerinin gerçekleştiği lüks değerleri

# 1-Up / 3-Down için sayaçlar
consecutive_correct = 0  # Üst üste gelen "Rahatsız Oldum (Doğru)" sayısı
last_direction = None    # En son hareket yönü ("up" veya "down")

print("=" * 60)
print("  1-UP / 3-DOWN ADAPTIVE STAIRCASE (LUX COMFORT TEST)")
print("=" * 60)
print(f"Sınırlar: {MIN_VAL} lx ile {MAX_VAL} lx arası | Toplam Adım: {TOTAL_TRIALS}")
print("-" * 60)
print("Klavye Talimatları:")
print("-> Işık sizi RAHATSIZ ETTİ ise       : [YUKARI OK] tuşuna basın")
print("-> Işık sizi RAHATSIZ ETMEDİ ise    : [AŞAĞI OK] tuşuna basın")
print("=" * 60)

def get_arrow_key():
    """Terminalden yukarı veya aşağı ok tuşunu Enter gerektirmeden yakalar."""
    if sys.platform == "win32":
        import msvcrt
        while True:
            ch = msvcrt.getch()
            if ch in (b'\x00', b'\xe0'):  
                ch = msvcrt.getch()
                if ch == b'H': return "up"
                if ch == b'P': return "down"

# ==========================================
# 2. DENEY DÖNGÜSÜ (SABİT 30 ADIM)
# ==========================================
for trial in range(1, TOTAL_TRIALS + 1):
    history.append(current_value)
    
    print(f"\n[Adım {trial}/{TOTAL_TRIALS}]")
    print(f"Şu anki Işık Şiddeti: {current_value:.2f} lx")
    print(f"Mevcut Seri (Üst üste rahatsızlık): {consecutive_correct}/3")
    print("Seçiminiz bekleniyor (Yukarı/Aşağı Ok)...")
    
    key = get_arrow_key()
    step = STEP_SIZES[trial - 1] # Bu adımda kullanılacak lüks değişim miktarı
    
    # --- DURUM A: IŞIK RAHATSIZ ETTİ (DOĞRU YANIT) ---
    if key == "up":
        print("-> Tepki: RAHATSIZ ETTİ (1)")
        consecutive_correct += 1
        
        # 3 kez üst üste rahatsız etti mi?
        if consecutive_correct == 3:
            print(f"   [3/3 Seri Yakalandı!] Işık {step} lx kısılıyor.")
            current_value -= step
            consecutive_correct = 0  # Sayacı sıfırla
            
            # Yön Değişimi (Reversal) Kontrolü
            if last_direction == "increased":
                reversal_points.append(history[-1])
                print("   *** YÖN DEĞİŞİMİ (REVERSAL) TESPİT EDİLDİ! ***")
            last_direction = "decreased"
        else:
            print("   [Seri Devam Ediyor] Işık seviyesi sabit tutuldu.")
            # Seviye değişmediği için yön nötr kalır
            
    # --- DURUM B: IŞIK RAHATSIZ ETMEDİ (YANLIŞ YANIT) ---
    elif key == "down":
        print(f"-> Tepki: RAHATSIZ ETMEDİ (0) -> Işık hemen {step} lx artırılıyor.")
        current_value += step
        consecutive_correct = 0  # Tek bir hatada seri tamamen sıfırlanır
        
        # Yön Değişimi (Reversal) Kontrolü
        if last_direction == "decreased":
            reversal_points.append(history[-1])
            print("   *** YÖN DEĞİŞİMİ (REVERSAL) TESPİT EDİLDİ! ***")
        last_direction = "increased"

    # --- 3. GÜVENLİK SINIRLARI (0-100 lx Dışına Çıkma) ---
    if current_value < MIN_VAL:
        current_value = MIN_VAL
    elif current_value > MAX_VAL:
        current_value = MAX_VAL

# ==========================================
# 4. TEST SONU VE THRESHOLD HESAPLAMA
# ==========================================
print("\n" + "=" * 60)
print("  DENEY BAŞARIYLA TAMAMLANDI!")
print("=" * 60)

print("Gerçekleşen Tüm Yön Değişimleri (Reversals):")
if reversal_points:
    print(f"  { [round(x, 2) for x in reversal_points] } lx")
    # Bilimsel yöntem: Eğer 2'den fazla reversal varsa ilkini alışma evresi diye eleriz
    if len(reversal_points) > 2:
        final_reversals = reversal_points[1:]
        print("  (İlk yön değişimi ısınma turları olduğu için elendi.)")
    else:
        final_reversals = reversal_points
        
    threshold = sum(final_reversals) / len(final_reversals)
    print(f"\nHesaplanan Eşik Değeri (%79.4 Rahatsızlık): {threshold:.2f} lx")
else:
    print("  Hiç yön değişimi gerçekleşmedi (Katılımcı hep aynı tuşa basmış olabilir).")
    threshold = sum(history[-5:]) / 5
    print(f"\nHesaplanan Eşik Değeri (Son 5 adımın ortalaması): {threshold:.2f} lx")

print("=" * 60)