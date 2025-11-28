import requests
import json
import csv
import re
from pathlib import Path
from tqdm import tqdm
from datasets import load_dataset
from collections import defaultdict

# ==========================================
# --- CONFIGURATION / НАСТРОЙКИ ---
# ==========================================

KAIKKI_URL = "https://kaikki.org/dictionary/Bulgarian/kaikki.org-dictionary-Bulgarian.jsonl"
HF_DATASET_ID = "vislupus/alpaca-bulgarian-dictionary"
HF_REGEX_PATTERN = r"Дума:\s*([^\s(]+)\s*\(([^)]+)\)"

HERE = Path(__file__).resolve().parent
OUTPUT_DIR = HERE / "output"
LOCAL_JSONL = OUTPUT_DIR / "bg_kaikki.jsonl"

WIKI_IPA_FILE = OUTPUT_DIR / "source_wiktionary_ipa.tsv"
CHITANKA_STRESS_FILE = OUTPUT_DIR / "source_chitanka_stress.tsv"
# Този файл е само за твоя справка, за да видиш омографите:
HOMOGRAPHS_DEBUG_FILE = OUTPUT_DIR / "debug_detected_homographs.tsv"

# ==========================================

OUTPUT_DIR.mkdir(exist_ok=True)

def download_kaikki():
    """Сваля речника от Wiktionary (Kaikki), само ако го няма."""
    
    # ПРОВЕРКА: Съществува ли файлът и има ли данни в него?
    if LOCAL_JSONL.exists():
        file_size_mb = LOCAL_JSONL.stat().st_size / (1024 * 1024)
        if file_size_mb > 0:
            print(f"[INFO] Wiktionary JSONL е наличен ({file_size_mb:.2f} MB). Пропускам сваляне.")
            return
        else:
            print("[WARNING] Намерен е празен/счупен файл. Ще сваля наново.")
    
    # СЪЩИНСКО СВАЛЯНЕ
    print(f"[INFO] Сваляне на Wiktionary данни от {KAIKKI_URL}...")
    try:
        with requests.get(KAIKKI_URL, stream=True) as r:
            r.raise_for_status()
            total_size = int(r.headers.get('content-length', 0))
            
            with open(LOCAL_JSONL, 'wb') as f, tqdm(total=total_size, unit='B', unit_scale=True, desc="Download Kaikki") as bar:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
                    bar.update(len(chunk))
        print("[SUCCESS] Wiktionary свален.")
    except Exception as e:
        print(f"[ERROR] Грешка при сваляне: {e}")
        # Ако гръмне, трием счупения файл, за да не пречи следващия път
        if LOCAL_JSONL.exists():
            LOCAL_JSONL.unlink()

def process_wiktionary():
    print("[INFO] Обработка на Wiktionary...")
    count = 0
    with open(LOCAL_JSONL, "r", encoding="utf-8") as f_in, \
         open(WIKI_IPA_FILE, "w", encoding="utf-8", newline="") as f_out:
        
        writer = csv.writer(f_out, delimiter="\t")
        writer.writerow(["word", "ipa"])
        
        for line in f_in:
            if not line.strip(): 
                continue
            try:
                entry = json.loads(line)
                word = entry.get("word", "").strip()
                if not word or " " in word: 
                    continue 

                if "sounds" in entry:
                    for sound in entry["sounds"]:
                        if "ipa" in sound:
                            ipa = sound["ipa"].replace("/", "").replace("[", "").replace("]", "").strip()
                            if ipa:
                                writer.writerow([word, ipa])
                                count += 1
            except Exception: 
                continue
    print(f" -> Извлечени {count} записа от Wiktionary.")

def process_chitanka():
    """
    Тази функция вече е 'умна'. Тя събира всички варианти за една дума
    и записва всички тях, за да хванем омографите (вълна/вълна).
    """
    print(f"[INFO] Обработка на Chitanka/Alpaca dataset...")
    try:
        ds = load_dataset(HF_DATASET_ID, split="train")
    except Exception as e:
        print(f"[ERROR] Грешка с Dataset: {e}")
        return

    extract_re = re.compile(HF_REGEX_PATTERN, re.IGNORECASE)
    
    # Речник: дума -> множество от ударени форми
    # "вълна" -> {"въ`лна", "вълна`"}
    word_map = defaultdict(set)
    
    for row in ds:
        text = row.get("input", "")
        match = extract_re.search(text)
        if match:
            base_word = match.group(1).lower().strip()
            stressed_word = match.group(2).split(",")[0].split(" ")[0].lower().strip()
            
            if base_word and stressed_word:
                word_map[base_word].add(stressed_word)

    # Записване
    count = 0
    homographs = 0
    
    with open(CHITANKA_STRESS_FILE, "w", encoding="utf-8", newline="") as f_out, \
         open(HOMOGRAPHS_DEBUG_FILE, "w", encoding="utf-8", newline="") as f_debug:
        
        writer = csv.writer(f_out, delimiter="\t")
        debug_writer = csv.writer(f_debug, delimiter="\t")
        
        writer.writerow(["word", "stressed_word"])
        debug_writer.writerow(["word", "count", "variants"])
        
        for word, variants in word_map.items():
            sorted_variants = sorted(list(variants))
            
            # Ако има повече от 1 вариант -> ОМОГРАФ!
            if len(sorted_variants) > 1:
                homographs += 1
                debug_writer.writerow([word, len(sorted_variants), "; ".join(sorted_variants)])
            
            # Записваме ВСИЧКИ варианти в основния файл, за да ги обработи Step 2
            for v in sorted_variants:
                writer.writerow([word, v])
                count += 1
                
    print(f" -> Запазени {count} форми от Chitanka.")
    print(f" -> Открити {homographs} потенциални омографа (виж {HOMOGRAPHS_DEBUG_FILE.name}).")

if __name__ == "__main__":
    download_kaikki()
    process_wiktionary()
    process_chitanka()