# Email Reader - Internship Application Counter

A Python application that parses email data from Google Takeout and counts how many internships you've applied to.

## Features

- Parses MBOX files from Google Takeout
- Identifies internship application emails using keyword matching
- Counts total applications and unique companies
- Shows application history with dates and subjects
- Handles both single MBOX files and directories containing multiple MBOX files

## Requirements

- Python 3.6 or higher
- No external dependencies (uses only Python standard library)

## Usage

### Getting Your Email Data from Google Takeout

1. Go to [Google Takeout](https://takeout.google.com/)
2. Select "Mail" from the list of services
3. Choose your export format (MBOX is recommended)
4. Download and extract the archive
5. Locate the MBOX files in the extracted folder

### Running the Application

**For a single MBOX file:**
```bash
python email_parser.py path/to/your/email.mbox
```

**For a directory containing multiple MBOX files:**
```bash
python email_parser.py path/to/your/takeout/folder
```

### Example Output

```
Parsing All mail Including Spam and Trash.mbox...
  Found 45 applications in All mail Including Spam and Trash.mbox

============================================================
INTERNSHIP APPLICATION SUMMARY
============================================================

Total Applications: 45
Unique Companies: 32

Companies Applied To:
  - Google: 2 application(s)
  - Microsoft: 1 application(s)
  - Amazon: 3 application(s)
  ...

Recent Applications (showing last 10):
  [2024-01-15] Google
    Subject: Application for Software Engineering Intern
  [2024-01-12] Microsoft
    Subject: Internship Application - Summer 2024
  ...
============================================================
```

## How It Works

The application uses several heuristics to identify internship applications:

1. **Keyword Matching**: Looks for keywords like "internship", "application", "applied", "resume", etc.
2. **Sent Email Detection**: Prioritizes emails you sent (likely applications)
3. **Exclusion Filters**: Filters out rejection emails and confirmations
4. **Company Extraction**: Attempts to extract company names from email addresses

## Customization

You can modify the keyword lists in `email_parser.py`:

- `APPLICATION_KEYWORDS`: Keywords that suggest an application
- `EXCLUSION_KEYWORDS`: Keywords that suggest it's NOT an application

## Notes

- The parser may not catch 100% of applications - you may need to adjust keywords based on your email patterns
- Company name extraction is based on email domains and may not always be accurate
- Large MBOX files may take some time to process

