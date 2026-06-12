import csv
import re
from pathlib import Path
from collections import defaultdict

HERE = Path(__file__).resolve().parent
INPUT_FILE = HERE / "output" / "lexicon_raw.tsv"
OUTPUT_FILE = HERE / "lexicon.tsv"

# Специфични "бъгове", открити от поддържащия проекта
LITERAL_FIXES = {
    "ɛrɡɔlɐm": "ɤ",    # ер голям (Ъ)
    "ɛrmɐlɤk": "j",    # ер малък (Ь)
    "ikrɐtkɔ": "j",    # и кратко (Й)
    "ikratkɔ": "j",    # вариант
    "ɔtˈinki": "",     # артефакт в края
    "ɔtmɛtki": "",     # артефакт
}
# Ръчни поправки за 95-те думи, които Espeak счупи
MANUAL_FIXES = {
    "албедо": "albˈɛdɔ", "амонтилядо": "amɔntiljˈadɔ", "антиизкуство": "antiizkˈustvɔ",
    "антипиратство": "antipirˈatstvɔ", "архитектурознание": "arxitɛkturɔznˈaniɛ",
    "балсамико": "balsˈamikɔ", "бездържавие": "bɛzdɤrʒˈaviɛ", "безславие": "bɛzslˈaviɛ",
    "бензое": "bɛnzɔˈɛ", "бетонджийство": "bɛtɔndʒˈijstvɔ", "биткаджийство": "bitkadʒˈijstvɔ",
    "блюдолизничене": "bljudɔliznˈitʃɛnɛ", "богатеене": "bɔgatɛˈɛnɛ", "борсалино": "bɔrsalˈinɔ",
    "брависимо": "bravˈisimɔ", "бушидо": "buʃidˈɔ", "бързоходство": "bɤrzɔxˈɔtstvɔ",
    "веганство": "vˈɛɡanstvɔ", "вибрато": "vibrˈatɔ", "висине": "visinˈɛ",
    "витро": "vˈitrɔ", "всеединство": "vsɛɛdˈinstvɔ", "всеоръжие": "vsɛɔrˈɤʒiɛ",
    "второзаконие": "vtɔrɔzakˈɔniɛ", "въжарство": "vɤʒˈarstvɔ", "гаспачо": "ɡaspˈatʃɔ",
    "гинко": "ɡˈinkɔ", "двойкарство": "dvɔjkˈarstvɔ", "димене": "dimˈɛnɛ",
    "добле": "dˈɔblɛ", "дохио": "dˈɔxiɔ", "дробене": "drɔbˈɛnɛ",
    "животозастраховане": "ʒivɔtɔzastraxˈɔvanɛ", "интертото": "intɛrtˈɔtɔ",
    "инферно": "infˈɛrnɔ", "кахърене": "kaxˈɤrɛnɛ", "кейнсианство": "kɛjnsiˈanstvɔ",
    "клечане": "klˈɛtʃanɛ", "коантро": "kɔantrˈɔ", "колебаене": "kɔlɛbˈaɛnɛ",
    "конелиано": "kɔnɛliˈanɔ", "крайморие": "krajmˈɔriɛ", "кураре": "kurˈarɛ",
    "лешоядство": "lɛʃɔjˈatstvɔ", "луфтвафе": "lˈuftvafɛ", "лъщене": "lɤʃtʃˈɛnɛ",
    "майсторене": "majstɔrˈɛnɛ", "маслинопроизводство": "maslinɔprɔizvˈɔtstvɔ",
    "метларство": "mɛtlˈarstvɔ", "мецотинто": "mɛtsɔtˈintɔ", "минерализиране": "minɛralizˈiranɛ",
    "мирянство": "mirjˈanstvɔ", "музикантство": "muzikˈantstvɔ", "налбантство": "nalbˈantstvɔ",
    "незнаене": "nɛznˈaɛnɛ", "необвързване": "nɛɔbvˈɤrzvanɛ", "непримирение": "nɛprimirˈɛniɛ",
    "непритежаване": "nɛpritɛʒˈavanɛ", "несподеляне": "nɛspɔdɛljˈanɛ", "олийце": "ɔlˈijtsɛ",
    "пантофарство": "pantɔfˈarstvɔ", "папо": "pˈapɔ", "пармиджано": "parmidʒˈanɔ",
    "парно": "pˈarnɔ", "пасене": "pasˈɛnɛ", "песо": "pˈɛsɔ", "песто": "pˈɛstɔ",
    "пилотство": "pilˈɔtstvɔ", "подвижничество": "pɔdvˈiʒnitʃɛstvɔ", "подмосковие": "pɔdmɔskˈɔviɛ",
    "потенциране": "pɔtɛntsˈiranɛ", "правоверие": "pravɔvˈɛriɛ", "преводачество": "prɛvɔdˈatʃɛstvɔ",
    "приднестровие": "pridnɛstrˈɔviɛ", "прошуто": "prɔʃˈutɔ", "псевдошампанско": "psɛvdɔʃampˈanskɔ",
    "психо": "psˈixɔ", "растене": "rastˈɛnɛ", "редене": "rɛdˈɛnɛ", "режисьорство": "rɛʒisjˈɔrstvɔ",
    "реминерализиране": "rɛminɛralizˈiranɛ", "риене": "rˈiɛnɛ", "самолетостроене": "samɔlɛtɔstrɔˈɛnɛ",
    "скандинавие": "skandinˈaviɛ", "соцминало": "sɔtsmˈinalɔ", "суперкарго": "supɛrkˈarɡɔ",
    "сърежисьорство": "sɤrɛʒisjˈɔrstvɔ", "термобельо": "tɛrmɔbɛljˈɔ", "тузарство": "tuzˈarstvɔ",
    "фалшименто": "falʃimˈɛntɔ", "филморазпространение": "filmɔrasprɔstranˈɛniɛ",
    "хамкане": "xˈamkanɛ", "христолюбие": "xristɔljˈubiɛ", "шевро": "ʃɛvrˈɔ", "шиацу": "ʃiˈatsu"
}


def ipa_quality_score(ipa):
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

    if ipa.endswith(("ˈɤ", "ˈa", "ˈɔ", "ˈu", "ˈi", "ˈɛ")):
        score -= 10.0

    return score


def select_canonical_variant(variants):
    return max(
        sorted(set(variants)),
        key=lambda ipa: (ipa_quality_score(ipa), -len(ipa), ipa),
    )


def clean_ipa_base(ipa):
    if not ipa:
        return ""

    # 1. Оправяме имената на буквите (икратко, ерголям и т.н.)
    # Трябва да е ПРЕДИ останалото чистене
    for bad, good in LITERAL_FIXES.items():
        ipa = ipa.replace(bad, good)

    # 2. Махаме тирета и Espeak артефакти
    ipa = ipa.replace("\u0361", "")
    espeak_map = {
        'ɫ': 'l', 'ɲ': 'n', 'ʂ': 'ʃ', 'ʑ': 'ʒ',
        'ç': 'x', 'ʎ': 'l', 'c': 'k', 'ŋ': 'n', 'ɱ': 'm',
        'w': 'v', '-': ''
    }
    for bad, good in espeak_map.items():
        ipa = ipa.replace(bad, good)

    # 3. Wiktionary нормализация
    ipa = ipa.replace('e', 'ɛ').replace('o', 'ɔ').replace('g', 'ɡ')

    # 4. Изчистване на диакритики
    ipa = re.sub(r"[\u031f\u032f\u031e\u032a]", "", ipa)
    ipa = ipa.replace("ɟ", "ɡ").replace("ʲ", "j").replace(
        " ", "").replace("(", "").replace(")", "")

    # 5. Премахване на двойни ударения (пазим последното)
    if ipa.count("ˈ") > 1:
        parts = ipa.split("ˈ")
        ipa = "".join(parts[:-1]) + "ˈ" + parts[-1]

    return ipa


def fix_sht_logic(word, ipa):
    if "щ" not in word:
        if "ш" in word:
            ipa = ipa.replace("ʃtʃ", "ʃ")
        return ipa
    if "ʃtʃ" in ipa or "ʃˈtʃ" in ipa:
        return ipa
    ipa = re.sub(r'ʃ(ˈ?)t', r'ʃ\1tʃ', ipa)
    if "ʃtʃ" not in ipa and "ʃˈtʃ" not in ipa:
        ipa = re.sub(r'ʃ(ˈ?)', r'ʃ\1tʃ', ipa)
    return ipa.replace("ʃtʃtʃ", "ʃtʃ").replace("ʃtʃt", "ʃtʃ")


def main():
    if not INPUT_FILE.exists():
        return
    final_dataset = defaultdict(set)
    # вече не търсим ɛnnˈan, защото LITERAL_FIXES ще го оправи
    bad_markers = {"nanb", "anbg", "nnbg", "nnan"}

    with open(INPUT_FILE, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f, delimiter="\t")
        for row in reader:
            if len(row) < 2:
                continue
            word = row[0].strip().lower()
            raw_ipa = row[1].strip()

            # Филтри за боклук
            if any(c.isdigit() for c in word):
                continue
            if word.startswith(("-", "<", "[", "(")):
                continue
            if any('a' <= c <= 'z' for c in word):
                continue

            # Чистене
            if word in MANUAL_FIXES:
                ipa = MANUAL_FIXES[word]
            else:
                ipa = clean_ipa_base(raw_ipa)
                if any(m in ipa.lower() for m in bad_markers) or not ipa:
                    continue
                ipa = fix_sht_logic(word, ipa)

            final_dataset[word].add(ipa)

    # ВАЖНО: Подреждане и запис (Unix style newlines)
    sorted_words = sorted(final_dataset.keys())
    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="\n") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        for w in sorted_words:
            writer.writerow([w, select_canonical_variant(final_dataset[w])])

    print(f"[SUCCESS] Лексиконът е пречистен и подреден.")


if __name__ == "__main__":
    main()
