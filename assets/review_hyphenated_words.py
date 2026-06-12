import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent
INPUT_FILE = HERE / "lexicon.tsv"
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

        f_out.write(f"{'WORD':<30} | {'IPA'}\n")
        f_out.write("-" * 60 + "\n")

        for row in reader:
            if len(row) < 2:
                continue
            word, ipa = row[0], row[1]

            if "-" in word:
                hyphenated_count += 1
                f_out.write(f"{word:<30} | {ipa}\n")

    print("-" * 30)
    print("[SUCCESS] Done.")
    print(f"  Found: {hyphenated_count} hyphenated words.")
    print(f"  Check file: {OUTPUT_FILE}")
    print("-" * 30)
    print("СЪВЕТ: Отвори файла и виж кои си струва да запазим.")
    print("Търси думи, които променят звученето си при сливане (напр. жп-).")


if __name__ == "__main__":
    main()
