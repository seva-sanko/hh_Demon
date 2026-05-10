# hh_Demon

Async HH.ru job market analyzer. Scrapes vacancies via the HH.ru API, extracts skills from descriptions using NLP, builds a skill co-occurrence graph, and outputs salary stats and demand metrics.

> Work in progress — further development planned.

## What it does

1. **Fetch** — async bulk download of vacancies from HH.ru API (`aiohttp`, configurable concurrency)
2. **Extract skills** — parse skill tags + free-text descriptions using `pymorphy2` lemmatization + `KNOWN_SKILLS` dictionary
3. **Analyze** — salary stats (avg/median), missing skills vs user profile, Skill Demand Index
4. **Graph** — skill co-occurrence graph (`networkx`), cluster detection, tech-stack grouping

## Output

- Average and median salary (RUB, vacancies with stated salary only)
- Top-15 missing skills ranked by vacancy frequency
- Skill Demand Index — % of vacancies mentioning each skill
- Skill salary premium — delta in salary for vacancies requiring a skill
- Skill clusters and detected tech stacks

## Config (`config.py`)

```python
USER_SKILLS = ['python', 'django', 'git', 'sql', 'html', 'css']
PROFESSION_NAME = 'Python разработчик'
VACANCIES_PER_PAGE = 100
TOTAL_PAGES_TO_PARSE = 5
CONCURRENT_REQUESTS = 10
```

## Setup

```bash
pip install aiohttp pymorphy2 nltk networkx
python -c "import nltk; nltk.download('stopwords')"
python main.py
```

## Files

| File | Description |
|------|-------------|
| `main.py` | Entry point — fetch → analyze → print report |
| `hh_api.py` | Async HH.ru API client |
| `analyzer.py` | Skill extraction, salary stats, graph building, cluster detection |
| `config.py` | Search query, user skill list, API settings, NLP init |
| `setup_nltk.py` | NLTK data download helper |
