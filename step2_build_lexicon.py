import csv
import re
from pathlib import Path
from phonemizer import phonemize
from phonemizer.backend.espeak.wrapper import EspeakWrapper

# --- НАСТРОЙКИ ---
HERE = Path(__file__).resolve().parent
OUTPUT_DIR = HERE / "output"

# ПЪТ ДО ESPEAK (Променете това, ако сте на Linux или друга папка!)
# За Linux обикновено не е нужно да се задава set_library, ако е инсталиран с apt.
ESPEAK_LIB_PATH = r"C:\Program Files\eSpeak NG\libespeak-ng.dll"

# Входове
WIKI_FILE = OUTPUT_DIR / "source_wiktionary_ipa.tsv"
CHITANKA_FILE = OUTPUT_DIR / "source_chitanka_stress.tsv"
# Изход
RAW_LEXICON = OUTPUT_DIR / "lexicon_raw.tsv"

def fix_phonology(ipa: str) -> str:
    """
    Нормализира IPA към българския стандарт.
    """
    if not ipa:
        return ""
    # 1. Замяна на шва (ə) с ɤ (за буквата 'ъ')
    ipa = ipa.replace('ə', 'ɤ')
    # 2. Махане на руското 'ы' (ɨ) -> i
    ipa = ipa.replace('ɨ', 'i')
    # 3. Стандартизация на g
    ipa = ipa.replace('g', 'ɡ')
    # 4. Чистене на излишни знаци
    ipa = ipa.replace('ː', '').replace('ˌ', '')
    ipa = re.sub(r"\s+", " ", ipa).strip()
    return ipa

def main():
    # 1. Инициализация на Espeak
    try:
        if Path(ESPEAK_LIB_PATH).exists():
            EspeakWrapper.set_library(ESPEAK_LIB_PATH)
            print(f"[INFO] Espeak DLL зареден: {ESPEAK_LIB_PATH}")
    except:
        print("[WARNING] Espeak DLL не е намерен. Скриптът може да гръмне при генерация.")

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

    # ---------------------------------------------------------
    # ЕТАП 2: Chitanka (Ударения -> Espeak)
    # ---------------------------------------------------------
    print("[ETAP 2] Генерация чрез Espeak (Chitanka Stress)...")
    
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
    
    print(f" -> Ще се генерират {len(words_to_gen)} думи...")

    # Batch генерация (по-бързо)
    if words_to_gen:
        try:
            # Espeak вижда ударението в текста (напр. "ръка`") и прави правилния IPA
            ipas = phonemize(words_to_gen, language='bg', backend='espeak', strip=True, with_stress=True, njobs=4)
            
            for i, raw_ipa in enumerate(ipas):
                base = original_map[i]
                good_ipa = fix_phonology(raw_ipa)
                
                if base not in final_dataset: 
                    final_dataset[base] = set()
                final_dataset[base].add(good_ipa)
        except Exception as e:
            print(f"[ERROR] Espeak error: {e}")

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