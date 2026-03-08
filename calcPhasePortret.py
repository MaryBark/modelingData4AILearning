#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Программа для расчёта фазовых портретов космических объектов
Генерация реалистичных немонотонных фазовых портретов
"""

import json
import numpy as np
import pandas as pd
import os
from datetime import datetime
import math
import warnings
warnings.filterwarnings('ignore')

class PhasePortraitCalculator:
    """
    Калькулятор фазовых портретов космических объектов
    """
    
    def __init__(self):
        self.S0 = 1367  # плотность лучистого потока Солнца (Вт/м²)
        self.m0 = -26.7  # звездная величина Солнца
        
    def get_object_dimensions(self, obj):
        """Извлекает размеры объекта"""
        shape_value = obj.get('shape')
        if shape_value is None:
            shape = ''
        else:
            shape = str(shape_value).upper()
        
        if 'SPHERE' in shape and obj.get('diameter'):
            radius = obj['diameter'] / 2
        elif obj.get('width') and obj.get('height') and obj.get('depth'):
            radius = max(obj['width'], obj['height'], obj['depth']) / 2
        elif obj.get('span'):
            radius = obj['span'] / 2
        elif obj.get('xSectAvg'):
            radius = math.sqrt(obj['xSectAvg'] / math.pi)
        else:
            radius = 1.0
            
        return radius
    
    def calculate_phase_portrait(self, obj, num_points=200):
        """
        Рассчитывает реалистичный фазовый портрет с немонотонной зависимостью
        """
        radius = self.get_object_dimensions(obj)
        name = str(obj.get('name', '')).upper()
        obj_class = str(obj.get('objectClass', '')).upper()
        
        # Генерируем фазовые углы от 0 до 180 градусов
        phi = np.linspace(0, 180, num_points)
        
        results = []
        
        for phase in phi:
            phase_rad = math.radians(phase)
            
            # ---- 1. Диффузная компонента (медленно меняется) ----
            # Формула для диффузной сферы: ((π - φ)cos φ + sin φ)/π
            f_phi = ((math.pi - phase_rad) * math.cos(phase_rad) + math.sin(phase_rad)) / math.pi
            diffuse = f_phi * 1000  # базовый уровень
            
            # ---- 2. Зеркальные компоненты (дают пики) ----
            
            # Пик 1: при малых углах (для навигационных КА)
            peak1 = 0
            if 'GPS' in name or 'NAVSTAR' in name or 'GLONASS' in name:
                # Острый пик вблизи 0
                peak1 = 50000 * np.exp(-(phase ** 2) / 50)
            elif 'INMARSAT' in name or 'TERRESTAR' in name:
                # Пик при 10-15 градусах для геостационарных
                peak1 = 40000 * np.exp(-((phase - 13) ** 2) / 30)
            else:
                # Случайный пик для обычных объектов
                peak_pos = np.random.uniform(5, 30)
                peak1 = np.random.uniform(20000, 40000) * np.exp(-((phase - peak_pos) ** 2) / 50)
            
            # Пик 2: при средних углах (отражение от корпуса)
            peak2_pos = np.random.uniform(45, 75)
            peak2 = np.random.uniform(15000, 30000) * np.exp(-((phase - peak2_pos) ** 2) / 100)
            
            # Пик 3: при больших углах (обратное отражение)
            peak3_pos = np.random.uniform(120, 150)
            peak3 = np.random.uniform(10000, 20000) * np.exp(-((phase - peak3_pos) ** 2) / 150)
            
            # ---- 3. Случайные вариации ----
            noise = np.random.normal(0, 2000) * (1 + 0.5 * math.sin(phase_rad * 5))
            
            # Суммируем все компоненты
            M = diffuse + peak1 + peak2 + peak3 + noise
            
            # Гарантируем положительные значения
            M = max(M, 1000)
            
            # ---- 4. Углы ориентации alpha и beta ----
            # Они тоже должны иметь немонотонный характер
            
            # Базовая линия
            alpha_base = phase * 0.6
            beta_base = phase * 0.55
            
            # Добавляем осцилляции
            alpha = alpha_base + 15 * math.sin(phase_rad * 3) + 10 * math.cos(phase_rad * 2)
            beta = beta_base + 12 * math.sin(phase_rad * 2.5) + 8 * math.cos(phase_rad * 3)
            
            # Добавляем пики в углах, соответствующие пикам яркости
            alpha += 5 * np.exp(-((phase - 13) ** 2) / 100)
            beta += 4 * np.exp(-((phase - 13) ** 2) / 100)
            
            # Ограничиваем значения
            alpha = min(max(alpha, 0), 180)
            beta = min(max(beta, 0), 180)
            
            results.append({
                'phi': round(phase, 2),
                'M': round(M),
                'alpha': round(alpha, 2),
                'beta': round(beta, 2)
            })
        
        return pd.DataFrame(results)
    
    def generate_object_portrait(self, obj, output_dir):
        """Генерирует и сохраняет фазовый портрет"""
        cospar = obj.get('cosparId', 'unknown')
        if cospar is None:
            cospar = 'unknown'
        cospar = str(cospar).replace('/', '_').replace('\\', '_')
        
        name = obj.get('name', 'unknown')
        if name is None:
            name = 'unknown'
        name = str(name).replace(' ', '_').replace('/', '_').replace(',', '_')
        
        if len(name) > 50:
            name = name[:50]
        
        # Генерируем портрет
        df = self.calculate_phase_portrait(obj, num_points=200)
        
        # Сохраняем в Excel
        filename = f"{cospar}_{name}.xlsx"
        filepath = os.path.join(output_dir, filename)
        
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Фазовый портрет', index=False)
            
            workbook = writer.book
            worksheet = writer.sheets['Фазовый портрет']
            
            from openpyxl.styles import numbers
            for row in range(2, len(df) + 2):
                for col in range(1, 5):
                    cell = worksheet.cell(row=row, column=col)
                    if isinstance(cell.value, (int, float)):
                        cell.number_format = numbers.FORMAT_NUMBER
        
        # Сохраняем в CSV
        csv_filename = f"{cospar}_{name}.csv"
        csv_filepath = os.path.join(output_dir, csv_filename)
        df.to_csv(csv_filepath, index=False, encoding='utf-8-sig', sep=';', decimal=',')
        
        print(f"  ✅ {filename} - M: {df['M'].min()}-{df['M'].max()}")
        
        return filepath


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
        print(f"  ❌ Ошибка загрузки {filename}: {e}")
        return []


def main():
    print("="*70)
    print("🚀 ГЕНЕРАЦИЯ ФАЗОВЫХ ПОРТРЕТОВ КОСМИЧЕСКИХ ОБЪЕКТОВ")
    print("📊 Формат: phi, M, alpha, beta (немонотонные зависимости)")
    print("="*70)
    
    # Создаем папки
    spacecraft_dir = 'Spacecrafts'
    debris_dir = 'SpaceDebris'
    
    os.makedirs(spacecraft_dir, exist_ok=True)
    os.makedirs(debris_dir, exist_ok=True)
    
    print(f"📁 Создана папка: {spacecraft_dir}")
    print(f"📁 Создана папка: {debris_dir}")
    
    # Загружаем данные
    print("\n📂 Загрузка данных...")
    
    spacecraft = load_json_file('spacecraft_20260307_202246.json')
    debris = load_json_file('debris_20260307_202246.json')
    
    print(f"✅ Загружено космических аппаратов: {len(spacecraft)}")
    print(f"✅ Загружено объектов мусора: {len(debris)}")
    
    calculator = PhasePortraitCalculator()
    
    # Обрабатываем космические аппараты
    print("\n🛰️  Генерация фазовых портретов для космических аппаратов...")
    for i, obj in enumerate(spacecraft[:50]):  # Первые 50 для теста
        if i % 10 == 0:
            print(f"  Прогресс: {i}/50")
        calculator.generate_object_portrait(obj, spacecraft_dir)
    
    # Обрабатываем космический мусор
    print("\n💫 Генерация фазовых портретов для космического мусора...")
    for i, obj in enumerate(debris[:30]):  # Первые 30 для теста
        if i % 10 == 0:
            print(f"  Прогресс: {i}/30")
        calculator.generate_object_portrait(obj, debris_dir)
    
    print("\n" + "="*70)
    print("✅ ГЕНЕРАЦИЯ ЗАВЕРШЕНА")
    print("📁 Результаты сохранены в папках:")
    print(f"   - {spacecraft_dir}/")
    print(f"   - {debris_dir}/")
    print("="*70)


if __name__ == "__main__":
    # Фиксируем seed для воспроизводимости
    np.random.seed(42)
    main()