# Dataset card: educational diagrams for SANA LoRA fine-tuning

All numbers on this page are copied from `docs/dataset/stats.json`, which
`training/dataset/stats.py` computes from the built dataset. Built on 2026-10-02 on the workstation.

## Summary

- **Total images: 4225** (1024x1024 PNG, padded to square on white, one caption each)
- Split (seed 42): train **3803**, val **211**, test **211**
- Caption format: `edudiag, {level words}, {look words}, {description}` (mean 25.9 words)
- The dataset itself is not committed or copied between machines (`training/data/` is git-ignored);
  it is rebuilt with the scripts in `training/dataset/`.

## Sources and licences

| source | images |
|---|---|
| wikimedia_commons | 2785 |
| ai2d | 1440 |

| Source | Where it was downloaded from | Licence, and where it was checked |
|---|---|---|
| AI2D (AI2 Diagrams, Kembhavi et al. 2016) | Official AI2 bucket `s3://ai2-public-datasets/diagrams/ai2d-all.zip` | **CC BY-SA**, as stated on the AWS Open Data registry page https://registry.opendata.aws/allenai-diagrams/ (checked 2026-10-02). The page does not state a version number; the Hugging Face mirror `lmms-lab/ai2d` states no licence. The diagrams were originally collected from the web by AI2, so the licence is the dataset publisher's statement, not a per-image verification. |
| Wikimedia Commons | MediaWiki API, files in science-diagram categories (list in `training/dataset/download_wikimedia.py`) | Per file, from the API's `extmetadata.LicenseShortName`. Only Public Domain, CC0, CC BY and CC BY-SA were accepted; NC, ND and unknown licences were skipped. Author, licence and description-page URL are stored per image in `manifest.csv`. |

Sources that were evaluated and **not used**:

- **TQA** (AI2): distributed under CC BY-NC 3.0 (non-commercial). Not used, in favour of permissive sources.
- **ScienceQA**: the official site states CC BY-NC-SA, while the Hugging Face mirror `derek-thomas/ScienceQA` is tagged cc-by-sa-4.0. Because of this contradiction and the NC term, it was not used.

### Images per licence

| licence (as reported by the source) | images |
|---|---|
| CC BY-SA | 1440 |
| CC BY-SA 4.0 | 1067 |
| CC BY-SA 3.0 | 664 |
| Public domain | 530 |
| CC0 | 207 |
| CC BY 4.0 | 149 |
| CC BY 3.0 | 98 |
| CC BY 2.5 | 25 |
| CC BY-SA 2.5 | 22 |
| CC BY 2.0 | 8 |
| CC BY-SA 2.0 uk | 3 |
| CC BY-SA 2.0 de | 2 |
| CC BY-SA 3.0 igo | 2 |
| CC BY-SA 3.0 de | 2 |
| CC BY-SA 2.0 | 1 |
| CC BY-SA 1.0 | 1 |
| CC BY-SA 3.0 nl | 1 |
| CC BY 1.0 | 1 |
| CC BY-SA 3.0 cz | 1 |
| CC BY 2.0 kr | 1 |

Attribution is required for every CC BY / CC BY-SA image; `manifest.csv` holds the author and source URL
needed for it. Whether a LoRA trained on CC BY-SA images must itself be shared under CC BY-SA is an
open legal question; treat the adapter as an academic, non-redistributed artefact unless the owner decides otherwise.

### Wikimedia Commons images per root category

| root category | images |
|---|---|
| Physics diagrams | 621 |
| Biology diagrams | 597 |
| Chemistry diagrams | 340 |
| Earth science diagrams | 275 |
| Optics diagrams | 260 |
| Zoology diagrams | 219 |
| Life cycle diagrams | 183 |
| Science diagrams | 170 |
| Diagrams of volcanoes | 85 |
| Rock cycle diagrams | 28 |
| Food web diagrams | 7 |

## Style tags (from the captioning model)

| complexity | images |
|---|---|
| simple | 2728 |
| detailed | 1497 |

| look | images |
|---|---|
| textbook_diagram | 3105 |
| infographic | 827 |
| process_flow | 285 |
| cross_section | 8 |

| complexity / look | images |
|---|---|
| simple / textbook_diagram | 1995 |
| detailed / textbook_diagram | 1110 |
| simple / infographic | 539 |
| detailed / infographic | 288 |
| simple / process_flow | 189 |
| detailed / process_flow | 96 |
| simple / cross_section | 5 |
| detailed / cross_section | 3 |

Mapping to caption words: simple → `school level`, detailed → `college level`; infographic →
`learn style colourful infographic`; textbook_diagram and cross_section → `exam style clean labeled
textbook diagram`; process_flow → `process flow diagram`.

## Pipeline and what each step removed

| Step | AI2D | Wikimedia Commons |
|---|---|---|
| Raw images | 4903 | 3300 (candidates that passed the licence, size and type checks at crawl time) |
| Dropped: min side < 512 | 3447 | 0 (already filtered at crawl time) |
| Dropped: aspect ratio > 3 | 0 | 4 |
| Dropped: perceptual-hash duplicate | 16 | 476 |
| Dropped: corrupt | 0 | 0 |
| Kept after `filter.py` | 1440 | 2820 |

After captioning (`Qwen/Qwen2.5-VL-7B-Instruct`, 4260 images), `build_metadata.py` dropped:
caption could not be parsed **18**, flagged as photo of people **9**,
flagged as not an educational diagram **8**. Kept: **4225**.

## Known issues

- **Captions are machine-written and only spot-checked.** `caption_samples.md` lists 50 random captions.
  Reading them shows mostly correct descriptions, but also errors: some captions still describe labels
  ("labeled parts"), some start with a capital or are full sentences, and a few are vague.
- **Not every image is a diagram.** The captioning model flagged only 8 images as non-diagrams, which is
  too few: the samples include a bar chart and a drawing of sailboats from the Commons categories.
- **Style tags are unbalanced.** 3105 of 4225 images are `textbook_diagram`, only 8 are `cross_section`,
  and `simple` outnumbers `detailed`. The "learn / infographic" look is under-represented.
- **Most diagrams contain text labels.** SANA cannot render legible text, so the fine-tuned model
  learns label-like marks that are not readable.
- **Upscaling.** Images with a short side between 512 and 1024 px were upscaled to 1024.
- **Subject mix.** AI2D is primary-school science; the Commons part leans towards biology and physics.
- **"Held-out" split.** val/test are random 5% splits; near-duplicate diagrams of the same subject can
  appear in both train and test (only perceptual-hash duplicates were removed).
