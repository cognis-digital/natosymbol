# Demo 01 — Basic SIDC validation and decoding

This demo shows NATOSYMBOL validating, decoding and building APP-6 /
MIL-STD-2525C Symbol Identification Codes (SIDC). Everything runs with the
Python standard library only — no install, no network.

## What a SIDC is

A SIDC is a 15-character code that describes a tactical symbol on a Common
Operational Picture (COP). Example: `SFGPUCI-----USG`

| Pos | Field             | Value    | Meaning            |
|-----|-------------------|----------|--------------------|
| 1   | Coding scheme     | `S`      | Warfighting        |
| 2   | Affiliation       | `F`      | Friend             |
| 3   | Battle dimension  | `G`      | Ground             |
| 4   | Status            | `P`      | Present            |
| 5-10| Function ID       | `UCI---` | Infantry           |
| 11  | Modifier 1        | `-`      | None               |
| 12  | Modifier 2        | `-`      | None               |
| 13-14| Country          | `US`     | United States      |
| 15  | Order of battle   | `G`      | Ground OB          |

## Try it

Validate the bundled feed of SIDCs (mix of valid and intentionally broken):

```sh
python -m natosymbol batch demos/01-basic/feed.sidc
```

Decode a single symbol as JSON for piping into other tools:

```sh
python -m natosymbol --format json describe SFGPUCI-----USG
```

Build a SIDC for a hostile armor battalion (US country code) from fields:

```sh
python -m natosymbol build --affiliation H --dimension G \
    --function UCR--- --modifier2 F --country US
```

The `batch` and `validate` subcommands exit non-zero if any SIDC is invalid,
so they drop straight into CI / compliance gates.
