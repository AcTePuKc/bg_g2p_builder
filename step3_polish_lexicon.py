import csv
import re
from pathlib import Path
from collections import defaultdict

HERE = Path(__file__).resolve().parent
INPUT_FILE = HERE / "output" / "lexicon_raw.tsv"
OUTPUT_FILE = HERE / "lexicon.tsv"

# Азбука (за да сме сигурни, че единичните букви са там)
ALPHABET_IPA = {
    "а": "a", "б": "b", "в": "v", "г": "ɡ", "д": "d", "е": "ɛ",
    "ж": "ʒ", "з": "z", "и": "i", "й": "j", "к": "k", "л": "l",
    "м": "m", "н": "n", "о": "ɔ", "п": "p", "р": "r", "с": "s",
    "т": "t", "у": "u", "ф": "f", "х": "x", "ц": "t͡s", 
    "ч": "t͡ʃ", "ш": "ʃ", "щ": "ʃt͡ʃ", "ъ": "ɤ", "ь": "", 
    "ю": "ju", "я": "ja"
}

def is_garbage(word, ipa):
    """Строг филтър за боклук"""
    # 1. Ако думата започва/завършва с тире
    if word.startswith("-") or word.endswith("-"): 
        return True
    # 2. Ако IPA съдържа грешка 'nan' (Not a Number)
    if "nan" in ipa: 
        return True
    # 3. Празни
    if not word.strip() or not ipa.strip(): 
        return True
    return False

def clean_ipa_artifacts(ipa):
    """
    Дълбоко почистване на IPA символите.
    """
    # 1. Махаме маркери за език: (bg), (en)
    ipa = re.sub(r"\([a-z]{2}\)", "", ipa)
    
    # 2. Махаме скобите
    ipa = ipa.replace("(", "").replace(")", "")
    
    # 3. Махаме диакритики и артефакти (открити при одита)
    # U+031F (Plus sign below - ̟)
    # U+032F (Inverted breve below - ̯)
    # U+031E (Down tack - ̞)
    ipa = ipa.replace("\u031f", "").replace("\u032f", "").replace("\u031e", "")

    # 4. Странният символ ɟ (вероятно грешка за g или d) -> правим го на g
    ipa = ipa.replace("ɟ", "ɡ")
    
    # 5. Уеднаквяване на палатализация: ʲ -> j
    ipa = ipa.replace("ʲ", "j")
    
    # 6. Махаме излишни интервали
    ipa = ipa.replace(" ", "")
    
    return ipa

def apply_custom_phonology(word, ipa):
    """
    Прилага специфичните поправки (Affricates)
    """
    if not ipa: 
        return ""

    # Първо чистим артефактите
    ipa = clean_ipa_artifacts(ipa)

    # 1. Оправяне на Ц (ts -> t͡s)
    if "ts" in ipa and "t͡s" not in ipa:
        ipa = ipa.replace("ts", "t͡s")

    # 2. Оправяне на Ч (tʃ -> t͡ʃ)
    if "tʃ" in ipa and "t͡ʃ" not in ipa:
        ipa = ipa.replace("tʃ", "t͡ʃ")

    # 3. Оправяне на ДЖ (dʒ -> d͡ʒ) - НОВО!
    if "dʒ" in ipa and "d͡ʒ" not in ipa:
        ipa = ipa.replace("dʒ", "d͡ʒ")

    # 4. Оправяне на Щ (ʃt -> ʃt͡ʃ) - само ако думата има 'щ'
    if "щ" in word:
        if "ʃt" in ipa and "ʃt͡ʃ" not in ipa:
             ipa = ipa.replace("ʃt", "ʃt͡ʃ")
    
    return ipa

def main():
    if not INPUT_FILE.exists():
        print("[ERROR] Липсва lexicon_raw.tsv. Пусни Step 2!")
        return

    print("[INFO] Финално полиране (Deep Clean + Affricates + Dedupe)...")
    
    final_dict = defaultdict(set)

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        for row in reader:
            if not row: 
                continue
            word = row[0].strip().lower()
            ipa = row[1].strip()
            
            if not is_garbage(word, ipa):
                new_ipa = apply_custom_phonology(word, ipa)
                if new_ipa:
                    final_dict[word].add(new_ipa)

    # Добавяне на азбуката
    for letter, ipa in ALPHABET_IPA.items():
        # Force-ваме азбуката да е точно както искаме
        final_dict[letter] = {ipa}

    # Сортиране и запис
    sorted_words = sorted(final_dict.keys())
    
    count = 0
    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        for word in sorted_words:
            # Сортираме вариантите за консистенция
            variants = sorted(list(final_dict[word]))
            for variant in variants:
                writer.writerow([word, variant])
                count += 1

    print(f"[SUCCESS] Готово! Финален файл: {OUTPUT_FILE}")
    print(f" -> Общо редове: {count}")
    print(" -> Изчистени: nan, (bg), ̟, ʲ")
    print(" -> Оправени: t͡s, t͡ʃ, d͡ʒ, ʃt͡ʃ")

if __name__ == "__main__":
    main()