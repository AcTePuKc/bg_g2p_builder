# Data Sources

This repository builds Bulgarian grapheme-to-phoneme resources by combining
multiple upstream inputs plus repository-local normalization logic.

## 1. Kaikki / Wiktionary

Kaikki.org provides machine-readable exports derived from Wiktionary. In this
project, Kaikki / Wiktionary is the upstream source for Wiktionary-derived
Bulgarian lexical entries and pronunciation data, including IPA where available.

Notes:

- The underlying content is community-authored Wiktionary material.
- Licensing and attribution obligations for Wiktionary-derived content may flow
  into generated datasets. See `DATA_LICENSE.md`.
- If you redistribute outputs that include or derive from this source, preserve
  upstream attribution and review applicable share-alike requirements.

## 2. vislupus/alpaca-bulgarian-dictionary

The Hugging Face dataset `vislupus/alpaca-bulgarian-dictionary` is used as an
upstream source of Bulgarian stress-marked lexical data. In this repository it
serves primarily as a stress reference to improve pronunciation generation and
disambiguation.

Notes:

- This repository attributes the dataset as an upstream linguistic source.
- Users should review the dataset page and any embedded licensing metadata
  before redistributing derivative lexical outputs.

## 3. eSpeak NG

eSpeak NG is used only as an optional reference, generation engine, or
comparison baseline unless a specific file in this repository explicitly states
that code or data was copied from eSpeak NG.

Important limitation:

- This repository does not treat eSpeak NG as a bundled source of copied code or
  copied data by default.
- If future revisions import eSpeak NG code or data directly, those additions
  should be documented explicitly in both this file and `NOTICE.md`.

## 4. Manually Authored Rules

The repository also contains manually authored correction, cleanup, and
normalization rules. These rules cover issues such as stress handling,
phonological cleanup, and normalization choices made during lexicon generation.

These manually authored rules are part of the repository source and are distinct
from the external upstream linguistic datasets listed above.
