import requests
import json
import csv
import re
from pathlib import Path
from tqdm import tqdm
from datasets import load_dataset

# ==========================================
# --- CONFIGURATION / НАСТРОЙКИ ---
# ==========================================

# 1. Wiktionary (Kaikki.org)
KAIKKI_URL = "https://kaikki.org/dictionary/Bulgarian/kaikki.org-dictionary-Bulgarian.jsonl"

# 2. Hugging Face Dataset (Stress Data)
HF_DATASET_ID = "vislupus/alpaca-bulgarian-dictionary"

# 3. Regex за парсване на HF dataset-а
HF_REGEX_PATTERN = r"Дума:\s*([^\s(]+)\s*\(([^)]+)\)"

# 4. Пътища и файлове
HERE = Path(__file__).resolve().parent
OUTPUT_DIR = HERE / "output"
LOCAL_JSONL = OUTPUT_DIR / "bg_kaikki.jsonl"

WIKI_IPA_FILE = OUTPUT_DIR / "source_wiktionary_ipa.tsv"
CHITANKA_STRESS_FILE = OUTPUT_DIR / "source_chitanka_stress.tsv"

# ==========================================
# --- КРАЙ НА НАСТРОЙКИТЕ ---
# ==========================================

OUTPUT_DIR.mkdir(exist_ok=True)

def download_kaikki():
    """Сваля речника от Wiktionary (Kaikki)"""
    if LOCAL_JSONL.exists():
        print("[INFO] Wiktionary JSONL вече е свален.")
        return

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

def process_wiktionary():
    """Вади IPA от сваления JSONL файл"""
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
                
                # Филтър за фрази
                if not word or " " in word: 
                    continue 

                if "sounds" in entry:
                    for sound in entry["sounds"]:
                        if "ipa" in sound:
                            # Почистване на скобите /.../ или [...]
                            ipa = sound["ipa"].replace("/", "").replace("[", "").replace("]", "").strip()
                            if ipa:
                                writer.writerow([word, ipa])
                                count += 1
            except Exception: 
                # Пропускаме редове, които са счупен JSON или нямат нужната структура
                continue
                
    print(f" -> Извлечени {count} записа с IPA от Wiktionary.")

def process_chitanka():
    """Сваля dataset с ударения от Hugging Face"""
    print(f"[INFO] Сваляне и обработка на dataset: {HF_DATASET_ID}...")
    try:
        ds = load_dataset(HF_DATASET_ID, split="train")
    except Exception as e:
        print(f"[ERROR] Не може да се зареди dataset-а: {e}")
        return

    extract_re = re.compile(HF_REGEX_PATTERN, re.IGNORECASE)
    
    count = 0
    with open(CHITANKA_STRESS_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["word", "stressed_word"])
        
        for row in ds:
            text = row.get("input", "")
            match = extract_re.search(text)
            if match:
                base_word = match.group(1).lower().strip()
                stressed_word = match.group(2).split(",")[0].split(" ")[0].lower().strip()
                
                if base_word and stressed_word:
                    writer.writerow([base_word, stressed_word])
                    count += 1
    print(f" -> Извлечени {count} думи с ударения.")

if __name__ == "__main__":
    download_kaikki()
    process_wiktionary()
    process_chitanka()