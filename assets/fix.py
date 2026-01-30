import csv
from pathlib import Path

# --- КОНФИГУРАЦИЯ ---
HERE = Path(__file__).resolve().parent
# Взимаме финалния лексикон
INPUT_FILE = HERE / "lexicon.tsv"
# Тук ще запишем думите за преглед
OUTPUT_FILE = HERE / "hyphens_review_list.txt"

def main():
    if not INPUT_FILE.exists():
        print("[ERROR] Няма файл lexicon.tsv!")
        return

    print(f"[INFO] Scanning for hyphenated words in {INPUT_FILE.name}...")
    
    hyphenated_count = 0
    
    with open(INPUT_FILE, "r", encoding="utf-8") as f_in, \
         open(OUTPUT_FILE, "w", encoding="utf-8") as f_out:
        
        reader = csv.reader(f_in, delimiter="\t")
        
        # Записваме хедър във файла за преглед
        f_out.write(f"{'WORD':<30} | {'IPA'}\n")
        f_out.write("-" * 60 + "\n")

        for row in reader:
            if not row: continue
            word = row[0]
            ipa = row[1]
            
            # Търсим тире
            if "-" in word:
                hyphenated_count += 1
                # Записваме го красиво подравнено
                f_out.write(f"{word:<30} | {ipa}\n")

    print("-" * 30)
    print(f"[SUCCESS] Done.")
    print(f"  Found: {hyphenated_count} hyphenated words.")
    print(f"  Check file: {OUTPUT_FILE}")
    print("-" * 30)
    print("СЪВЕТ: Отвори файла и виж кои си струва да запазим.")
    print("Търси думи, които променят звученето си при сливане (напр. жп-).")

if __name__ == "__main__":
    main()