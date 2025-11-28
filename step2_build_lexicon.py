import csv
import re
from pathlib import Path
from phonemizer import phonemize
from phonemizer.backend.espeak.wrapper import EspeakWrapper

# --- CONFIGURATION ---
ESPEAK_LANGUAGE = "bg"
ESPEAK_LIB_PATH = r"C:\Program Files\eSpeak NG\libespeak-ng.dll"

HERE = Path(__file__).resolve().parent
OUTPUT_DIR = HERE / "output"
WIKI_FILE = OUTPUT_DIR / "source_wiktionary_ipa.tsv"
CHITANKA_FILE = OUTPUT_DIR / "source_chitanka_stress.tsv"
RAW_LEXICON = OUTPUT_DIR / "lexicon_raw.tsv"

def fix_phonology(ipa: str) -> str:
    if not ipa: 
        return ""
    # BG Specific fixes
    ipa = ipa.replace('ə', 'ɤ')
    ipa = ipa.replace('ɨ', 'i')
    ipa = ipa.replace('g', 'ɡ')
    ipa = ipa.replace('ː', '').replace('ˌ', '')
    ipa = re.sub(r"\s+", " ", ipa).strip()
    return ipa

def main():
    try:
        if Path(ESPEAK_LIB_PATH).exists():
            EspeakWrapper.set_library(ESPEAK_LIB_PATH)
            print(f"[INFO] Espeak DLL зареден.")
    except Exception:
        print("[WARNING] Espeak DLL не е намерен.")

    # Използваме SET за да пазим уникални IPA за всяка дума
    final_dataset = {} # word -> set(ipa)

    # 1. Wiktionary
    print("[ETAP 1] Зареждане на Wiktionary...")
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

    # 2. Chitanka (Stress)
    print("[ETAP 2] Генерация чрез Espeak (вкл. омографи)...")
    
    words_to_gen = []
    original_map = [] 
    
    if CHITANKA_FILE.exists():
        with open(CHITANKA_FILE, "r", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter="\t")
            next(reader, None)
            for row in reader:
                if not row: 
                    continue
                base, stressed = row[0], row[1]
                
                words_to_gen.append(stressed)
                original_map.append(base)
    
        print(f" -> Ще се генерират {len(words_to_gen)} думи...")

        if words_to_gen:
            try:
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

    # Запис
    print(f"[INFO] Записване в {RAW_LEXICON}...")
    with open(RAW_LEXICON, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        for word in sorted(final_dataset.keys()):
            for ipa in sorted(list(final_dataset[word])): # Сортирани IPA варианти
                writer.writerow([word, ipa])

    print("[SUCCESS] Lexicon built.")

if __name__ == "__main__":
    main()