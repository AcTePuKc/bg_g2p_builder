import requests
import json
import csv
import re
from pathlib import Path
from tqdm import tqdm
from datasets import load_dataset
from collections import defaultdict
import sqlite3
from typing import List, Optional


# ==========================================
# --- CONFIGURATION / НАСТРОЙКИ ---
# ==========================================

KAIKKI_URL = "https://kaikki.org/dictionary/Bulgarian/kaikki.org-dictionary-Bulgarian.jsonl"
HF_DATASET_ID = "vislupus/alpaca-bulgarian-dictionary"
MFA_PLAIN_DICT_URL = "https://raw.githubusercontent.com/MontrealCorpusTools/mfa-models/main/dictionary/bulgarian/mfa/bulgarian_mfa.dict"

HF_REGEX_PATTERN = r"Дума:\s*([^\s(]+)\s*\(([^)]+)\)"

HERE = Path(__file__).resolve().parent
OUTPUT_DIR = HERE / "output"
LOCAL_JSONL = OUTPUT_DIR / "bg_kaikki.jsonl"
MFA_IPA_FILE = OUTPUT_DIR / "source_mfa_ipa.tsv"
BGOS_SQLITE = OUTPUT_DIR / "bgospodinov.sqlite"
OUT_PRON = OUTPUT_DIR / "source_bgospodinov_pron.tsv"
OUT_PRON_STRESSED = OUTPUT_DIR / "source_bgospodinov_pron_stressed.tsv"
OUT_WORD_STRESS = OUTPUT_DIR / "source_bgospodinov_word_stress.tsv"

WIKI_IPA_FILE = OUTPUT_DIR / "source_wiktionary_ipa.tsv"
CHITANKA_STRESS_FILE = OUTPUT_DIR / "source_chitanka_stress.tsv"
# Този файл е само за справка: показва думи с повече от един стресов вариант,
# които после трябва да се преценят дали са trainable неоднозначности или шум.
HOMOGRAPHS_DEBUG_FILE = OUTPUT_DIR / "debug_detected_homographs.tsv"

# ==========================================

OUTPUT_DIR.mkdir(exist_ok=True)


def process_bgospodinov_sqlite():
    if not BGOS_SQLITE.exists():
        print(f"[INFO] Няма SQLite артефакт: {BGOS_SQLITE.name} (пропускам bgospodinov)")
        return

    print("[INFO] Обработка на bgospodinov SQLite...")

    con = sqlite3.connect(str(BGOS_SQLITE))
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    # Основният join според реалната схема:
    # wordform.wordform_id == pronunciation.wordform_id
    sql = """
    SELECT
        w.wordform AS word,
        w.wordform_stressed AS word_stressed,
        p.pronunciation AS pron,
        p.pronunciation_stressed AS pron_stressed,
        p.is_normative AS is_normative
    FROM wordform w
    JOIN pronunciation p ON p.wordform_id = w.wordform_id
    """

    out_pron = 0
    out_pron_stressed = 0
    out_word_stress = 0

    with open(OUT_PRON, "w", encoding="utf-8", newline="") as f1, \
         open(OUT_PRON_STRESSED, "w", encoding="utf-8", newline="") as f2, \
         open(OUT_WORD_STRESS, "w", encoding="utf-8", newline="") as f3:

        w1 = csv.writer(f1, delimiter="\t")
        w2 = csv.writer(f2, delimiter="\t")
        w3 = csv.writer(f3, delimiter="\t")

        w1.writerow(["word", "pronunciation", "is_normative"])
        w2.writerow(["word", "pronunciation_stressed", "is_normative"])
        w3.writerow(["word", "word_stressed", "is_normative"])

        for row in cur.execute(sql):
            word = row["word"]
            word_stressed = row["word_stressed"]
            pron = row["pron"]
            pron_stressed = row["pron_stressed"]
            is_normative = row["is_normative"]

            # Пази само единични думи (без интервали)
            if not isinstance(word, str):
                continue
            word = word.strip().lower()
            if not word or " " in word:
                continue

            # 1) pronunciation (unstressed)
            if isinstance(pron, str):
                p = pron.strip().replace(" ", "")
                if p:
                    w1.writerow([word, p, int(is_normative) if is_normative is not None else ""])
                    out_pron += 1

            # 2) pronunciation_stressed
            if isinstance(pron_stressed, str):
                ps = pron_stressed.strip().replace(" ", "")
                if ps:
                    w2.writerow([word, ps, int(is_normative) if is_normative is not None else ""])
                    out_pron_stressed += 1

            # 3) wordform_stressed (графемно ударение)
            if isinstance(word_stressed, str):
                ws = word_stressed.strip()
                if ws and " " not in ws:
                    w3.writerow([word, ws, int(is_normative) if is_normative is not None else ""])
                    out_word_stress += 1

    con.close()

    print(f" -> Извлечени {out_pron} записа: {OUT_PRON.name}")
    print(f" -> Извлечени {out_pron_stressed} записа: {OUT_PRON_STRESSED.name}")
    print(f" -> Извлечени {out_word_stress} записа: {OUT_WORD_STRESS.name}")

def process_mfa_plain_dict():
    print("[INFO] Обработка на MFA plain dictionary...")
    OUTPUT_DIR.mkdir(exist_ok=True)

    try:
        r = requests.get(MFA_PLAIN_DICT_URL, timeout=60)
        r.raise_for_status()
        text = r.text
    except Exception as e:
        print(f"[ERROR] MFA download failed: {e}")
        return

    count = 0
    with open(MFA_IPA_FILE, "w", encoding="utf-8", newline="") as f_out:
        w = csv.writer(f_out, delimiter="\t")
        w.writerow(["word", "ipa"])

        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # MFA .dict е: WORD  phone phone phone...
            parts = line.split()
            if len(parts) < 2:
                continue

            word = parts[0].strip().lower()
            phones = parts[1:]

            # при “по една дума” прескачаме фрази/мулти-токени
            if " " in word or "\t" in word:
                continue

            ipa = "".join(phones)  # махаме интервалите
            if ipa:
                w.writerow([word, ipa])
                count += 1

    print(f" -> Извлечени {count} записа от MFA.")


def download_kaikki():
    """Сваля речника от Wiktionary (Kaikki), само ако го няма."""

    # ПРОВЕРКА: Съществува ли файлът и има ли данни в него?
    if LOCAL_JSONL.exists():
        file_size_mb = LOCAL_JSONL.stat().st_size / (1024 * 1024)
        if file_size_mb > 0:
            print(
                f"[INFO] Wiktionary JSONL е наличен ({file_size_mb:.2f} MB). Пропускам сваляне.")
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
                            ipa = sound["ipa"].replace(
                                "/", "").replace("[", "").replace("]", "").strip()
                            if ipa:
                                writer.writerow([word, ipa])
                                count += 1
            except Exception:
                continue
    print(f" -> Извлечени {count} записа от Wiktionary.")


def process_chitanka():
    """
    Тази функция събира всички открити стресови варианти за една дума.
    Това е помощен междинен слой за G2P build-а, а не окончателен списък
    с trainable омографи за директно включване в финалния лексикон.
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
            stressed_word = match.group(2).split(
                ",")[0].split(" ")[0].lower().strip()

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

            # Ако има повече от 1 вариант, това е сигнал за потенциална
            # неоднозначност или за алтернативни форми, които после искат
            # допълнителна преценка за G2P training lexicon.
            if len(sorted_variants) > 1:
                homographs += 1
                debug_writer.writerow(
                    [word, len(sorted_variants), "; ".join(sorted_variants)])

            # Записваме всички варианти в междинния файл, за да може Step 2
            # да ги ползва като помощен сигнал при генерацията.
            for v in sorted_variants:
                writer.writerow([word, v])
                count += 1

    print(f" -> Запазени {count} форми от Chitanka.")
    print(
        f" -> Открити {homographs} думи с повече от един стресов вариант (виж {HOMOGRAPHS_DEBUG_FILE.name}).")


if __name__ == "__main__":
    download_kaikki()
    process_wiktionary()
    process_chitanka()
    process_mfa_plain_dict()
    process_bgospodinov_sqlite()
