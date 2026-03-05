import asyncio
import aiohttp
import time
import re
from collections import Counter
from tqdm.asyncio import tqdm_asyncio

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

# NLP инструменты
morph = pymorphy2.MorphAnalyzer()
russian_stopwords = stopwords.words("russian")

# --- Обработка текста вакансии ---
def process_text(text):
    text = re.sub(r'<.*?>', ' ', text)
    text = re.sub(r'[^a-zA-Zа-яА-Я+#/.\s]', ' ', text).lower()
    return [morph.parse(word)[0].normal_form
            for word in text.split()
            if word not in russian_stopwords and len(word) > 1]

def extract_skills_from_text(words, known_skills):
    return {word for word in words if word in known_skills}


# --- Асинхронные функции для работы с HH.ru ---
async def fetch_json(session, url, retries=3):
    for _ in range(retries):
        try:
            async with session.get(url, timeout=15) as response:
                return await response.json()
        except Exception:
            await asyncio.sleep(1)
    return {}

async def fetch_vacancy(session, vacancy_id, retries=3):
    url = f"{HH_API_URL}/{vacancy_id}"
    for attempt in range(retries):
        try:
            async with session.get(url, timeout=15) as response:
                return await response.json()
        except Exception as e:
            if attempt < retries - 1:
                await asyncio.sleep(0.5)
            else:
                print(f"Не удалось загрузить {vacancy_id}: {e}")
                return {}

async def fetch_all_vacancies(session, vacancy_list):
    semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)

    async def fetch_with_semaphore(vacancy_id):
        async with semaphore:
            return await fetch_vacancy(session, vacancy_id)

    tasks = [fetch_with_semaphore(v['id']) for v in vacancy_list]
    results = []
    for f in tqdm_asyncio.as_completed(tasks, desc="Загрузка вакансий"):
        result = await f
        if not result:
            print("Потеряна вакансия")  # <-- сюда добавляем лог
        else:
            results.append(result)
    return results

def analyze_vacancies(vacancies, user_skills):
    salaries = []
    missing_skills_counter = Counter()
    user_skills_set = set(user_skills)

    for vac in vacancies:
        salary_info = vac.get('salary')
        if salary_info and salary_info['currency'] == 'RUR':
            salary_from = salary_info.get('from') or 0
            salary_to = salary_info.get('to') or 0
            if salary_from and salary_to:
                salaries.append((salary_from + salary_to) / 2)
            elif salary_from:
                salaries.append(salary_from)
            elif salary_to:
                salaries.append(salary_to)

        vac_skills_tags = {s['name'].lower() for s in vac.get('key_skills', [])}
        description_text = vac.get('description', '')
        vac_skills_text = extract_skills_from_text(process_text(description_text), KNOWN_SKILLS)

        all_skills = vac_skills_tags.union(vac_skills_text)
        missing_skills_counter.update(all_skills - user_skills_set)

    avg_salary = int(sum(salaries) / len(salaries)) if salaries else 0
    sorted_salaries = sorted(salaries)
    median_salary = int(sorted_salaries[len(sorted_salaries)//2]) if sorted_salaries else 0

    print(f"DEBUG: всего найдено уникальных missing skills: {len(missing_skills_counter)}")

    return {
        'avg_salary': avg_salary,
        'median_salary': median_salary,
        'missing_skills': missing_skills_counter.most_common(15),
        'total_vacancies_analyzed': len(vacancies)
    }


async def get_vacancy_list_with_param(api_filters=None):
    """
    Загружает вакансии с HH.ru с реальными фильтрами API.
    :param api_filters: dict с фильтрами API (salary, area, experience, employment, schedule)
    """
    all_vacs = []
    api_filters = api_filters or {}
    #----------- впн
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0 Safari/537.36"
    }

    timeout = aiohttp.ClientTimeout(total=30)

    async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
    # async with aiohttp.ClientSession() as session:
        for page in range(TOTAL_PAGES_TO_PARSE):
            params = {
                'text': PROFESSION_NAME,
                'per_page': VACANCIES_PER_PAGE,
                'page': page,
                'only_with_salary': 'true',
            }
            # добавляем реальные фильтры API
            params.update(api_filters)

            try:
                async with session.get(HH_API_URL, params=params, timeout=15) as response:
                    data = await response.json()
            except Exception as e:
                print(f"Ошибка при загрузке страницы {page}: {e}")
                continue

            items = data.get('items', [])
            if not items:
                break
            all_vacs.extend(items)
            # await asyncio.sleep(0.1)  # пауза, чтобы не перегрузить API
            await asyncio.sleep(0.3) #впн
    return all_vacs

async def get_vacancy_list():
    all_vacs = []
    # ----------- впн
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0 Safari/537.36"
    }

    timeout = aiohttp.ClientTimeout(total=30)

    async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
    # async with aiohttp.ClientSession() as session:
        for page in range(TOTAL_PAGES_TO_PARSE):
            params = {
                'text': PROFESSION_NAME,
                'area': 1,
                'per_page': VACANCIES_PER_PAGE,
                'page': page,
                'only_with_salary': True
            }
            data = await fetch_json(session, f"{HH_API_URL}?text={PROFESSION_NAME}&area=1&per_page={VACANCIES_PER_PAGE}&page={page}&only_with_salary=True")
            if not data.get('items'):
                break
            all_vacs.extend(data['items'])
            # await asyncio.sleep(0.1)  # пауза, чтобы не перегрузить API
            await asyncio.sleep(0.3)  # впн
    return all_vacs


async def main():
    print(f"Загружаю вакансии по запросу '{PROFESSION_NAME}'...")
    vacancy_list = await get_vacancy_list()
    print(f"Всего вакансий для загрузки: {len(vacancy_list)}")

    async with aiohttp.ClientSession() as session:
        full_vacancies = await fetch_all_vacancies(session, vacancy_list)

    analysis_result = analyze_vacancies(full_vacancies, USER_SKILLS)

    print("\n" + "-"*30)
    print(f"Отчет по рынку для '{PROFESSION_NAME}'")
    print("-"*30 + "\n")

    print(f"Средняя зарплата: {analysis_result['avg_salary']:,} RUB".replace(',', ' '))
    print(f"Медианная зарплата: {analysis_result['median_salary']:,} RUB".replace(',', ' '))
    print(f"(проанализировано {analysis_result['total_vacancies_analyzed']} вакансий с зарплатой в RUR)")

    print("\nТОП-15 недостающих навыков (из тегов и текста вакансий):")
    total = analysis_result['total_vacancies_analyzed']
    for skill, count in analysis_result['missing_skills']:
        percentage = (count / total) * 100
        print(f"- {skill.capitalize()} (встречается в ~{percentage:.0f}% вакансий)")

    print(f"\n\n")
    api_filters = {
        'area': 1,
        'salary': 150000,
        'experience': 'between3And6',
        'employment': 'full',
        'schedule': 'fullDay',
    }

    vacancy_list_with_param = await get_vacancy_list_with_param(api_filters)
    print(f"Всего вакансий после фильтров API: {len(vacancy_list_with_param)}")


if __name__ == '__main__':
    asyncio.run(main())