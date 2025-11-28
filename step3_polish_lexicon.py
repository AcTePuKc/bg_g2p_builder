import csv
import re
from pathlib import Path
from collections import defaultdict

HERE = Path(__file__).resolve().parent
INPUT_FILE = HERE / "output" / "lexicon_raw.tsv"
OUTPUT_FILE = HERE / "lexicon.tsv"

# Твоята нова азбука с Tie-Bars и специфично Щ
ALPHABET_IPA = {
    "а": "a", "б": "b", "в": "v", "г": "ɡ", "д": "d", "е": "ɛ",
    "ж": "ʒ", "з": "z", "и": "i", "й": "j", "к": "k", "л": "l",
    "м": "m", "н": "n", "о": "ɔ", "п": "p", "р": "r", "с": "s",
    "т": "t", "у": "u", "ф": "f", "х": "x", "ц": "t͡s", 
    "ч": "t͡ʃ", "ш": "ʃ", "щ": "ʃt͡ʃ", "ъ": "ɤ", "ь": "", 
    "ю": "ju", "я": "ja"
}

def is_garbage(word):
    """Филтър за боклук"""
    # Махаме думи, започващи/завършващи с тире (освен ако не е нещо като 'по-')
    if word.startswith("-") or word.endswith("-"): 
        return True
    
    # Махаме очевидни OCR грешки като "аа-я" (освен ако не решиш да ги пазиш)
    if word == "аа-я": 
        return True
    
    if not word.strip(): 
        return True
    return False

def clean_ipa_artifacts(ipa):
    """
    Маха Espeak маркери като (en), (bg) и оправя структурата.
    Пример: (en)sˈi(bɡ)kɫˈa sɐ -> sˈikɫˈasɐ
    """
    # Махаме (en), (bg), (fr) и т.н.
    ipa = re.sub(r"\([a-z]{2}\)", "", ipa)
    
    # Махаме двойни интервали, които може да са останали след горното
    ipa = re.sub(r"\s+", " ", ipa).strip()
    return ipa

def apply_custom_phonology(word, ipa):
    """
    Прилага специфичните поправки върху целия речник:
    1. Чисти артефакти ((en))
    2. Оправя африкатите (ts -> t͡s)
    3. Оправя Щ (ʃt -> ʃt͡ʃ)
    """
    if not ipa: 
        return ""

    # 1. Чистене на (en)/(bg)
    ipa = clean_ipa_artifacts(ipa)

    # 2. Оправяне на Ц и Ч
    if "ts" in ipa and "t͡s" not in ipa:
        ipa = ipa.replace("ts", "t͡s")
    if "tʃ" in ipa and "t͡ʃ" not in ipa:
        ipa = ipa.replace("tʃ", "t͡ʃ")

    # 3. Оправяне на Щ (само ако думата съдържа буквата 'щ')
    if "щ" in word:
        if "ʃt" in ipa and "ʃt͡ʃ" not in ipa:
             ipa = ipa.replace("ʃt", "ʃt͡ʃ")
    
    return ipa

def main():
    if not INPUT_FILE.exists():
        print("[ERROR] Липсва lexicon_raw.tsv. Пусни Step 2!")
        return

    print("[INFO] Финално полиране (Deduplication + Cleaning)...")
    
    # ИЗПОЛЗВАМЕ defaultdict(set), ЗА ДА ПАЗИМ ВСИЧКИ ВАРИАНТИ!
    # word -> set(ipa1, ipa2...)
    final_dict = defaultdict(set)

    # 1. Четене
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        for row in reader:
            if not row:
                continue
            word = row[0].strip().lower()
            ipa = row[1].strip()
            
            if not is_garbage(word):
                new_ipa = apply_custom_phonology(word, ipa)
                if new_ipa:
                    final_dict[word].add(new_ipa)

    # 2. Добавяне на азбуката
    for letter, ipa in ALPHABET_IPA.items():
        # Добавяме ги. Ако вече ги има, set-ът ще игнорира дубликата.
        # Ако съществуващото IPA е различно, ще имаме 2 варианта (което е ок, или можеш да го force-неш)
        # Тук решаваме да го force-нем (да сме сигурни, че 'щ' е ʃt͡ʃ)
        final_dict[letter] = {ipa}

    # 3. Сортиране и запис
    sorted_words = sorted(final_dict.keys())
    
    count = 0
    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        
        for word in sorted_words:
            # Сортираме и IPA вариантите за консистенция
            variants = sorted(list(final_dict[word]))
            for variant in variants:
                writer.writerow([word, variant])
                count += 1

    print(f"[SUCCESS] Готово! Финален файл: {OUTPUT_FILE}")
    print(f" -> Общо редове: {count}")
    print(f" -> Омографите (вълна/вълна) са запазени.")
    print(f" -> Артефакти като (en)/(bg) са премахнати.")

if __name__ == "__main__":
    main()