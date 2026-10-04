# VIS-D059 — curated D-059 replay

**Status:** evaluator/presentation-only replay; non-evidential.

> CURATED ILLUSTRATIVE EXAMPLES — selected post-result for visual interest; not a representative sample; zero evidential weight; does not alter or strengthen any D-059 conclusion.

This record describes one deterministic HTML export of ten digest-gated D-059
endurance lifetimes. It makes no scientific claim and does not change the
accepted D-059 artifact, record, protocol, controller, environment, or
interpretation.

## Authority

- VIS-D059 implementation proposal: [GitHub issue #209](https://github.com/PiFlow/aweform/issues/209).
- Binding implementation authorization: [Sol comment 5980190155](https://github.com/PiFlow/aweform/issues/209#issuecomment-5980190155), with Flow's direction “yes go luna implement now”.
- Accepted digest source: [`D-059-v05-s1-level1-floor-rebaseline.json`](D-059-v05-s1-level1-floor-rebaseline.json), `endurance.lifetime_summaries`.
- Implementation base: `0c6019012831de2dd9207f68384ecbb779e9a540`.

The runner composes unchanged D-059/D-058/D-045 components. Before HTML is
written, each of the ten exact allowlisted tuples must reproduce both the
accepted `trajectory_digest_sha256` and
`final_causal_state_digest_sha256`. The output is written only after every
tuple matches. D-045 `boundary_scale < 1` indicates constrained motion, but its
dynamic wall/corner anatomy remains **UNKNOWN**. S1 wall interaction is shown
from D-058 contact telemetry without assigning inferred wall identities.

## Curated allowlist and reasons

The post-result curation covers qualitatively distinct lifetime shapes in the
accepted forward endurance subset. D045_1M U rows show selected failure,
survival, and boundary-scaled examples; D045_1M C rows show the stall-turn
contrast; S1 rows show multi-cycle docking in both room sizes. S1 is shown on U
only because accepted D-059 records S1 C≡U as structural identity.

| # | Seed | Substrate / arm | Curation reason from accepted D-059 fields |
|---:|---:|---|---|
| 1 | 26052 | D045_1M / U | Earliest energy depletion: `ENERGY_DEPLETION` at 141,564 transitions; first RETURN `RETURN_TIMEOUT_FAILURE`; 120,426 boundary-scaled transitions. |
| 2 | 26002 | D045_1M / U | Docks once, then times out and depletes at 234,979. |
| 3 | 26005 | D045_1M / U | Survives 300,000 transitions with 2 DOCKED + 1 timeout; most boundary-scaled U lifetime (200,196). |
| 4 | 26051 | D045_1M / C | Stall-turn contrast: 3/3 DOCKED, most boundary-scaled C lifetime (175,764). |
| 5 | 26042 | D045_1M / C | 3/3 DOCKED; longest C RETURN (51 transitions). |
| 6 | 26000 | S1_3M / U | First forward seed; 6 cycles, 6/6 DOCKED. |
| 7 | 26038 | S1_3M / U | All 6 RETURNs `wall_exposed_any`; lowest S1_3M minimum energy (0.19803); longest S1_3M RETURN (93). |
| 8 | 26016 | S1_3M / U | 6/6 wall-exposed RETURNs, all DOCKED. |
| 9 | 26001 | S1_1M / U | 6/6 wall-exposed RETURNs; highest terminal-spin maximum (19). |
| 10 | 26035 | S1_1M / U | Longest S1_1M RETURN (46 transitions). |

## Digest verification

Every expected value below was read from the accepted D-059 JSON. The matching
recomputed values are shown in the adjacent columns; each lifetime matched on
both digests.

| Seed | Substrate / arm | Expected trajectory SHA-256 | Recomputed trajectory SHA-256 | Expected final causal-state SHA-256 | Recomputed final causal-state SHA-256 | Result |
|---:|---|---|---|---|---|---|
| 26052 | D045_1M / U | `7667b20ff371f8b096f40bcee7081143a991f6458e3e6980427e9a730c613f8b` | `7667b20ff371f8b096f40bcee7081143a991f6458e3e6980427e9a730c613f8b` | `adce72f4c017a9acbd5431caf971d61ae15849b7023a257dce96c4590f5d54de` | `adce72f4c017a9acbd5431caf971d61ae15849b7023a257dce96c4590f5d54de` | MATCH |
| 26002 | D045_1M / U | `f462f63dc900cd173f1723965e9c5b25ce3d65c7a16e4b5704aaba28de94524c` | `f462f63dc900cd173f1723965e9c5b25ce3d65c7a16e4b5704aaba28de94524c` | `7d918c8579a40f0ee38f4d48acf7b99d5b4bde828d48a6b900b48e7a6a63b243` | `7d918c8579a40f0ee38f4d48acf7b99d5b4bde828d48a6b900b48e7a6a63b243` | MATCH |
| 26005 | D045_1M / U | `9006cb9ee7a95eb1fbbbb712c6ae0f214d361d7d98ee02b75cada9a2f74e08e5` | `9006cb9ee7a95eb1fbbbb712c6ae0f214d361d7d98ee02b75cada9a2f74e08e5` | `e3289cff9f6708d51bf92405a41558fb2f72d4ff350f38f341766dcecda48dea` | `e3289cff9f6708d51bf92405a41558fb2f72d4ff350f38f341766dcecda48dea` | MATCH |
| 26051 | D045_1M / C | `c6b9ad610e8ae40c097b019078f5ecb4a7673d2426c873cfb62d811342d8c88f` | `c6b9ad610e8ae40c097b019078f5ecb4a7673d2426c873cfb62d811342d8c88f` | `e03929edc188ba42cda568819ccd4e63269041718f007098b0a3b8c860e35010` | `e03929edc188ba42cda568819ccd4e63269041718f007098b0a3b8c860e35010` | MATCH |
| 26042 | D045_1M / C | `7c6e30eecc32191b1918e062fe529a7ce9e28f8464aabc8dbbf37a2c0572a066` | `7c6e30eecc32191b1918e062fe529a7ce9e28f8464aabc8dbbf37a2c0572a066` | `7485099e5f7cd37b02e25459fad8c57e1b6a72f92f9f60bf486b8e3ac90ad838` | `7485099e5f7cd37b02e25459fad8c57e1b6a72f92f9f60bf486b8e3ac90ad838` | MATCH |
| 26000 | S1_3M / U | `524eb373c95797b0741ac0c19ad72a9c1afe2e4de8e16d426019038b1e218be9` | `524eb373c95797b0741ac0c19ad72a9c1afe2e4de8e16d426019038b1e218be9` | `130d91e0a67ea18b2a1e07b1541e229b26bb62d37745f20dcf3b7b14d90576d1` | `130d91e0a67ea18b2a1e07b1541e229b26bb62d37745f20dcf3b7b14d90576d1` | MATCH |
| 26038 | S1_3M / U | `1d1c33e9db5d1da16d9bac331fcfa28f366ef265118cf81d152d3193d4d9c5e7` | `1d1c33e9db5d1da16d9bac331fcfa28f366ef265118cf81d152d3193d4d9c5e7` | `f78b9a21d5268bcbbe7895d77cf5e01166e8ed6f09124b8048be88dc00979ed9` | `f78b9a21d5268bcbbe7895d77cf5e01166e8ed6f09124b8048be88dc00979ed9` | MATCH |
| 26016 | S1_3M / U | `009df136dce1ac97df812d755da85fd0b629a60126c416d84a6b76b6f1bf0528` | `009df136dce1ac97df812d755da85fd0b629a60126c416d84a6b76b6f1bf0528` | `0799a3a201a2819dc36eb3511733e15a0022e582fced89c585b6e75dfc085485` | `0799a3a201a2819dc36eb3511733e15a0022e582fced89c585b6e75dfc085485` | MATCH |
| 26001 | S1_1M / U | `674dc67d3453368467406be5fd708e8e9b820d761bd941a3414ce866d12dce4c` | `674dc67d3453368467406be5fd708e8e9b820d761bd941a3414ce866d12dce4c` | `7234eb48e50ebde8ac052a9745d4dcd927e356730a3e78ccfc5fbeecd1918d51` | `7234eb48e50ebde8ac052a9745d4dcd927e356730a3e78ccfc5fbeecd1918d51` | MATCH |
| 26035 | S1_1M / U | `e094389e50b5cb0588d044dafc76b0a753f425bd569542767cebe81105077d03` | `e094389e50b5cb0588d044dafc76b0a753f425bd569542767cebe81105077d03` | `3410cf447564c5c0307afe11f57672ef403df2f0d485460f8b971692d83c553f` | `3410cf447564c5c0307afe11f57672ef403df2f0d485460f8b971692d83c553f` | MATCH |

## Export provenance

- **Exact command:** `PYTHONHASHSEED=0 MPLCONFIGDIR=/private/tmp/aweform-mpl UV_CACHE_DIR=/private/tmp/aweform-uv-cache uv run aweform-export-vis-d059-html`
- **Run result:** all ten trajectory digests and all ten final causal-state digests matched; no mismatch.
- **Runtime:** 198.56 seconds wall (`/usr/bin/time -p`, includes CLI startup and Matplotlib initialization).
- **Python:** 3.14.7.
- **`PYTHONHASHSEED`:** `0`.
- **HTML bytes:** 20,516,612.
- **HTML SHA-256:** `9faaa7a110fdae70a0509e38b1380ba682dddf4d9a347f84e709d5e5e00600d5`.
- **HTML:** [`VIS-D059-curated-replay.html`](VIS-D059-curated-replay.html).
- **Frame label:** every frame's action line is prefixed with the lifetime identity `{substrate}/{arm}` (for example `D045_1M/U`, `S1_1M/U`, `D045_1M/C`).

## Protected-file hash proof

Before commit, SHA-256 was recomputed for each protected implementation file,
the D-059 executable/test/artifact/record, and every tracked `development/D-*`
Markdown, JSON, and HTML artifact/replay. All **137 paths** were byte-identical
to `git show 0c6019012831de2dd9207f68384ecbb779e9a540:<path>`.

| Protected path | SHA-256 |
|---|---|
| `src/aweform/d059.py` | `0ff23bb32520244740b54fee8caeb45ccffbb422fb0eb1a3370735e9c1804d9c` |
| `tests/test_d059.py` | `9a875154dbf77e3cebe565239c10dfadc8e94b00872f78d3cf243e74e3af0b15` |
| `development/D-059-v05-s1-level1-floor-rebaseline.json` | `8a4c30f3f969987e1683d6c702f694e8611a16b3cc3c29250e61ad6b87a89129` |
| `development/D-059-v05-s1-level1-floor-rebaseline.md` | `47d651d3f4a584f429d430589367959d5be9503ab2ee6e9206b5631ef47dfb30` |
| `src/aweform/d045.py` | `b137b80df53894d96684e6a2513d33f4b6bc39c23dfeeba0476d2949387ca774` |
| `src/aweform/d049.py` | `85253a9277523f8ca689638b2720fd582f6b43650be2eb0cb4fcbb8af7d3921a` |
| `src/aweform/d050.py` | `c9a031545a5a6dcbe732994f7d3c3534d4d1b22ec1b82c78e7d9f98e74666358` |
| `src/aweform/d052.py` | `4c93a3dd8171380370e212547c8ed90dad5359477fb685489e33fbcaa00d09a4` |
| `src/aweform/d053.py` | `45754c9e4536370f5e969cca6e4e3f59232d435ba289abf7efd82fa965b868e7` |
| `src/aweform/d054.py` | `d3664b318a42a53b6f524449c12337096999bbd42eb1d27a6d3da4aeca6b7313` |
| `src/aweform/d055.py` | `2ced64b2c524f542f8cb83f2c3dafeb526dd37d8533eba298ea15bb268703693` |
| `src/aweform/d056.py` | `8bf7370f86cac5ed8a580d0456cd7111f90f1108994de1b64761e69cc95ca518` |
| `src/aweform/d057.py` | `ceb93c5fb930d5fb8ee25448fbcd272408b327a532cc60317430d34662602ca8` |
| `src/aweform/d058.py` | `8ee22b6185114ef200604671bfcaf61efc728b665d69ca2ded18ba948fb1d9ee` |
| `src/aweform/development_visualizer.py` | `11073ae8f30a561b7760b8a4939e9cf7b68bd60b1cc86b29845178be42558ca5` |
| `src/aweform/body.py` | `3d5d1bfd6b231591bb1515dc495f5dbb743b0dda1e8a8adcbc1414ff93a94236` |
| `src/aweform/env.py` | `c61832671a3dd5e3d40435304153a521bf925d4be24c964984e157c429d2cb19` |
| `src/aweform/exp001.py` | `f644cb14ae56446af5ad2ca8d8d61eef5c8a9d1d6c18fdaf4362ca7441c71be7` |
| `src/aweform/exp003.py` | `72f3d67651b95df6d395dc9f57f49b20bf92dc8c28603941fe0b89121b9cb9f2` |
| `src/aweform/exp003_seed_policy.py` | `b624a117ef947f41a3c494d017d398dd0212a0f7975698922f0f455a87ea0f8d` |

This is a selected post-result presentation artifact. The seed selector and
title repeat the warning above. It has zero evidential weight.
