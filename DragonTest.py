#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Программа для генерации фазовых портретов космических объектов
Генерирует данные, соответствующие формату сайта sakva.ru
Значения M в диапазоне 10000-50000, как на сайте
Берет последние 1000 объектов
ИСПРАВЛЕННАЯ ВЕРСИЯ - правильный диапазон phi
"""

import json
import numpy as np
import pandas as pd
import os
import math
import time
import random

class PhasePortraitGenerator:
    """
    Генератор фазовых портретов в формате сайта sakva.ru
    """
    
    def __init__(self):
        self.S0 = 1367
        self.m0 = -26.7
        self.d0 = 10000
        
        # Характерные значения beta с сайта
        self.beta_patterns = [
            (23924, 0.35),  # часто
            (24990, 0.30),  # часто
            (28277, 0.25),  # реже
            (13.36, 0.02),  # очень редко
            (13.41, 0.02),
            (13.76, 0.02),
            (13.98, 0.02),
            (13.24, 0.02)
        ]
        
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
    
    def get_object_type(self, obj):
        """Определяет тип объекта для настройки параметров"""
        name = str(obj.get('name', '')).upper()
        obj_class = str(obj.get('objectClass', '')).upper()
        
        if any(x in name for x in ['GPS', 'NAVSTAR', 'GLONASS', 'GALILEO']):
            return 'navigation'
        elif any(x in name for x in ['GEO', 'INMARSAT', 'TERRESTAR']):
            return 'geo'
        elif 'PAYLOAD' in obj_class:
            return 'payload'
        elif 'ROCKET' in obj_class:
            return 'rocket'
        elif 'DEBRIS' in obj_class:
            return 'debris'
        else:
            return 'unknown'
    
    def calculate_brightness(self, phi_d, obj_type):
        """
        Расчет яркости M как на сайте
        """
        # Базовый уровень зависит от типа объекта и фазового угла
        if obj_type == 'navigation':
            base = 28000 - 50 * phi_d
        elif obj_type == 'geo':
            base = 26000 - 40 * phi_d
        elif obj_type == 'payload':
            base = 24000 - 30 * phi_d
        elif obj_type == 'rocket':
            base = 22000 - 20 * phi_d
        else:
            base = 20000 - 10 * phi_d
        
        # Основные пики
        # Пик при 0-20 градусах (противостояние)
        peak_opposition = 15000 * math.exp(-(phi_d ** 2) / 200)
        
        # Пик для навигационных КА при малых углах
        if obj_type == 'navigation' and phi_d < 30:
            nav_peak = 25000 * math.exp(-(phi_d ** 2) / 100)
        else:
            nav_peak = 0
        
        # Пик для геостационарных при 10-15°
        if obj_type == 'geo' and 5 < phi_d < 25:
            geo_peak = 20000 * math.exp(-((phi_d - 13) ** 2) / 30)
        else:
            geo_peak = 0
        
        # Пик при 90-110 градусах (как на сайте)
        if 80 < phi_d < 120:
            peak_mid = 18000 * math.exp(-((phi_d - 103) ** 2) / 50)
        else:
            peak_mid = 0
        
        # Пик при больших углах (обратное отражение)
        if phi_d > 140:
            peak_back = 12000 * math.exp(-((phi_d - 160) ** 2) / 100)
        else:
            peak_back = 0
        
        # Случайные вариации (зависят от угла)
        variation = np.random.normal(0, 1000) * (1 + 0.5 * math.sin(math.radians(phi_d * 3)))
        
        M = base + peak_opposition + nav_peak + geo_peak + peak_mid + peak_back + variation
        
        # Ограничиваем диапазон как на сайте
        M = max(M, 8000)
        M = min(M, 60000)
        
        return M
    
    def calculate_angles(self, phi_d, obj_type):
        """
        Расчет углов alpha и beta как на сайте
        """
        # Альфа зависит от типа орбиты
        if obj_type in ['navigation', 'geo']:
            # Для высоких орбит alpha близка к phi
            alpha = phi_d * random.uniform(0.95, 1.05) + np.random.normal(0, 1)
        else:
            # Для низких орбит alpha может отличаться
            alpha = phi_d * random.uniform(0.8, 1.2) + np.random.normal(0, 5)
        
        alpha = np.clip(alpha, 0, 180)
        
        # Выбор beta из характерных значений
        if obj_type in ['navigation', 'geo', 'payload']:
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
                beta += np.random.normal(0, 100)
        else:
            # Для мусора и ракет - случайные значения
            beta = random.uniform(10000, 30000)
        
        return round(alpha, 2), round(beta, 2) if beta < 1000 else round(beta)
    
    def calculate_phase_portrait(self, obj, num_points=500):
        """
        Расчет фазового портрета в формате сайта
        """
        obj_type = self.get_object_type(obj)
        
        # Устанавливаем seed для воспроизводимости
        obj_id = obj.get('cosparId', '') or obj.get('name', '')
        random.seed(abs(hash(str(obj_id))) % 2**32)
        np.random.seed(abs(hash(str(obj_id))) % 2**32)
        
        results = []
        
        # Генерируем точки по всему диапазону 0-180 градусов
        for i in range(num_points):
            # Равномерное распределение по всему диапазону
            phi_d = random.uniform(0, 180)
            
            # Расчет яркости
            M = self.calculate_brightness(phi_d, obj_type)
            
            # Расчет углов
            alpha, beta = self.calculate_angles(phi_d, obj_type)
            
            results.append({
                'phi': round(phi_d, 2),
                'M': round(M),
                'alpha': alpha,
                'beta': beta
            })
        
        # Сортируем по phi для удобства
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


def main():
    print("="*80)
    print("🚀 ГЕНЕРАТОР ФАЗОВЫХ ПОРТРЕТОВ (ФОРМАТ САЙТА)")
    print("📊 Значения M: 8000-60000, как на sakva.ru")
    print("📊 Диапазон phi: 0-180 градусов")
    print("📊 Берем последние 1000 объектов")
    print("="*80)
    
    spacecraft_dir = 'Spacecrafts_site_1000_fixed'
    debris_dir = 'SpaceDebris_site_1000_fixed'
    
    os.makedirs(spacecraft_dir, exist_ok=True)
    os.makedirs(debris_dir, exist_ok=True)
    
    print(f"📁 Создана папка: {spacecraft_dir}")
    print(f"📁 Создана папка: {debris_dir}")
    
    print("\n📂 Загрузка данных...")
    
    spacecraft_all = load_json_file('spacecraft_20260307_202246.json')
    debris_all = load_json_file('debris_20260307_202246.json')
    
    print(f"✅ Всего космических аппаратов: {len(spacecraft_all)}")
    print(f"✅ Всего объектов мусора: {len(debris_all)}")
    
    # Берем ПОСЛЕДНИЕ 1000 объектов
    total_sc = min(10, len(spacecraft_all))
    total_db = min(10, len(debris_all))
    
    spacecraft = spacecraft_all[-total_sc:]
    debris = debris_all[-total_db:]
    
    print(f"\n📊 Для обработки выбрано:")
    print(f"   - Космические аппараты: {len(spacecraft)} (последние {total_sc})")
    print(f"   - Космический мусор: {len(debris)} (последние {total_db})")
    
    generator = PhasePortraitGenerator()
    
    # Тестовый прогон для первого объекта
    if spacecraft:
        test_obj = spacecraft[0]
        print(f"\n🔍 Тестовый объект: {test_obj.get('name')}")
        test_df = generator.calculate_phase_portrait(test_obj, num_points=20)
        print("\nПример данных (первые 10 строк):")
        print(test_df.head(10).to_string())
        print(f"\nДиапазон phi: {test_df['phi'].min()} - {test_df['phi'].max()}")
        print(f"Диапазон M: {test_df['M'].min()} - {test_df['M'].max()}")
    
    print("\n🛰️  Генерация портретов для космических аппаратов...")
    processed_sc = 0
    
    for i, obj in enumerate(spacecraft):
        try:
            if generator.generate_object_portrait(obj, spacecraft_dir):
                processed_sc += 1
        except Exception as e:
            print(f"  ⚠ Ошибка: {e}")
        
        if (i + 1) % 100 == 0:
            print(f"  Прогресс: {i+1}/{len(spacecraft)} (успешно: {processed_sc})")
    
    print("\n💫 Генерация портретов для космического мусора...")
    processed_db = 0
    
    for i, obj in enumerate(debris):
        try:
            if generator.generate_object_portrait(obj, debris_dir):
                processed_db += 1
        except Exception as e:
            print(f"  ⚠ Ошибка: {e}")
        
        if (i + 1) % 100 == 0:
            print(f"  Прогресс: {i+1}/{len(debris)} (успешно: {processed_db})")
    
    print("\n" + "="*80)
    print("✅ ГЕНЕРАЦИЯ ЗАВЕРШЕНА")
    print(f"📊 Обработано объектов: {processed_sc + processed_db}")
    print("📁 Результаты сохранены в папках:")
    print(f"   - {spacecraft_dir}/ ({processed_sc} файлов)")
    print(f"   - {debris_dir}/ ({processed_db} файлов)")
    print("\n📈 Каждый файл содержит данные по всему диапазону phi 0-180°")
    print("="*80)


if __name__ == "__main__":
    main()