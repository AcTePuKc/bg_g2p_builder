import requests
import json
import csv
import re
from pathlib import Path
from tqdm import tqdm
from datasets import load_dataset
from collections import defaultdict

# --- КОНФИГУРАЦИЯ ---
HERE = Path(__file__).resolve().parent
OUTPUT_DIR = HERE / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# 1. Wiktionary URL (Kaikki.org)
# Ако този линк умре, търсете "Kaikki Bulgarian JSONL"
KAIKKI_URL = "https://kaikki.org/dictionary/Bulgarian/kaikki.org-dictionary-Bulgarian.jsonl"
LOCAL_JSONL = OUTPUT_DIR / "bg_kaikki.jsonl"

# 2. Файлове за запис
WIKI_IPA_FILE = OUTPUT_DIR / "source_wiktionary_ipa.tsv"
CHITANKA_STRESS_FILE = OUTPUT_DIR / "source_chitanka_stress.tsv"

def download_kaikki():
    if LOCAL_JSONL.exists():
        print("[INFO] Wiktionary JSONL вече е свален.")
        return

    print(f"[INFO] Сваляне на Wiktionary данни от {KAIKKI_URL}...")
    try:
        with requests.get(KAIKKI_URL, stream=True) as r:
            r.raise_for_status()
            total_size = int(r.headers.get('content-length', 0))
            with open(LOCAL_JSONL, 'wb') as f, tqdm(total=total_size, unit='B', unit_scale=True) as bar:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
                    bar.update(len(chunk))
        print("[SUCCESS] Wiktionary свален.")
    except Exception as e:
        print(f"[ERROR] Грешка при сваляне: {e}")

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
                    continue # Без фрази

                if "sounds" in entry:
                    for sound in entry["sounds"]:
                        if "ipa" in sound:
                            ipa = sound["ipa"].replace("/", "").replace("[", "").replace("]", "").strip()
                            if ipa:
                                writer.writerow([word, ipa])
                                count += 1
            except: 
                continue
    print(f" -> Извлечени {count} записа с IPA от Wiktionary.")

def process_chitanka():
    print("[INFO] Сваляне и обработка на Chitanka/Alpaca dataset...")
    try:
        # Ако HuggingFace dataset-ът изчезне, потърсете друг източник за "Bulgarian Spellcheck"
        ds = load_dataset("vislupus/alpaca-bulgarian-dictionary", split="train")
    except Exception as e:
        print(f"[ERROR] Не може да се зареди dataset-а: {e}")
        return

    # Regex за вадене на дума с ударение: "Дума: дума (ду`ма)"
    extract_re = re.compile(r"Дума:\s*([^\s(]+)\s*\(([^)]+)\)", re.IGNORECASE)
    
    count = 0
    with open(CHITANKA_STRESS_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["word", "stressed_word"])
        
        for row in ds:
            text = row.get("input", "")
            match = extract_re.search(text)
            if match:
                base_word = match.group(1).lower().strip()
                # Взимаме първата дума в скобите (понякога са изброени няколко)
                stressed_word = match.group(2).split(",")[0].split(" ")[0].lower().strip()
                
                # Валидация
                if base_word and stressed_word:
                    writer.writerow([base_word, stressed_word])
                    count += 1
    print(f" -> Извлечени {count} думи с ударения от Chitanka.")

if __name__ == "__main__":
    download_kaikki()
    process_wiktionary()
    process_chitanka()