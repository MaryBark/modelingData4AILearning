import json

def analyze_json_structure(filename):
    """Анализирует структуру JSON файла"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"\n📁 Анализ файла: {filename}")
        print(f"Тип данных: {type(data).__name__}")
        
        if isinstance(data, dict):
            print(f"Ключи верхнего уровня: {list(data.keys())}")
            if 'data' in data and isinstance(data['data'], list):
                print(f"Количество записей в data: {len(data['data'])}")
                if data['data']:
                    print("Пример первой записи:")
                    print(json.dumps(data['data'][0], indent=2)[:500])
        elif isinstance(data, list):
            print(f"Количество записей: {len(data)}")
            if data:
                print("Пример первой записи:")
                print(json.dumps(data[0], indent=2)[:500])
                
    except Exception as e:
        print(f"Ошибка при анализе {filename}: {e}")

# Анализируем оба файла
analyze_json_structure('spoatt.json')
analyze_json_structure('fragments.json')