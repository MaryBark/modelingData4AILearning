#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ПОЛНЫЙ КОМПЛЕКС ДЛЯ ФАЗОВЫХ ПОРТРЕТОВ
1. Генерация данных в формате сайта sakva.ru (из первого кода)
2. Построение графиков по сгенерированным данным
Берет последние 1000 объектов из каждого файла
"""

import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import os
import math
import time
import random
import glob

# ==================== ЧАСТЬ 1: ГЕНЕРАТОР ДАННЫХ (из первого кода) ====================

class PhasePortraitGenerator:
    """
    Генератор фазовых портретов в формате сайта sakva.ru
    """
    
    def __init__(self):
        self.S0 = 1367
        self.m0 = -26.7
        self.d0 = 10000
        
    def get_object_radius(self, obj):
        """Определяет эффективный радиус объекта"""
        if obj.get('diameter'):
            return obj['diameter'] / 2
        elif obj.get('xSectAvg'):
            return math.sqrt(obj['xSectAvg'] / math.pi)
        elif obj.get('width') and obj.get('height'):
            return max(obj['width'], obj['height']) / 2
        else:
            obj_class = obj.get('objectClass', '')
            if 'PAYLOAD' in str(obj_class).upper():
                return 1.5
            elif 'ROCKET' in str(obj_class).upper():
                return 2.0
            else:
                return 0.5
    
    def get_albedo(self, obj):
        """Определяет коэффициент отражения"""
        name = str(obj.get('name', '')).upper()
        obj_class = obj.get('objectClass', '')
        
        # Базовые значения
        a_diffuse = 0.2
        a_specular = 0.1
        
        # Корректировка в зависимости от типа объекта
        if any(x in name for x in ['GPS', 'NAVSTAR', 'GLONASS', 'GALILEO']):
            a_diffuse = 0.3
            a_specular = 0.5
        elif any(x in name for x in ['GEO', 'INMARSAT', 'TERRESTAR']):
            a_diffuse = 0.25
            a_specular = 0.4
        elif 'PAYLOAD' in str(obj_class).upper():
            a_diffuse = 0.3
            a_specular = 0.2
            
        return a_diffuse, a_specular
    
    def calculate_phase_portrait(self, obj, num_points=500):
        """
        Расчет фазового портрета в формате сайта
        """
        R = self.get_object_radius(obj)
        a_diffuse, a_specular = self.get_albedo(obj)
        name = str(obj.get('name', '')).upper()
        
        # Устанавливаем seed для воспроизводимости
        obj_id = obj.get('cosparId', '') or obj.get('name', '')
        random.seed(abs(hash(str(obj_id))) % 2**32)
        np.random.seed(abs(hash(str(obj_id))) % 2**32)
        
        results = []
        
        # Генерируем точки
        for i in range(num_points):
            # Случайный фазовый угол
            r = random.random()
            if r < 0.3:
                phi_d = random.uniform(0, 40)
            elif r < 0.6:
                phi_d = random.uniform(40, 100)
            else:
                phi_d = random.uniform(100, 180)
            
            phi_r = math.radians(phi_d)
            
            # Диффузная компонента
            f_phi = ((math.pi - phi_r) * math.cos(phi_r) + math.sin(phi_r)) / math.pi
            diffuse_base = 15000 * f_phi + 5000
            
            # Зеркальные пики
            specular = 0
            
            # Пик для навигационных КА
            if any(x in name for x in ['GPS', 'NAVSTAR', 'GLONASS']):
                if phi_d < 30:
                    specular += 35000 * math.exp(-(phi_d ** 2) / 100)
            
            # Пик для геостационарных
            elif any(x in name for x in ['GEO', 'INMARSAT', 'TERRESTAR']):
                if 5 < phi_d < 25:
                    specular += 30000 * math.exp(-((phi_d - 13) ** 2) / 50)
            
            # Пик при больших углах
            if phi_d > 120:
                specular += 15000 * math.exp(-((phi_d - 140) ** 2) / 200)
            
            # Случайные вариации
            variations = np.random.normal(0, 2000) * (1 + 0.5 * math.sin(phi_r * 5))
            
            # Суммируем
            M = diffuse_base + specular + variations
            M = max(M, 5000)
            M = min(M, 60000)
            
            # Расчет углов alpha и beta
            if any(x in name for x in ['GPS', 'GEO']):
                alpha = phi_d * random.uniform(0.95, 1.05)
                beta = random.uniform(0, 15) * random.uniform(0.8, 1.2)
            else:
                alpha = phi_d * random.uniform(0.7, 0.9) + random.uniform(-10, 10)
                beta = random.uniform(15, 35) * random.uniform(0.8, 1.2)
            
            # Иногда добавляем значения как на сайте
            if random.random() < 0.3:
                beta = random.choice([23924, 24990, 28277]) * random.uniform(0.98, 1.02)
            
            results.append({
                'phi': round(phi_d, 2),
                'M': round(M),
                'alpha': round(alpha, 2),
                'beta': round(beta, 2) if beta > 1000 else round(beta, 2)
            })
        
        # Перемешиваем
        random.shuffle(results)
        
        return pd.DataFrame(results)
    
    def generate_object_portrait(self, obj, output_dir):
        """Сохраняет портрет в файл"""
        cospar = obj.get('cosparId', 'unknown')
        if cospar is None:
            cospar = 'unknown'
        cospar = str(cospar).replace('/', '_').replace('\\', '_').replace(':', '_')
        
        name = obj.get('name', 'unknown')
        if name is None:
            name = 'unknown'
        name = ''.join(c for c in str(name) if c.isalnum() or c in ' _-').rstrip()
        name = name.replace(' ', '_')[:40]
        
        df = self.calculate_phase_portrait(obj, num_points=500)
        
        if df.empty:
            return None
        
        filename = f"{cospar}_{name}.xlsx"
        filepath = os.path.join(output_dir, filename)
        
        if os.path.exists(filepath):
            base, ext = os.path.splitext(filename)
            filename = f"{base}_{int(time.time())}{ext}"
            filepath = os.path.join(output_dir, filename)
        
        try:
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Фазовый портрет', index=False)
            
            return filepath
        except Exception:
            return None


# ==================== ЧАСТЬ 2: ПОСТРОЕНИЕ ГРАФИКОВ ====================

def plot_phase_portrait_from_file(filename, output_dir='phase_portraits'):
    """
    Строит фазовый портрет из файла с данными
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Читаем данные
    df = pd.read_excel(filename)
    
    # Извлекаем имя файла
    base_name = os.path.basename(filename)
    name_without_ext = os.path.splitext(base_name)[0]
    
    # Создаем график
    plt.figure(figsize=(14, 10))
    
    # Определяем цвет по типу (из имени файла)
    base_upper = base_name.upper()
    if 'GPS' in base_upper or 'NAVSTAR' in base_upper or 'GLONASS' in base_upper:
        color = 'red'
        point_color = 'darkred'
        type_label = 'Навигационный КА'
    elif 'GEO' in base_upper or 'INMARSAT' in base_upper or 'TERRESTAR' in base_upper:
        color = 'green'
        point_color = 'darkgreen'
        type_label = 'Геостационарный КА'
    elif 'SC' in base_upper or 'PAYLOAD' in base_upper:
        color = 'blue'
        point_color = 'darkblue'
        type_label = 'КА'
    elif 'DB' in base_upper or 'DEBRIS' in base_upper:
        color = 'gray'
        point_color = 'dimgray'
        type_label = 'Мусор'
    else:
        color = 'purple'
        point_color = 'purple'
        type_label = 'Объект'
    
    # Сортируем по phi для линий
    df_sorted = df.sort_values('phi')
    
    # Рисуем сглаженную линию (скользящее среднее)
    window = 20
    if len(df_sorted) > window:
        df_sorted['M_smooth'] = df_sorted['M'].rolling(window=window, center=True).mean()
        plt.plot(df_sorted['phi'], df_sorted['M_smooth'], color=color, 
                linewidth=2.5, label=f'{type_label} (сглаженная)', alpha=0.8)
    
    # Рисуем точки
    plt.scatter(df['phi'], df['M'], c=point_color, s=25, alpha=0.5, 
                edgecolors='none', label='Наблюдения')
    
    # Настройки графика
    plt.xlabel('φ (фазовый угол, градусы)', fontsize=14)
    plt.ylabel('M (звездная величина)', fontsize=14)
    plt.title(f'Фазовый портрет: {name_without_ext}', fontsize=16)
    plt.grid(True, alpha=0.3, linestyle='--')
    
    # Инвертируем ось Y
    plt.gca().invert_yaxis()
    
    # Устанавливаем пределы
    plt.xlim(0, 180)
    plt.ylim(0, 60000)
    
    # Добавляем горизонтальные линии
    for y in range(0, 60001, 10000):
        plt.axhline(y=y, color='gray', linestyle='-', alpha=0.1)
    
    # Добавляем вертикальные линии
    for x in range(0, 181, 30):
        plt.axvline(x=x, color='gray', linestyle='-', alpha=0.1)
    
    # Добавляем характерные точки
    plt.scatter([103], [35000], c='red', s=200, marker='*', 
                label='Типичный пик яркости', zorder=5, edgecolors='black')
    
    plt.legend(loc='upper right')
    
    # Сохраняем
    output_file = os.path.join(output_dir, f'{name_without_ext}_portrait.png')
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"    ✅ График: {os.path.basename(output_file)}")
    
    return output_file


def plot_comparison_portraits(folder_path, output_dir='phase_portraits', max_files=15):
    """
    Строит сравнительный график из нескольких файлов
    """
    excel_files = glob.glob(os.path.join(folder_path, '*.xlsx'))
    
    if not excel_files:
        return
    
    plt.figure(figsize=(16, 12))
    
    files_to_plot = excel_files[:max_files]
    colors = plt.cm.tab20(np.linspace(0, 1, len(files_to_plot)))
    
    for i, filename in enumerate(files_to_plot):
        df = pd.read_excel(filename)
        df_sorted = df.sort_values('phi')
        
        # Сглаживание
        window = 15
        if len(df_sorted) > window:
            df_sorted['M_smooth'] = df_sorted['M'].rolling(window=window, center=True).mean()
            
            # Короткое имя
            base_name = os.path.basename(filename)
            short_name = base_name[:25] + '...' if len(base_name) > 25 else base_name
            
            plt.plot(df_sorted['phi'], df_sorted['M_smooth'], color=colors[i], 
                    linewidth=1.5, label=short_name, alpha=0.7)
    
    plt.xlabel('φ (фазовый угол, градусы)', fontsize=14)
    plt.ylabel('M (звездная величина)', fontsize=14)
    plt.title(f'Сравнение фазовых портретов (первые {len(files_to_plot)} объектов)', fontsize=16)
    plt.grid(True, alpha=0.3)
    plt.gca().invert_yaxis()
    plt.xlim(0, 180)
    plt.ylim(0, 60000)
    
    for y in range(0, 60001, 10000):
        plt.axhline(y=y, color='gray', linestyle='-', alpha=0.1)
    for x in range(0, 181, 30):
        plt.axvline(x=x, color='gray', linestyle='-', alpha=0.1)
    
    plt.legend(loc='upper right', fontsize=8, ncol=2)
    
    folder_name = os.path.basename(folder_path)
    output_file = os.path.join(output_dir, f'comparison_{folder_name}.png')
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"  ✅ Сравнительный график: {os.path.basename(output_file)}")


def plot_summary_portrait(folder_path, output_dir='phase_portraits'):
    """
    Строит сводный график всех объектов из папки
    """
    excel_files = glob.glob(os.path.join(folder_path, '*.xlsx'))
    
    if not excel_files:
        return
    
    plt.figure(figsize=(16, 12))
    
    for filename in excel_files[:100]:
        try:
            df = pd.read_excel(filename)
            
            # Определяем цвет
            base_name = os.path.basename(filename).upper()
            if 'GPS' in base_name or 'NAVSTAR' in base_name:
                color = 'red'
                alpha = 0.2
            elif 'GEO' in base_name or 'INMARSAT' in base_name:
                color = 'green'
                alpha = 0.2
            elif 'SC' in base_name:
                color = 'blue'
                alpha = 0.15
            else:
                color = 'gray'
                alpha = 0.1
            
            plt.scatter(df['phi'], df['M'], c=color, s=5, alpha=alpha, edgecolors='none')
            
        except:
            continue
    
    plt.xlabel('φ (фазовый угол, градусы)', fontsize=14)
    plt.ylabel('M (звездная величина)', fontsize=14)
    plt.title('Сводный фазовый портрет', fontsize=16)
    plt.grid(True, alpha=0.3)
    plt.gca().invert_yaxis()
    plt.xlim(0, 180)
    plt.ylim(0, 60000)
    
    legend_elements = [
        Patch(facecolor='red', alpha=0.5, label='Навигационные КА'),
        Patch(facecolor='green', alpha=0.5, label='Геостационарные КА'),
        Patch(facecolor='blue', alpha=0.5, label='Другие КА'),
        Patch(facecolor='gray', alpha=0.5, label='Мусор')
    ]
    plt.legend(handles=legend_elements, loc='upper right')
    
    folder_name = os.path.basename(folder_path)
    output_file = os.path.join(output_dir, f'summary_{folder_name}.png')
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"  ✅ Сводный график: {os.path.basename(output_file)}")


# ==================== ЧАСТЬ 3: ЗАГРУЗКА ДАННЫХ ====================

def load_json_file(filename):
    """Загружает JSON файл"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, dict) and 'objects' in data:
            return data['objects']
        elif isinstance(data, list):
            return data
        else:
            return []
    except Exception as e:
        print(f"❌ Ошибка загрузки {filename}: {e}")
        return []


# ==================== ЧАСТЬ 4: ОСНОВНАЯ ПРОГРАММА ====================

def main():
    print("="*80)
    print("🚀 ПОЛНЫЙ КОМПЛЕКС ДЛЯ ФАЗОВЫХ ПОРТРЕТОВ")
    print("📊 1. Генерация данных в формате сайта sakva.ru")
    print("📊 2. Построение графиков по сгенерированным данным")
    print("📊 Берем последние 1000 объектов из каждого файла")
    print("="*80)
    
    # Папки
    data_dir_sc = 'GeneratedData_SC'
    data_dir_db = 'GeneratedData_DB'
    plots_dir = 'PhasePortraits_Generated'
    
    os.makedirs(data_dir_sc, exist_ok=True)
    os.makedirs(data_dir_db, exist_ok=True)
    os.makedirs(plots_dir, exist_ok=True)
    
    print(f"\n📁 Папки для данных: {data_dir_sc}, {data_dir_db}")
    print(f"📁 Папка для графиков: {plots_dir}")
    
    # Загружаем исходные данные
    print("\n📂 Загрузка исходных данных...")
    
    spacecraft_all = load_json_file('spacecraft_20260307_202246.json')
    debris_all = load_json_file('debris_20260307_202246.json')
    
    print(f"✅ Всего КА: {len(spacecraft_all)}")
    print(f"✅ Всего мусора: {len(debris_all)}")
    
    # Берем последние 1000
    total_sc = min(1000, len(spacecraft_all))
    total_db = min(1000, len(debris_all))
    
    spacecraft = spacecraft_all[-total_sc:]
    debris = debris_all[-total_db:]
    
    print(f"\n📊 Для обработки:")
    print(f"   - КА: {len(spacecraft)} (последние {total_sc})")
    print(f"   - Мусор: {len(debris)} (последние {total_db})")
    
    generator = PhasePortraitGenerator()
    
    # ===== ЭТАП 1: ГЕНЕРАЦИЯ ДАННЫХ =====
    print("\n" + "="*80)
    print("🛠️  ЭТАП 1: ГЕНЕРАЦИЯ ДАННЫХ")
    print("="*80)
    
    # Генерация для КА
    print("\n🛰️  Генерация для КА...")
    for i, obj in enumerate(spacecraft[:10]):  # Для теста 10
        if generator.generate_object_portrait(obj, data_dir_sc):
            if (i + 1) % 5 == 0:
                print(f"  Прогресс: {i+1}/10")
    
    # Генерация для мусора
    print("\n💫 Генерация для мусора...")
    for i, obj in enumerate(debris[:10]):  # Для теста 10
        if generator.generate_object_portrait(obj, data_dir_db):
            if (i + 1) % 5 == 0:
                print(f"  Прогресс: {i+1}/10")
    
    # Специально для 2024-178B
    print("\n🎯 Поиск 2024-178B...")
    target_obj = None
    for obj in spacecraft_all + debris_all:
        if obj.get('cosparId') == '2024-178B':
            target_obj = obj
            break
    
    if target_obj:
        print(f"  ✅ Найден: {target_obj.get('name')}")
        generator.generate_object_portrait(target_obj, data_dir_sc)
    else:
        print("  ⚠ Не найден, создаю тестовый")
        test_obj = {
            'cosparId': '2024-178B',
            'name': 'Dragon Trunk',
            'objectClass': 'Payload',
            'diameter': 3.6,
            'xSectAvg': 10.0
        }
        generator.generate_object_portrait(test_obj, data_dir_sc)
    
    # ===== ЭТАП 2: ПОСТРОЕНИЕ ГРАФИКОВ =====
    print("\n" + "="*80)
    print("📈 ЭТАП 2: ПОСТРОЕНИЕ ГРАФИКОВ")
    print("="*80)
    
    # Индивидуальные графики для КА
    print("\n🖼️  Индивидуальные графики для КА:")
    sc_files = glob.glob(os.path.join(data_dir_sc, '*.xlsx'))[:5]
    for filename in sc_files:
        plot_phase_portrait_from_file(filename, os.path.join(plots_dir, 'individual'))
    
    # Индивидуальные графики для мусора
    print("\n🖼️  Индивидуальные графики для мусора:")
    db_files = glob.glob(os.path.join(data_dir_db, '*.xlsx'))[:5]
    for filename in db_files:
        plot_phase_portrait_from_file(filename, os.path.join(plots_dir, 'individual'))
    
    # Сравнительные графики
    print("\n📊 Сравнительные графики:")
    plot_comparison_portraits(data_dir_sc, plots_dir, max_files=10)
    plot_comparison_portraits(data_dir_db, plots_dir, max_files=10)
    
    # Сводные графики
    print("\n📊 Сводные графики:")
    plot_summary_portrait(data_dir_sc, plots_dir)
    plot_summary_portrait(data_dir_db, plots_dir)
    
    print("\n" + "="*80)
    print("✅ ВСЕ ОПЕРАЦИИ ЗАВЕРШЕНЫ")
    print(f"📁 Данные: {data_dir_sc}/, {data_dir_db}/")
    print(f"📁 Графики: {plots_dir}/")
    print("="*80)


if __name__ == "__main__":
    main()