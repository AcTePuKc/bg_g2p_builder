import csv
import re
from pathlib import Path
from phonemizer import phonemize
from phonemizer.backend.espeak.wrapper import EspeakWrapper

# ==========================================
# --- CONFIGURATION / НАСТРОЙКИ ---
# ==========================================

# 1. Език за Espeak (напр. 'bg', 'en', 'pt', 'pt-br')
ESPEAK_LANGUAGE = "bg"

# 2. Път до Espeak DLL (Само за Windows)
# Ако сте на Linux, оставете го както е (няма да се ползва, ако не съществува).
ESPEAK_LIB_PATH = r"C:\Program Files\eSpeak NG\libespeak-ng.dll"

# 3. Файлове
HERE = Path(__file__).resolve().parent
OUTPUT_DIR = HERE / "output"

WIKI_FILE = OUTPUT_DIR / "source_wiktionary_ipa.tsv"
CHITANKA_FILE = OUTPUT_DIR / "source_chitanka_stress.tsv"
RAW_LEXICON = OUTPUT_DIR / "lexicon_raw.tsv"

# ==========================================
# --- КРАЙ НА НАСТРОЙКИТЕ ---
# ==========================================

def fix_phonology(ipa: str) -> str:
    """
    Нормализира IPA към българския стандарт.
    ЗАБЕЛЕЖКА: Ако ползвате скрипта за друг език, изчистете тази функция!
    """
    if not ipa:
        return ""
    
    # 1. Замяна на шва (ə) с ɤ (за буквата 'ъ') - BG Specific
    ipa = ipa.replace('ə', 'ɤ')
    
    # 2. Махане на руското 'ы' (ɨ) -> i - BG Specific
    ipa = ipa.replace('ɨ', 'i')
    
    # 3. Стандартизация на g
    ipa = ipa.replace('g', 'ɡ')
    
    # 4. Чистене на излишни знаци (дължини, вторични ударения)
    ipa = ipa.replace('ː', '').replace('ˌ', '')
    
    # 5. Премахване на двойни интервали
    ipa = re.sub(r"\s+", " ", ipa).strip()
    
    return ipa

def main():
    # 1. Инициализация на Espeak
    try:
        if Path(ESPEAK_LIB_PATH).exists():
            EspeakWrapper.set_library(ESPEAK_LIB_PATH)
            print(f"[INFO] Espeak DLL зареден: {ESPEAK_LIB_PATH}")
    except Exception:
        print("[WARNING] Espeak DLL не е намерен. Скриптът ще разчита на системния PATH.")

    final_dataset = {} # word -> set(ipa)

    # ---------------------------------------------------------
    # ЕТАП 1: Wiktionary (Най-висок приоритет)
    # ---------------------------------------------------------
    print("[ETAP 1] Зареждане на Wiktionary (IPA)...")
    if WIKI_FILE.exists():
        with open(WIKI_FILE, "r", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter="\t")
            next(reader, None)
            for row in reader:
                if not row: 
                    continue
                word, raw_ipa = row[0], row[1]
                
                good_ipa = fix_phonology(raw_ipa)
                if word not in final_dataset: 
                    final_dataset[word] = set()
                final_dataset[word].add(good_ipa)
    else:
        print(f"[WARNING] Няма файл {WIKI_FILE}. Пропуснат Етап 1.")

    # ---------------------------------------------------------
    # ЕТАП 2: Chitanka (Ударения -> Espeak)
    # ---------------------------------------------------------
    print("[ETAP 2] Генерация чрез Espeak...")
    
    words_to_gen = []
    original_map = [] # Пазим коя е базовата дума за всеки запис
    
    if CHITANKA_FILE.exists():
        with open(CHITANKA_FILE, "r", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter="\t")
            next(reader, None)
            for row in reader:
                if not row: 
                    continue
                base, stressed = row[0], row[1]
                
                # Ако думата вече я има от Wiktionary, пропускаме я (там е по-точна)
                if base in final_dataset: 
                    continue
                
                words_to_gen.append(stressed)
                original_map.append(base)
    else:
         print(f"[WARNING] Няма файл {CHITANKA_FILE}. Пропуснат Етап 2.")
    
    print(f" -> Ще се генерират {len(words_to_gen)} думи...")

    # Batch генерация (по-бързо)
    if words_to_gen:
        try:
            # Използваме променливата ESPEAK_LANGUAGE
            ipas = phonemize(
                words_to_gen, 
                language=ESPEAK_LANGUAGE, 
                backend='espeak', 
                strip=True, 
                with_stress=True, 
                njobs=4
            )
            
            for i, raw_ipa in enumerate(ipas):
                base = original_map[i]
                good_ipa = fix_phonology(raw_ipa)
                
                if base not in final_dataset: 
                    final_dataset[base] = set()
                final_dataset[base].add(good_ipa)
        except Exception as e:
            print(f"[ERROR] Espeak грешка: {e}")
            print("Съвет: Проверете дали сте инсталирали espeak-ng!")

    # ---------------------------------------------------------
    # ЗАПИС
    # ---------------------------------------------------------
    print(f"[INFO] Записване в {RAW_LEXICON}...")
    with open(RAW_LEXICON, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        for word in sorted(final_dataset.keys()):
            for ipa in final_dataset[word]:
                writer.writerow([word, ipa])

    print("[SUCCESS] Lexicon built.")

if __name__ == "__main__":
    main()