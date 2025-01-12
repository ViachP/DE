import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
import datetime
import timeit

# Путь к файлу Excel
excel_file_path = 'live.xlsx'

# Загрузка существующего файла, если он есть
if os.path.exists(excel_file_path):
    existing_df = pd.read_excel(excel_file_path)
else:
    existing_df = pd.DataFrame()

# Список URL-адресов
urls = [
    'https://www.marathonbet.by/su/live/popular'
]

data = []
start_time = timeit.default_timer()
today_date = datetime.datetime.now().strftime('%d/%m/%Y')

# Функция для преобразования текста в float
def to_float(value):
    try:
        return float(value) if value not in ['-', '—', None, ''] else None
    except ValueError:
        return None

# Обработка каждого URL
for url in urls:
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    match_containers = soup.select('tr.sub-row')

    for match_container in match_containers:
        league_name_element = match_container.find_previous('td', class_='category-label-td')
        league_name = league_name_element.find('h2', class_='category-label').text.strip() if league_name_element else '-'

        team_names = [div.find_next_sibling('div').text.strip() for div in match_container.select('b.member-number')]

        score_time_element = match_container.select_one('div.event-description div.cl-left.red')
        if score_time_element:
            score_parts = score_time_element.text.split()  # Получаем все части текста

            if len(score_parts) == 2:
                score = score_parts[0]  # Счёт, например: "1:0"
                match_time = score_parts[1]  # Время
            elif len(score_parts) > 2:
                if '(' in score_parts[1]:
                    score = f"{score_parts[0]} {score_parts[1]}"  # Счёт, например: "1:0 (0:1)"
                else:
                    score = score_parts[0]  # Только первый элемент как счёт
                match_time = ' '.join(score_parts[2:])  # Время - остальная часть
            else:
                score = '-'  # Если счёт не найден
                match_time = '-'
        else:
            score = '-'
            match_time = '-'

        odds_elements = {
            'П1': match_container.select_one('td[data-market-type="RESULT"] span[data-selection-key$=".1"]'),
            'Х': match_container.select_one('td[data-market-type="RESULT"] span[data-selection-key$=".draw"]'),
            'П2': match_container.select_one('td[data-market-type="RESULT"] span[data-selection-key$=".3"]'),
        }

        odds_values = {key: to_float(element.text.strip() if element else '-') for key, element in odds_elements.items()}

        fora_elements = match_container.select('td[data-market-type="TOTAL"]')
        fora_values = [fora_element.select_one('span').text.strip() for fora_element in fora_elements if fora_element.select_one('span')]
        fora_values_num = [to_float(value) for value in fora_values]

        fora_coefficients = []
        for fora_element in fora_elements:
            fora_coeff = None
            for content in fora_element.contents:
                if isinstance(content, str) and '(' in content:
                    fora_coeff = content.strip('() \n')
                    break
            fora_coefficients.append(to_float(fora_coeff) if fora_coeff is not None else None)

        # Добавляем полученные данные в список
        data.append({
            'Дата': today_date,
            
            'Счет': score,
            'Время': match_time,
            'Хозяева': team_names[0] if team_names else '-',
            'Гости': team_names[1] if len(team_names) > 1 else '-',
            'П1': odds_values['П1'],
            'Х': odds_values['Х'],
            'П2': odds_values['П2'],
            'тотал': fora_coefficients[0] if fora_coefficients else None,
            'ТМ': fora_values_num[0] if fora_values_num else None,
            'ТБ': fora_values_num[1] if len(fora_values_num) > 1 else None,
            'Лига': league_name
        })

# Отладочная информация
end_time = timeit.default_timer()
print(f'Время выполнения скрипта: {end_time - start_time:.2f} секунд')
print(f'Собрано матчей: {len(data)}')

# Если данные не были собраны, загрузка не требуется
if not data:
    print("Нет данных для добавления.")
    exit()

# Создание DataFrame из собранных данных
new_df = pd.DataFrame(data)

# Проверка уникальных значений в колонке 'Время'
print("Уникальные значения в колонке 'Время':")
print(new_df['Время'].unique())

# Фильтрация данных по значению в колонке 'Время'
filtered_df = new_df[new_df['Время'].str.contains('Пер\.')]  # Используем contains для поиска подстроки

# Отладочная информация по фильтру
print("Отфильтрованные данные:")
print(filtered_df)  # Вывод отфильтрованных данных
print(f"Количество отфильтрованных матчей: {len(filtered_df)}")

# Объединяем с существующими данными, проверяем на дубликаты по всем столбцам
if not filtered_df.empty:
    combined_df = pd.concat([existing_df, filtered_df]).drop_duplicates()
    # Запись в файл XLSX
    combined_df.to_excel(excel_file_path, index=False)
    print("Данные сохранены в файл 'live.xlsx'.")
else:
    print("Нет матчей с 'Пер' в колонке 'Время'. Данные не будут сохранены.")
