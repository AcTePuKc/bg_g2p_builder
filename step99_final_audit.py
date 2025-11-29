import csv
from pathlib import Path
from collections import Counter

# --- КОНФИГУРАЦИЯ ---
HERE = Path(__file__).resolve().parent
INPUT_FILE = HERE / "lexicon.tsv"

def main():
    if not INPUT_FILE.exists():
        print(f"[ERROR] Файлът липсва: {INPUT_FILE}")
        print("Първо изпълнете стъпки 1, 2 и 3!")
        return
    
    # 1. Събираме статистика
    char_counter = Counter()
    total_lines = 0
    
    print(f"[INFO] Одитиране на {INPUT_FILE.name}...")
    
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        
        for row in reader:
            if not row: 
                continue
            ipa = row[1]
            total_lines += 1
            
            # Броим всеки знак
            for char in ipa:
                char_counter[char] += 1

    # 2. Принтираме резултата
    print("\n" + "="*40)
    print(f"--- СТАТИСТИКА НА СИМВОЛИТЕ ---")
    print(f"Общо редове: {total_lines}")
    print(f"Уникални символи: {len(char_counter)}")
    print("-" * 40)
    
    # Сортираме по честота
    for char, count in char_counter.most_common():
        # Показваме Unicode кода за прецизност
        print(f"'{char}' (U+{ord(char):04X}) : {count}")
    
    print("="*40)
    
    # 3. Автоматична проверка за грешки
    errors = []
    
    # Проверка за кирилица в IPA
    for char in char_counter:
        if ord(char) > 0x0400: 
            errors.append(f"Открита кирилица: '{char}'")
    
    # Проверка за специфични грешки
    if 'ə' in char_counter: 
        errors.append("Открито шва 'ə' (трябва да е ɤ)")
    if 'ts' in char_counter: 
        errors.append("Открито 'ts' без tie-bar")
    if 'nan' in char_counter: 
        errors.append("Открита грешка 'nan'")
    if '(' in char_counter: 
        errors.append("Открити скоби ( )")

    if errors:
        print("\n[FAIL] ❌ ОТКРИТИ СА ПРОБЛЕМИ:")
        for e in errors:
            print(f" - {e}")
    else:
        print("\n[PASS] ✅ Файлът изглежда чист и валиден!")

if __name__ == "__main__":
    main()