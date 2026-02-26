# Paper Agent - Claude Code Project

## Overview
Daily AI agent that scrapes behavioral finance & asset pricing papers from NBER and SSRN, generates AI summaries using Claude API, and produces HTML reports with charts.

## Project Structure
```
paper_agent/
├── main.py              # Entry point + scheduler
├── config.py            # Topics, keywords, settings
├── requirements.txt
├── scrapers/
│   ├── nber_scraper.py  # NBER working papers scraper
│   └── ssrn_scraper.py  # SSRN papers scraper
├── processors/
│   └── ai_processor.py  # Claude API summarization
├── reports/
│   └── report_generator.py  # HTML report + matplotlib charts
├── data/               # Saved paper JSON (papers_YYYY-MM-DD.json)
├── reports/            # HTML digests (digest_YYYY-MM-DD.html, latest.html)
├── charts/             # Chart images
└── logs/               # agent.log
```

## Usage

### Run once (last 7 days):
```bash
python main.py --mode run --days 7
```

### Demo mode (no AI, fast test):
```bash
python main.py --mode demo
```

### Daily scheduler (runs at 08:00 Prague time):
```bash
python main.py --mode schedule
```

### Dry run (skip API calls):
```bash
python main.py --dry-run --days 3
```

## Setup for Claude Code
1. Install dependencies: `pip install -r requirements.txt`
2. Run demo to test: `python main.py --mode demo`
3. For production: ensure ANTHROPIC_API_KEY is set in environment
4. For daily scheduling: use `python main.py --mode schedule` or set up a cron job:
   ```
   0 8 * * * cd /path/to/paper_agent && python main.py --mode run --days 1
   ```

## Configuration (config.py)
- `TOPICS`: Research areas and keywords to filter papers
- `NBER_CONFIG.programs`: NBER program codes (AP=Asset Pricing, CF=Corporate Finance, etc.)
- `AI_CONFIG.summary_prompt`: Customize the AI analysis prompt
- `SCHEDULE_CONFIG.run_time`: Change daily run time

## Extending
- Add new topics to `TOPICS` dict in config.py
- Modify `AI_CONFIG.summary_prompt` to change what Claude analyzes
- Add email delivery by extending `main.py`'s `run_agent()` function
- Add more sources (AER, JF, RFS) by creating new scrapers following the pattern

## Report Output
Reports are saved to `reports/latest.html` (always overwritten) and 
`reports/digest_YYYY-MM-DD.html` (archived). Open in any browser.
