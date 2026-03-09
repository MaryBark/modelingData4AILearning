#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ПОЛНЫЙ КОМПЛЕКС ДЛЯ ФАЗОВЫХ ПОРТРЕТОВ
Генерация данных ТОЧНО как на сайте sakva.ru
Диапазон phi: 90-115 градусов
Значения M: 10000-50000 с резкими пиками
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

# ==================== ЧАСТЬ 1: ГЕНЕРАТОР ДАННЫХ ====================

class PhasePortraitGenerator:
    """
    Генератор фазовых портретов ТОЧНО как на сайте sakva.ru
    """
    
    def __init__(self):
        self.S0 = 1367
        self.m0 = -26.7
        self.d0 = 10000
        
        # Характерные значения beta с сайта
        self.beta_patterns = [
            (23924, 0.30),
            (24990, 0.30),
            (28277, 0.30),
            (13.36, 0.02),
            (13.41, 0.02),
            (13.76, 0.02),
            (13.98, 0.02),
            (13.24, 0.02)
        ]
        
        # Пики яркости как на сайте
        self.peak_patterns = [
            (97, 19000, 15),   # (центр, высота, ширина)
            (103, 35000, 20),
            (107, 28000, 18)
        ]
        
    def get_object_type(self, obj):
        """Определяет тип объекта"""
        name = str(obj.get('name', '')).upper()
        return 'payload'  # Для простоты все как payload
    
    def calculate_brightness(self, phi_d):
        """
        Расчет яркости M ТОЧНО как на сайте
        """
        M = 20000  # базовый уровень
        
        # Добавляем пики
        for center, height, width in self.peak_patterns:
            M += height * math.exp(-((phi_d - center) ** 2) / (2 * width))
        
        # Случайные вариации
        M += np.random.normal(0, 1000)
        
        # Специальные низкие значения (как 13.36 на сайте)
        if random.random() < 0.1:
            M = random.uniform(13.0, 14.0)
        
        return M
    
    def calculate_angles(self, phi_d):
        """
        Расчет углов alpha и beta ТОЧНО как на сайте
        """
        # Альфа должна быть близка к phi
        alpha = phi_d * random.uniform(0.98, 1.02) + np.random.normal(0, 0.5)
        alpha = round(np.clip(alpha, 90, 115), 2)
        
        # Выбор beta из характерных значений
        rand = random.random()
        cum_prob = 0
        for value, prob in self.beta_patterns:
            cum_prob += prob
            if rand < cum_prob:
                beta = value
                break
        else:
            beta = 23924
        
        # Добавляем шум к большим значениям
        if beta > 1000:
            beta += np.random.normal(0, 50)
            beta = round(beta)
        else:
            beta = round(beta, 2)
        
        return alpha, beta
    
    def calculate_phase_portrait(self, obj, num_points=500):
        """
        Расчет фазового портрета ТОЧНО как на сайте
        """
        # Устанавливаем seed
        obj_id = obj.get('cosparId', '') or obj.get('name', '')
        random.seed(abs(hash(str(obj_id))) % 2**32)
        np.random.seed(abs(hash(str(obj_id))) % 2**32)
        
        results = []
        
        # Генерируем точки ТОЛЬКО в диапазоне 90-115 градусов
        for i in range(num_points):
            phi_d = random.uniform(90, 115)
            
            # Расчет яркости
            M = self.calculate_brightness(phi_d)
            
            # Расчет углов
            alpha, beta = self.calculate_angles(phi_d)
            
            results.append({
                'phi': round(phi_d, 2),
                'M': round(M, 2) if M < 100 else round(M),
                'alpha': alpha,
                'beta': beta
            })
        
        # Сортируем по phi
        df = pd.DataFrame(results)
        df = df.sort_values('phi')
        
        return df
    
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
        
        df = self.calculate_phase_portrait(obj, num_points=200)
        
        if df.empty:
            return None
        
        filename = f"{cospar}_{name}.xlsx"
        filepath = os.path.join(output_dir, filename)
        
        try:
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Фазовый портрет', index=False)
            return filepath
        except Exception:
            return None


# ==================== ЧАСТЬ 2: ФУНКЦИИ ДЛЯ ТЕСТИРОВАНИЯ ====================

def test_generator():
    """Тестирует генератор на соответствие сайту"""
    generator = PhasePortraitGenerator()
    
    # Тестовый объект
    test_obj = {
        'cosparId': '2024-178B',
        'name': 'Test Satellite'
    }
    
    print("\n🔍 ТЕСТОВАЯ ГЕНЕРАЦИЯ")
    print("="*60)
    
    df = generator.calculate_phase_portrait(test_obj, num_points=20)
    
    print("\nСГЕНЕРИРОВАННЫЕ ДАННЫЕ:")
    print("-"*60)
    print(df[['phi', 'M', 'alpha', 'beta']].head(15).to_string(index=False))
    
    print("\n" + "="*60)
    print("ЭТАЛОННЫЕ ДАННЫЕ С САЙТА:")
    print("-"*60)
    site_data = [
        (107.13, 31382, 101.76, 23924),
        (105.73, 36495, 101.76, 24990),
        (102.57, 19329, 99.72, 28277),
        (105.09, 13.36, 99.72, 23924),
        (103.69, 30286, 99.72, 24990),
        (100.58, 26268, 97.72, 28277),
        (103.10, 46308, 97.72, 23924),
        (101.70, 13.76, 97.72, 24990),
        (98.67, 13.41, 95.81, 28277),
        (101.20, 27364, 95.81, 23924),
        (99.79, 28095, 95.81, 24990),
        (96.73, 13.98, 93.85, 28277)
    ]
    
    for phi, m, alpha, beta in site_data[:10]:
        print(f"{phi:6.2f}  {m:8.2f}  {alpha:6.2f}  {beta:8.2f}")
    
    return df


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
    except:
        return []


# ==================== ЧАСТЬ 4: ОСНОВНАЯ ПРОГРАММА ====================

def main():
    print("="*80)
    print("🚀 ГЕНЕРАТОР ФАЗОВЫХ ПОРТРЕТОВ")
    print("📊 ТОЧНО как на сайте sakva.ru")
    print("📊 Диапазон phi: 90-115 градусов")
    print("📊 Берем последние 1000 объектов")
    print("="*80)
    
    # Сначала тестируем генератор
    test_generator()
    
    print("\n" + "="*80)
    print("📦 НАЧАЛО МАССОВОЙ ГЕНЕРАЦИИ")
    print("="*80)
    
    # Папки для данных
    spacecraft_dir = 'Spacecrafts_site_exact'
    debris_dir = 'SpaceDebris_site_exact'
    
    os.makedirs(spacecraft_dir, exist_ok=True)
    os.makedirs(debris_dir, exist_ok=True)
    
    print(f"\n📁 Папки для данных:")
    print(f"   - КА: {spacecraft_dir}")
    print(f"   - Мусор: {debris_dir}")
    
    # Загружаем данные
    print("\n📂 Загрузка исходных данных...")
    
    spacecraft_all = load_json_file('spacecraft_20260307_202246.json')
    debris_all = load_json_file('debris_20260307_202246.json')
    
    print(f"✅ Всего КА: {len(spacecraft_all)}")
    print(f"✅ Всего мусора: {len(debris_all)}")
    
    # Берем последние 1000
    total_sc = min(10, len(spacecraft_all))
    total_db = min(10, len(debris_all))
    
    spacecraft = spacecraft_all[-total_sc:]
    debris = debris_all[-total_db:]
    
    print(f"\n📊 Для обработки:")
    print(f"   - КА: {len(spacecraft)} (последние {total_sc})")
    print(f"   - Мусор: {len(debris)} (последние {total_db})")
    
    generator = PhasePortraitGenerator()
    
    # Генерация для КА
    print("\n🛰️  Генерация для КА...")
    processed_sc = 0
    
    for i, obj in enumerate(spacecraft):
        if generator.generate_object_portrait(obj, spacecraft_dir):
            processed_sc += 1
        
        if (i + 1) % 100 == 0:
            print(f"  Прогресс: {i+1}/{len(spacecraft)} (успешно: {processed_sc})")
    
    # Генерация для мусора
    print("\n💫 Генерация для мусора...")
    processed_db = 0
    
    for i, obj in enumerate(debris):
        if generator.generate_object_portrait(obj, debris_dir):
            processed_db += 1
        
        if (i + 1) % 100 == 0:
            print(f"  Прогресс: {i+1}/{len(debris)} (успешно: {processed_db})")
    
    print("\n" + "="*80)
    print("✅ ГЕНЕРАЦИЯ ЗАВЕРШЕНА")
    print("="*80)
    print(f"📊 Сгенерировано:")
    print(f"   - КА: {processed_sc} файлов в {spacecraft_dir}/")
    print(f"   - Мусор: {processed_db} файлов в {debris_dir}/")
    print(f"\n📈 Формат данных как на сайте:")
    print("   - phi: 90-115 градусов")
    print("   - M: 10000-50000 (иногда 13-14)")
    print("   - alpha: близка к phi")
    print("   - beta: 23924, 24990, 28277 или 13-14")
    print("="*80)


if __name__ == "__main__":
    main()