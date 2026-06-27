# Hardcover Books to Lists

<!-- social-badges:start -->
[![Discord](https://img.shields.io/badge/Discord-5865F2?logo=discord&logoColor=white)](https://discord.gg/jUMuSxGf6q)
[![GitHub](https://img.shields.io/badge/GitHub-181717?logo=github&logoColor=white)](https://github.com/NC1107)
[![Patreon](https://img.shields.io/badge/Patreon-F96854?logo=patreon&logoColor=white)](https://patreon.com/NPC1107)
<!-- social-badges:end -->

Simple script to convert Hardcover reading status books into lists that can be imported by Readarr.

## The Problem

Readarr can only import from Hardcover list URLs like `https://hardcover.app/@username/lists/want-to-read`, but not from reading status pages like `https://hardcover.app/@username/books/want-to-read`.

This script syncs your reading statuses (want-to-read, currently-reading, read, did-not-finish) into proper Hardcover lists that Readarr can import.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the script
python convert_books_to_list.py
```

Get your API key from https://hardcover.app/settings/api

## Usage

**Interactive mode** (select which statuses to convert):
```bash
python convert_books_to_list.py
```

**Command line** (convert specific statuses):
```bash
python convert_books_to_list.py --status want-to-read
python convert_books_to_list.py --status all
```

**With API key**:
```bash
python convert_books_to_list.py --api-key YOUR_KEY
```

Or set `HARDCOVER_API_KEY` environment variable in a `.env` file.

## Reading Statuses

- **want-to-read** - Best for Readarr (books to acquire)
- **currently-reading** - Books you're reading now
- **read** - Completed books
- **did-not-finish** - Books you didn't complete

## Readarr Setup

1. Run the script to create your lists
2. Copy the list URL from the output
3. In Readarr: Settings > Import Lists > Add > Hardcover
4. Paste your list URL
5. Save and test

## Features

- Supports all four Hardcover reading statuses
- Interactive or command-line mode
- Batch processing (convert multiple statuses at once)
- Automatic rate limiting and retries
- Skips duplicate books
- Safe to re-run anytime

## Example Output

```
Validating API key and fetching user info...
Authenticated as: Your Name (@yourusername)

Processing 1 status(es)...

============================================================
Processing: want-to-read
============================================================
Fetching your want-to-read books...
Found 42 want-to-read books
Checking for existing 'want-to-read' list...
List created! (ID: 12345)
Adding books to list...
  [1] Added: The Name of the Wind
  [2] Added: Mistborn: The Final Empire
  ...

============================================================
ALL COMPLETE!
============================================================

WANT-TO-READ:
  Total books: 42
  Added to list: 42
  List URL: https://hardcover.app/@yourusername/lists/want-to-read

============================================================
You can now use these list URLs in Readarr's import lists!
```

## License

MIT
