# Generating slides with Marp CLI

This directory contains Marp-based presentation sources.

For full documentation on Marp CLI, see: <https://github.com/marp-team/marp-cli>

## Prerequisites

- Node.js installed

## Render to HTML

```bash
npx @marp-team/marp-cli \
  --html \
  --allow-local-files \
  Wellbore-DDMS-Technical-Overview.md \
  -o Wellbore-DDMS-Technical-Overview.html
```

## Render to PDF

```bash
npx @marp-team/marp-cli \
  --pdf \
  --allow-local-files \
  Wellbore-DDMS-Technical-Overview.md \
  -o Wellbore-DDMS-Technical-Overview.pdf
```

## Notes

- Run the commands from the `docs/presentation/` directory.
- `--allow-local-files` is required because the deck references local image assets.
- Generated HTML and PDF files do not need to be edited by hand.
