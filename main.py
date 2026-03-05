# main.py
import asyncio
import aiohttp
import time

from config import PROFESSION_NAME, USER_SKILLS
from hh_api import get_vacancy_list, fetch_all_vacancies, get_vacancy_list_with_param
from analyzer import (
    analyze_vacancies,
    calculate_skill_salary_premium,
    build_skill_graph_lite,
    build_network_graph,
    detect_skill_clusters,
    print_skill_clusters,
    build_skill_graph,
    filter_graph,
    detect_stacks,
    print_stacks,
    extract_skills_from_text,
    process_text,
    KNOWN_SKILLS
)

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

    print("\nSkill Demand Index (топ навыков рынка):")
    for skill, percent in analysis_result['skill_demand_index']:
        print(f"{skill.capitalize():15} {percent}% вакансий")

    salary_premium = calculate_skill_salary_premium(full_vacancies)

    print("\n Skill Salary Premium (навыки увеличивающие зарплату):\n")
    for skill, premium in salary_premium:
        sign = "+" if premium > 0 else ""
        print(f"{skill.capitalize():15} {sign}{premium:,} RUB".replace(",", " "))

    for vac in full_vacancies:
        vac_skills_tags = {s['name'].lower() for s in vac.get('key_skills', [])}
        description_text = vac.get('description', '')
        vac_skills_text = extract_skills_from_text(process_text(description_text), KNOWN_SKILLS)
        vac['skills'] = list(vac_skills_tags.union(vac_skills_text))

    skill_graph = build_skill_graph_lite(full_vacancies)
    G_lite = build_network_graph(skill_graph)
    clusters = detect_skill_clusters(G_lite)
    print_skill_clusters(clusters)

    G = build_skill_graph(full_vacancies)
    G = filter_graph(G, min_weight=5)
    stacks = detect_stacks(G)
    print_stacks(stacks)

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