# analyzer.py
import re
from collections import Counter, defaultdict
from itertools import combinations
import networkx as nx
import community as community_louvain

from config import USER_SKILLS, KNOWN_SKILLS, morph, russian_stopwords

# --- Обработка текста вакансии ---
def process_text(text):
    text = re.sub(r'<.*?>', ' ', text)
    text = re.sub(r'[^a-zA-Zа-яА-Я+#/.\s]', ' ', text).lower()
    return [morph.parse(word)[0].normal_form
            for word in text.split()
            if word not in russian_stopwords and len(word) > 1]

def extract_skills_from_text(words, known_skills):
    return {word for word in words if word in known_skills}

# --- Основная аналитика ---
def analyze_vacancies(vacancies, user_skills):
    salaries = []
    missing_skills_counter = Counter()
    skill_counter = Counter()

    user_skills_set = set(user_skills)

    for vac in vacancies:
        # --- зарплата ---
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

        # --- навыки из тегов ---
        vac_skills_tags = {s['name'].lower() for s in vac.get('key_skills', [])}

        # --- навыки из текста ---
        description_text = vac.get('description', '')
        vac_skills_text = extract_skills_from_text(
            process_text(description_text),
            KNOWN_SKILLS
        )

        # --- объединяем ---
        all_skills = vac_skills_tags.union(vac_skills_text)

        # считаем спрос
        skill_counter.update(all_skills)

        # считаем недостающие навыки
        missing_skills_counter.update(all_skills - user_skills_set)

    # --- зарплаты ---
    avg_salary = int(sum(salaries) / len(salaries)) if salaries else 0
    sorted_salaries = sorted(salaries)
    median_salary = (
        int(sorted_salaries[len(sorted_salaries)//2])
        if sorted_salaries else 0
    )
    total_vacancies = len(vacancies)

    # --- Skill Demand Index ---
    skill_demand_index = []
    for skill, count in skill_counter.most_common():
        percentage = (count / total_vacancies) * 100
        skill_demand_index.append((skill, round(percentage, 1)))

    return {
        'avg_salary': avg_salary,
        'median_salary': median_salary,
        'missing_skills': missing_skills_counter.most_common(15),
        'skill_demand_index': skill_demand_index[:20],
        'total_vacancies_analyzed': total_vacancies
    }

def calculate_skill_salary_premium(vacancies):
    skill_salary = {}
    skill_counts = {}

    for vac in vacancies:
        salary_info = vac.get('salary')

        if not salary_info or salary_info['currency'] != 'RUR':
            continue

        salary_from = salary_info.get('from') or 0
        salary_to = salary_info.get('to') or 0

        if salary_from and salary_to:
            salary = (salary_from + salary_to) / 2
        elif salary_from:
            salary = salary_from
        elif salary_to:
            salary = salary_to
        else:
            continue

        # навыки
        vac_skills_tags = {s['name'].lower() for s in vac.get('key_skills', [])}
        description_text = vac.get('description', '')
        vac_skills_text = extract_skills_from_text(
            process_text(description_text),
            KNOWN_SKILLS
        )

        all_skills = vac_skills_tags.union(vac_skills_text)

        for skill in all_skills:
            skill_salary.setdefault(skill, []).append(salary)
            skill_counts[skill] = skill_counts.get(skill, 0) + 1

    # общий средний уровень
    all_salaries = []
    for vac in vacancies:
        salary_info = vac.get('salary')
        if not salary_info or salary_info['currency'] != 'RUR':
            continue
        salary_from = salary_info.get('from') or 0
        salary_to = salary_info.get('to') or 0
        if salary_from and salary_to:
            all_salaries.append((salary_from + salary_to) / 2)
        elif salary_from:
            all_salaries.append(salary_from)
        elif salary_to:
            all_salaries.append(salary_to)

    if not all_salaries:
        return []

    market_avg_salary = sum(all_salaries) / len(all_salaries)

    premium_list = []
    for skill, salaries in skill_salary.items():
        if len(salaries) < 5:
            continue
        avg_skill_salary = sum(salaries) / len(salaries)
        premium = avg_skill_salary - market_avg_salary
        premium_list.append((skill, int(premium)))

    premium_list.sort(key=lambda x: x[1], reverse=True)
    return premium_list[:15]

# --- Графы и кластеризация ---
def build_skill_graph_lite(vacancies):
    skill_graph = defaultdict(int)

    for vac in vacancies:
        vac_skills_tags = {s['name'].lower() for s in vac.get('key_skills', [])}
        description_text = vac.get('description', '')
        vac_skills_text = extract_skills_from_text(
            process_text(description_text),
            KNOWN_SKILLS
        )

        all_skills = list(vac_skills_tags.union(vac_skills_text))

        for skill1, skill2 in combinations(all_skills, 2):
            pair = tuple(sorted((skill1, skill2)))
            skill_graph[pair] += 1

    return skill_graph

def build_network_graph(skill_graph):
    G = nx.Graph()
    for (skill1, skill2), weight in skill_graph.items():
        if weight >= 20:
            G.add_edge(skill1, skill2, weight=weight)
    return G

def detect_skill_clusters(G):
    partition = community_louvain.best_partition(G)
    clusters = {}
    for skill, cluster_id in partition.items():
        if cluster_id not in clusters:
            clusters[cluster_id] = []
        clusters[cluster_id].append(skill)
    return clusters

def build_skill_graph(vacancies):
    G = nx.Graph()
    for v in vacancies:
        skills = set(v.get("skills", []))
        for s in skills:
            if not G.has_node(s):
                G.add_node(s)
        for s1, s2 in combinations(skills, 2):
            if G.has_edge(s1, s2):
                G[s1][s2]["weight"] += 1
            else:
                G.add_edge(s1, s2, weight=1)
    return G

def filter_graph(G, min_weight=3):
    G2 = nx.Graph()
    for u, v, data in G.edges(data=True):
        if data["weight"] >= min_weight:
            G2.add_edge(u, v, weight=data["weight"])
    return G2

def detect_stacks(G):
    partition = community_louvain.best_partition(G)
    stacks = {}
    for skill, cluster in partition.items():
        stacks.setdefault(cluster, []).append(skill)
    return stacks

# --- Функции вывода (оставить как есть, будут вызваны из main) ---
def print_skill_clusters(clusters):
    print("\n Найденные технологические стеки (Lite version):\n")
    for cluster_id, skills in clusters.items():
        if len(skills) < 3:
            continue
        print(f"Stack {cluster_id + 1}:")
        skills = list(skills)[:10]
        for skill in sorted(skills):
            print(f"  - {skill}")
        print()

def print_stacks(stacks):
    print("\nНайденные технологические стеки:\n")
    for i, skills in enumerate(stacks.values(), 1):
        if len(skills) < 3:
            continue
        print(f"\nStack {i}:")
        for s in sorted(skills):
            print(f"  - {s}")
        print()