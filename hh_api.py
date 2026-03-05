# hh_api.py
import asyncio
import aiohttp
from tqdm.asyncio import tqdm_asyncio

from config import PROFESSION_NAME, HH_API_URL, VACANCIES_PER_PAGE, TOTAL_PAGES_TO_PARSE, CONCURRENT_REQUESTS, HEADERS


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
            print("Потеряна вакансия")
        else:
            results.append(result)
    return results


async def get_vacancy_list():
    all_vacs = []
    timeout = aiohttp.ClientTimeout(total=30)

    async with aiohttp.ClientSession(headers=HEADERS, timeout=timeout) as session:
        for page in range(TOTAL_PAGES_TO_PARSE):
            params = {
                'text': PROFESSION_NAME,
                'area': 1,
                'per_page': VACANCIES_PER_PAGE,
                'page': page,
                'only_with_salary': True
            }
            data = await fetch_json(session,
                                    f"{HH_API_URL}?text={PROFESSION_NAME}&area=1&per_page={VACANCIES_PER_PAGE}&page={page}&only_with_salary=True")
            if not data.get('items'):
                break
            all_vacs.extend(data['items'])
            await asyncio.sleep(0.3)
    return all_vacs


async def get_vacancy_list_with_param(api_filters=None):
    """
    Загружает вакансии с HH.ru с реальными фильтрами API.
    :param api_filters: dict с фильтрами API (salary, area, experience, employment, schedule)
    """
    all_vacs = []
    api_filters = api_filters or {}

    timeout = aiohttp.ClientTimeout(total=30)

    async with aiohttp.ClientSession(headers=HEADERS, timeout=timeout) as session:
        for page in range(TOTAL_PAGES_TO_PARSE):
            params = {
                'text': PROFESSION_NAME,
                'per_page': VACANCIES_PER_PAGE,
                'page': page,
                'only_with_salary': 'true',
            }
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
            await asyncio.sleep(0.3)
    return all_vacs