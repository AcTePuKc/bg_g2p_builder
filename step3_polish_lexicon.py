import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent
INPUT_FILE = HERE / "output" / "lexicon_raw.tsv"
OUTPUT_FILE = HERE / "lexicon.tsv"

# Твоята нова азбука с Tie-Bars и специфично Щ
ALPHABET_IPA = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "ɡ",
    "д": "d",
    "е": "ɛ",
    "ж": "ʒ",
    "з": "z",
    "и": "i",
    "й": "j",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "ɔ",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "x",
    "ц": "t͡s",   # С tie-bar
    "ч": "t͡ʃ",   # С tie-bar
    "ш": "ʃ",
    "щ": "ʃt͡ʃ",  # Твоят вариант
    "ъ": "ɤ",
    "ь": "",     # Ер малък - без звук (или мекост, която моделът учи от контекста)
    "ю": "ju",
    "я": "ja"
}

def is_garbage(word):
    """Филтър за боклук (наставки, празни редове)"""
    if word.startswith("-") or word.endswith("-"): 
        return True
    if not word.strip(): 
        return True
    return False

def apply_custom_phonology(word, ipa):
    """
    Прилага специфичните поправки върху целия речник:
    1. Оправя африкатите (ts -> t͡s)
    2. Оправя Щ (ʃt -> ʃt͡ʃ), ако думата има 'щ'
    """
    if not ipa: 
        return ""

    # 1. Оправяне на Ц и Ч (добавяне на tie-bar)
    # Търсим ts, което НЕ е вече t͡s
    if "ts" in ipa and "t͡s" not in ipa:
        ipa = ipa.replace("ts", "t͡s")
    
    # Търсим tʃ, което НЕ е вече t͡ʃ
    if "tʃ" in ipa and "t͡ʃ" not in ipa:
        ipa = ipa.replace("tʃ", "t͡ʃ")

    # 2. Оправяне на Щ (само ако думата съдържа буквата 'щ')
    if "щ" in word:
        # Стандартният Espeak дава ʃt. Ние искаме ʃt͡ʃ
        # Внимаваме да не заменим нещо, което вече е оправено
        if "ʃt" in ipa and "ʃt͡ʃ" not in ipa:
             ipa = ipa.replace("ʃt", "ʃt͡ʃ")
    
    return ipa

def main():
    if not INPUT_FILE.exists():
        print("[ERROR] Липсва lexicon_raw.tsv. Пусни Step 2!")
        return

    print("[INFO] Финално полиране (Affricates, SHT fix, Lowercase)...")
    
    final_dict = {}

    # 1. Четене и почистване
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        for row in reader:
            if not row: 
                continue
            word = row[0].strip().lower()
            ipa = row[1].strip()
            
            if not is_garbage(word):
                # Прилагаме новите правила
                new_ipa = apply_custom_phonology(word, ipa)
                final_dict[word] = new_ipa

    # 2. Добавяне на азбуката (единичните букви)
    for letter, ipa in ALPHABET_IPA.items():
        if letter not in final_dict:
            final_dict[letter] = ipa
        else:
            # Ако буквата я има, но е с различно IPA от нашето желано, презаписваме я
            # (за да сме сигурни, че 'щ' е ʃt͡ʃ, а не ʃt)
            final_dict[letter] = ipa

    # 3. Сортиране и запис
    sorted_words = sorted(final_dict.keys())
    
    count = 0
    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        for word in sorted_words:
            writer.writerow([word, final_dict[word]])
            count += 1

    print(f"[SUCCESS] Готово! Финален файл: {OUTPUT_FILE}")
    print(f" -> Общо думи: {count}")
    print(f" -> Правила: щ=ʃt͡ʃ, ц=t͡s, ч=t͡ʃ")

if __name__ == "__main__":
    main()