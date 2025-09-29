name: Generate lookup HTML (manual)

on:
  workflow_dispatch:
    inputs:
      output_basename:
        description: "Base name for generated file in lookup/ (no extension)"
        required: false
        default: "lookup.auto"

permissions:
  contents: write

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Check out repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Generate new lookup HTML (timestamped copy)
        env:
          INPUT_FILES: |
            JAWS.html
            NVDA.html
            TalkBack-android.html
            VO-ios.html
            VO-mac.html
          LOOKUP_TEMPLATE: lookup/lookup.html
          OUTPUT_BASENAME: ${{ github.event.inputs.output_basename }}
        run: |
          set -euo pipefail
          TS="$(date -u +%Y%m%d-%H%M%S)"
          BASENAME="${OUTPUT_BASENAME:-lookup.auto}"
          OUTPUT_FILE="lookup/${BASENAME}.${TS}.html"
          echo "OUTPUT_FILE=${OUTPUT_FILE}" >> $GITHUB_ENV
          python .github/scripts/generate_lo_
