import csv
import re
from collections import defaultdict
from pathlib import Path
from phonemizer import phonemize
from phonemizer.backend.espeak.wrapper import EspeakWrapper

ESPEAK_LANGUAGE = "bg"
ESPEAK_LIB_PATH = r"C:\Program Files\eSpeak NG\libespeak-ng.dll"
BAD_IPA_MARKERS = {"nˈanbɡ", "nˈanbg", "nanbɡ", "nanbg"}

HERE = Path(__file__).resolve().parent
OUTPUT_DIR = HERE / "output"
WIKI_FILE = OUTPUT_DIR / "source_wiktionary_ipa.tsv"
CHITANKA_FILE = OUTPUT_DIR / "source_chitanka_stress.tsv"
RAW_LEXICON = OUTPUT_DIR / "lexicon_raw.tsv"
FAILED_FILE = OUTPUT_DIR / "debug_espeak_failed.tsv"
MFA_FILE = OUTPUT_DIR / "source_mfa_ipa.tsv"
BGOS_FILE = OUTPUT_DIR / "source_bgospodinov_word_stress.tsv"
BGOS_ONLY_NORMATIVE = True
BGOS_LIMIT = 0  # 0 = без лимит


def ipa_quality_score(ipa: str) -> float:
    score = 0.0
    stress_count = ipa.count("ˈ")
    if stress_count == 1:
        score += 100.0
    else:
        score -= 25.0 * abs(stress_count - 1)

    score += ipa.count("ɐ") * 2.0
    score += ipa.count("ɤ") * 2.0
    score -= ipa.count("a") * 0.25
    score -= ipa.count("o") * 0.25
    score -= ipa.count("e") * 0.25
    score -= ipa.count("g") * 2.0

    if "͡" in ipa or "-" in ipa:
        score -= 20.0
    if ipa.endswith(("ˈɤ", "ˈa", "ˈɔ", "ˈu", "ˈi", "ˈɛ")):
        score -= 10.0

    return score


def select_direct_candidate(candidates):
    return max(
        sorted(set(candidates)),
        key=lambda ipa: (ipa_quality_score(ipa), -len(ipa), ipa),
    )


def select_generated_candidate(candidates, direct_candidates):
    direct_candidates = set(direct_candidates)

    def sort_key(item):
        priority, stressed, ipa = item
        matches_direct = 1 if ipa in direct_candidates else 0
        return (matches_direct, priority, ipa_quality_score(ipa), stressed, ipa)

    return max(candidates, key=sort_key)[2]


def parse_bgospodinov_row(row):
    if not row or len(row) < 2:
        return None
    word = row[0].strip().lower()
    stressed = row[1].strip()
    is_norm = None
    if len(row) >= 3:
        v = row[2].strip()
        if v.isdigit():
            is_norm = int(v)
    if not word or not stressed:
        return None
    return word, stressed, is_norm


def fix_phonology(ipa: str) -> str:
    if not ipa:
        return ""
    ipa = ipa.replace('ə', 'ɤ')
    ipa = ipa.replace('ɨ', 'i')
    ipa = ipa.replace('g', 'ɡ')
    ipa = ipa.replace('ː', '').replace('ˌ', '')
    ipa = re.sub(r"\s+", " ", ipa).strip()
    return ipa


def main():
    try:
        if Path(ESPEAK_LIB_PATH).exists():
            EspeakWrapper.set_library(ESPEAK_LIB_PATH)
            print("[INFO] Espeak DLL зареден.")
    except Exception:
        print("[WARNING] Espeak DLL не е намерен.")

    final_dataset = {}
    failed_rows = []
    direct_candidates = defaultdict(set)
    generated_candidates = defaultdict(list)

    # --- ЕТАП 1: Директно IPA (Wiktionary & MFA) ---
    print("[ETAP 1] Зареждане на Wiktionary...")
    if WIKI_FILE.exists():
        with open(WIKI_FILE, "r", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter="\t")
            next(reader, None)
            for row in reader:
                if not row or len(row) < 2:
                    continue
                word, raw_ipa = row[0].strip().lower(), row[1]
                if not word:
                    continue
                good_ipa = fix_phonology(raw_ipa)
                if not good_ipa:
                    continue
                direct_candidates[word].add(good_ipa)
    
    print("[ETAP 1b] Зареждане на MFA...")
    if MFA_FILE.exists():
        with open(MFA_FILE, "r", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter="\t")
            next(reader, None)
            for row in reader:
                if not row:
                    continue
                word, raw_ipa = row[0].strip().lower(), row[1]
                if not word:
                    continue
                good_ipa = fix_phonology(raw_ipa)
                if good_ipa:
                    direct_candidates[word].add(good_ipa)

    # --- ЕТАП 2: Подготовка на думи за Espeak ---
    # Тук пазим различните стресови входове като помощен сигнал за фонемизация.
    # Това не означава, че всеки такъв вариант е подходящ за финален trainable
    # G2P запис без допълнителна курация.
    words_to_gen = []
    generation_meta = []
    seen_pairs = set()

    # 2a. Chitanka
    if CHITANKA_FILE.exists():
        print("[ETAP 2a] Четене на Chitanka...")
        with open(CHITANKA_FILE, "r", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter="\t")
            next(reader, None)
            for row in reader:
                if not row or len(row) < 2:
                    continue
                base, stressed = row[0].strip().lower(), row[1].strip()
                if not base or not stressed:
                    continue

                pair = (base, stressed)
                if pair in seen_pairs:
                    continue

                seen_pairs.add(pair)
                words_to_gen.append(stressed)
                generation_meta.append((base, stressed, 1))

    # 2b. bgospodinov
    if BGOS_FILE.exists():
        print("[ETAP 2b] Четене на bgospodinov...")
        added_bgos = 0
        with open(BGOS_FILE, "r", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter="\t")
            next(reader, None)
            for row in reader:
                parsed = parse_bgospodinov_row(row)
                if not parsed:
                    continue
                base, stressed, is_norm = parsed

                if BGOS_ONLY_NORMATIVE and is_norm is not None and is_norm != 1:
                    continue

                pair = (base, stressed)
                if pair in seen_pairs:
                    continue

                seen_pairs.add(pair)
                words_to_gen.append(stressed)
                generation_meta.append((base, stressed, 2))
                added_bgos += 1

                if BGOS_LIMIT and added_bgos >= BGOS_LIMIT:
                    break
        print(f" -> Добавени {added_bgos} нови думи от bgospodinov.")

    # --- ЕТАП 3: Масова генерация чрез Espeak ---
    print(f"[INFO] Ще се генерират {len(words_to_gen)} думи общо (Chitanka + bgos)...")
    print(f"[DEBUG] unique bases queued for espeak: {len({meta[0] for meta in generation_meta})}")

    if words_to_gen:
        try:
            ipas = phonemize(
                words_to_gen,
                language=ESPEAK_LANGUAGE,
                backend='espeak',
                strip=True,
                with_stress=True,
                njobs=4
            )

            for i, raw_ipa in enumerate(ipas):
                base, stressed, priority = generation_meta[i]
                good_ipa = fix_phonology(raw_ipa)

                if good_ipa in BAD_IPA_MARKERS or not good_ipa:
                    failed_rows.append((base, stressed, raw_ipa))
                    continue

                generated_candidates[base].append((priority, stressed, good_ipa))
            print("[INFO] Фонемизацията приключи успешно.")

        except Exception as e:
            print(f"[ERROR] Espeak грешка: {e}")
            raise SystemExit(1) from e

    # Запис на грешките
    if failed_rows:
        with open(FAILED_FILE, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, delimiter="\t")
            w.writerow(["base_word", "stressed_input", "raw_output"])
            w.writerows(failed_rows)

    # --- ЕТАП 4: Избор на един каноничен IPA вариант за G2P ---
    all_words = set(direct_candidates) | set(generated_candidates)
    for word in sorted(all_words):
        if generated_candidates[word]:
            final_dataset[word] = select_generated_candidate(
                generated_candidates[word],
                direct_candidates.get(word, set()),
            )
        elif direct_candidates[word]:
            final_dataset[word] = select_direct_candidate(direct_candidates[word])

    # --- ЕТАП 4: Записване на финалния лексикон ---
    print(f"[DEBUG] unique words in final_dataset: {len(final_dataset)}")
    print(f"[INFO] Записване в {RAW_LEXICON}...")
    
    with open(RAW_LEXICON, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        for word in sorted(final_dataset.keys()):
            writer.writerow([word, final_dataset[word]])

    print("[SUCCESS] Lexicon built.")


if __name__ == "__main__":
    main()
