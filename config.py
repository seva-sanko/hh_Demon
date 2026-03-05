# config.py
import pymorphy2
from nltk.corpus import stopwords

# --- Конфигурация ---
USER_SKILLS = ['python', 'django', 'git', 'sql', 'html', 'css']
PROFESSION_NAME = 'Python разработчик'
HH_API_URL = 'https://api.hh.ru/vacancies'
VACANCIES_PER_PAGE = 100
TOTAL_PAGES_TO_PARSE = 5
CONCURRENT_REQUESTS = 10  # количество одновременных запросов
# CONCURRENT_REQUESTS = 3  # впн версия

# --- Словарь известных навыков ---
KNOWN_SKILLS = {
    'python', 'django', 'flask', 'fastapi', 'sql', 'postgresql', 'postgres',
    'mysql', 'sqlite', 'git', 'docker', 'kubernetes', 'linux',
    'html', 'css', 'javascript', 'typescript',
    'react', 'vue', 'angular', 'rest', 'api', 'rest api', 'celery',
    'redis', 'rabbitmq', 'nginx', 'asyncio', 'aiohttp', 'pytest', 'unittest',
    'ci/cd', 'jenkins'
}

# --- Заголовки для запросов ---
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0 Safari/537.36"
}

# --- NLP инструменты (инициализация) ---
morph = pymorphy2.MorphAnalyzer()
russian_stopwords = stopwords.words("russian")