import csv
import sys
from pathlib import Path
from collections import Counter

HERE = Path(__file__).resolve().parent
PRIMARY_INPUT = HERE / "lexicon.tsv"
LEGACY_INPUT = HERE / "lexicon_final.tsv"
ASSET_INPUT = HERE / "assets" / "lexicon.tsv"


def emit(message: str):
    text = f"{message}\n"
    encoding = sys.stdout.encoding or "utf-8"
    sys.stdout.buffer.write(text.encode(encoding, errors="replace"))


def resolve_input_file():
    for path in (PRIMARY_INPUT, LEGACY_INPUT, ASSET_INPUT):
        if path.exists():
            return path
    return PRIMARY_INPUT

def main():
    input_file = resolve_input_file()
    if not input_file.exists():
        emit(f"[ERROR] Файлът липсва: {input_file}")
        return

    char_counter = Counter()
    total_lines = 0
    words_with_sch = [] 

    emit(f"[INFO] Одит на файл: {input_file}")

    with open(input_file, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f, delimiter="\t")
        for row in reader:
            if len(row) < 2: continue
            word, ipa = row[0], row[1]
            total_lines += 1
            for ch in ipa:
                char_counter[ch] += 1
            if "щ" in word:
                words_with_sch.append((word, ipa))

    emit("")
    emit("--- СТАТИСТИКА НА СИМВОЛИТЕ ---")
    for ch, count in char_counter.most_common():
        emit(f"'{ch}' (U+{ord(ch):04X}) : {count}")

    errors = []
    
    # Проверка за tie-bar
    tie_char = "\u0361"
    if tie_char in char_counter:
        errors.append(f"ГРЕШКА: Намерен tie-bar (⁀)!")

    # Интелигентна проверка за Щ (игнорираме ударението при проверката)
    sch_fail = 0
    for w, ipa in words_with_sch:
        # ПРАВИЛО: махаме ударението само за теста, за да видим дали звуците са там
        test_ipa = ipa.replace("ˈ", "")
        if "ʃtʃ" not in test_ipa:
            sch_fail += 1
            if sch_fail < 5:
                emit(f"[DEBUG] Реална грешка при Щ: {w} -> {ipa}")
    
    if sch_fail > 0:
        errors.append(f"ГРЕШКА: {sch_fail} думи с 'щ' не съдържат 'ʃtʃ' (дори без ударение)")

    emit("")
    emit("=" * 40)
    if errors:
        emit("[FAIL] ОТКРИТИ ПРОБЛЕМИ:")
        for e in errors:
            emit(f" - {e}")
    else:
        emit("[PASS] Лексиконът е ПЕРФЕКТЕН! Всички 'щ' са оправени, символите са чисти.")
    emit("=" * 40)

if __name__ == "__main__":
    main()
