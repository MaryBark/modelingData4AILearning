#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Программа для генерации фазовых портретов космических объектов
Генерирует НЕМОНОТОННЫЕ данные, как в реальных наблюдениях
Берет ПОСЛЕДНИЕ 1500 объектов из каждого файла
Сохраняет в формате: phi, M, alpha, beta
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
    Генератор фазовых портретов с немонотонными данными
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
    
    def diffuse_sphere_flux(self, R, phi_rad, a, d=10000):
        """Диффузно отражающая сфера"""
        d_m = d * 1000
        f_phi = ((math.pi - phi_rad) * math.cos(phi_rad) + math.sin(phi_rad)) / math.pi
        E = (2/3) * a * self.S0 * (R**2) * f_phi / (math.pi * d_m**2)
        return E
    
    def specular_sphere_flux(self, R, a, d=10000):
        """Зеркально отражающая сфера"""
        d_m = d * 1000
        E = a * self.S0 * (R**2) / (4 * d_m**2)
        return E
    
    def flux_to_magnitude(self, E):
        """Перевод потока в звездную величину"""
        if E <= 0:
            return 30.0
        m = self.m0 - 2.5 * math.log10(E / self.S0)
        return m
    
    def reduced_magnitude(self, m, d):
        """Приведение к стандартному расстоянию"""
        return m - 5 * math.log10(d / self.d0)
    
    def calculate_phase_portrait(self, obj, num_points=500):
        """
        Расчет фазового портрета с НЕМОНОТОННЫМИ данными
        """
        R = self.get_object_radius(obj)
        a_diffuse, a_specular = self.get_albedo(obj)
        name = str(obj.get('name', '')).upper()
        
        # Устанавливаем seed для воспроизводимости
        obj_id = obj.get('cosparId', '') or obj.get('name', '')
        random.seed(abs(hash(str(obj_id))) % 2**32)
        np.random.seed(abs(hash(str(obj_id))) % 2**32)
        
        results = []
        
        # Генерируем точки в случайном порядке
        for i in range(num_points):
            # Случайный фазовый угол с распределением
            r = random.random()
            if r < 0.3:
                # Больше точек в области малых углов (интересная область)
                phi_d = random.uniform(0, 30)
            elif r < 0.6:
                # Средние углы
                phi_d = random.uniform(30, 100)
            else:
                # Большие углы
                phi_d = random.uniform(100, 180)
            
            phi_r = math.radians(phi_d)
            
            # Случайное расстояние
            d = self.d0 * random.uniform(0.8, 1.2)
            
            # Диффузная компонента
            E_diffuse = self.diffuse_sphere_flux(R, phi_r, a_diffuse, d)
            
            # Зеркальная компонента
            E_specular = 0
            
            # Пик для навигационных КА
            if any(x in name for x in ['GPS', 'NAVSTAR', 'GLONASS']):
                if phi_d < 20:
                    peak_factor = math.exp(-(phi_d ** 2) / 50)
                    E_specular = self.specular_sphere_flux(R, a_specular, d) * peak_factor * 10
            
            # Пик для геостационарных
            elif any(x in name for x in ['GEO', 'INMARSAT', 'TERRESTAR']):
                if 5 < phi_d < 25:
                    peak_factor = math.exp(-((phi_d - 13) ** 2) / 30)
                    E_specular = self.specular_sphere_flux(R, a_specular, d) * peak_factor * 8
            
            # Небольшой пик для всех при малых углах
            if phi_d < 10:
                E_specular += self.specular_sphere_flux(R, a_specular * 0.2, d) * math.exp(-(phi_d ** 2) / 20)
            
            # Общий поток
            E_total = E_diffuse + E_specular
            
            # Звездная величина
            m = self.flux_to_magnitude(E_total)
            M = self.reduced_magnitude(m, d)
            
            # Добавляем шум
            noise = np.random.normal(0, 0.2)
            M_noisy = M + noise
            
            # Расчет углов alpha и beta
            if any(x in name for x in ['GPS', 'GEO']):
                alpha = phi_d * random.uniform(0.9, 1.1) + np.random.normal(0, 2)
                beta = random.uniform(0, 15) + 3 * math.sin(phi_r * 2) + np.random.normal(0, 1)
            else:
                alpha = phi_d * random.uniform(0.6, 0.8) + random.uniform(0, 20) + 10 * math.sin(phi_r * 3)
                beta = random.uniform(10, 30) + 10 * math.cos(phi_r * 2) + np.random.normal(0, 2)
            
            results.append({
                'phi': round(phi_d, 2),
                'M': round(M_noisy, 2),
                'alpha': round(np.clip(alpha, 0, 180), 2),
                'beta': round(np.clip(beta, 0, 180), 2)
            })
        
        # Перемешиваем результаты
        random.shuffle(results)
        
        return pd.DataFrame(results)
    
    def generate_object_portrait(self, obj, output_dir, obj_type):
        """Сохраняет портрет в файл"""
        # Формируем безопасное имя файла
        cospar = obj.get('cosparId', 'unknown')
        if cospar is None:
            cospar = 'unknown'
        cospar = str(cospar).replace('/', '_').replace('\\', '_').replace(':', '_')
        
        name = obj.get('name', 'unknown')
        if name is None:
            name = 'unknown'
        # Очищаем имя от недопустимых символов
        name = ''.join(c for c in str(name) if c.isalnum() or c in ' _-').rstrip()
        name = name.replace(' ', '_')[:40]
        
        # Генерируем портрет
        df = self.calculate_phase_portrait(obj, num_points=500)
        
        if df.empty:
            print(f"  ⚠ {cospar}_{name} - нет данных")
            return None
        
        # Сохраняем в Excel
        filename = f"{cospar}_{name}.xlsx"
        filepath = os.path.join(output_dir, filename)
        
        # Если файл существует, добавляем timestamp
        if os.path.exists(filepath):
            base, ext = os.path.splitext(filename)
            filename = f"{base}_{int(time.time())}{ext}"
            filepath = os.path.join(output_dir, filename)
        
        try:
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Фазовый портрет', index=False)
            
            # Статистика
            m_min = df['M'].min()
            m_max = df['M'].max()
            print(f"  ✅ {filename} - M: {m_min:.1f}-{m_max:.1f}")
            
        except Exception as e:
            print(f"  ❌ Ошибка сохранения {filename}: {e}")
        
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
    except FileNotFoundError:
        print(f"  ❌ Файл {filename} не найден")
        return []
    except Exception as e:
        print(f"  ❌ Ошибка загрузки {filename}: {e}")
        return []


def main():
    print("="*80)
    print("🚀 ГЕНЕРАТОР ФАЗОВЫХ ПОРТРЕТОВ")
    print("📊 Берутся ПОСЛЕДНИЕ 1500 объектов из каждого файла")
    print("📊 Формат: phi, M, alpha, beta (немонотонные данные)")
    print("="*80)
    
    # Создаем папки для результатов
    spacecraft_dir = 'Spacecrafts_last1500'
    debris_dir = 'SpaceDebris_last1500'
    
    os.makedirs(spacecraft_dir, exist_ok=True)
    os.makedirs(debris_dir, exist_ok=True)
    
    print(f"📁 Создана папка: {spacecraft_dir}")
    print(f"📁 Создана папка: {debris_dir}")
    
    # Загружаем данные
    print("\n📂 Загрузка данных...")
    
    spacecraft_all = load_json_file('spacecraft_20260307_202246.json')
    debris_all = load_json_file('debris_20260307_202246.json')
    
    print(f"✅ Всего космических аппаратов: {len(spacecraft_all)}")
    print(f"✅ Всего объектов мусора: {len(debris_all)}")
    
    if len(spacecraft_all) == 0 and len(debris_all) == 0:
        print("❌ Нет данных для обработки")
        return
    
    # Берем ПОСЛЕДНИЕ 1500 объектов
    total_sc = min(10, len(spacecraft_all))
    total_db = min(10, len(debris_all))
    
    spacecraft = spacecraft_all[-total_sc:]  # Последние total_sc объектов
    debris = debris_all[-total_db:]          # Последние total_db объектов
    
    print(f"\n📊 Для обработки выбрано:")
    print(f"   - Космические аппараты: {len(spacecraft)} (последние {total_sc})")
    print(f"   - Космический мусор: {len(debris)} (последние {total_db})")
    
    generator = PhasePortraitGenerator()
    
    # Обрабатываем космические аппараты
    print("\n🛰️  Генерация портретов для космических аппаратов...")
    processed_sc = 0
    
    for i, obj in enumerate(spacecraft):
        try:
            if generator.generate_object_portrait(obj, spacecraft_dir, 'SC'):
                processed_sc += 1
        except Exception as e:
            print(f"  ⚠ Ошибка обработки {obj.get('name', 'unknown')}: {e}")
        
        if (i + 1) % 100 == 0:
            print(f"  Прогресс: {i+1}/{len(spacecraft)}")
    
    # Обрабатываем космический мусор
    print("\n💫 Генерация портретов для космического мусора...")
    processed_db = 0
    
    for i, obj in enumerate(debris):
        try:
            if generator.generate_object_portrait(obj, debris_dir, 'DB'):
                processed_db += 1
        except Exception as e:
            print(f"  ⚠ Ошибка обработки {obj.get('name', 'unknown')}: {e}")
        
        if (i + 1) % 100 == 0:
            print(f"  Прогресс: {i+1}/{len(debris)}")
    
    print("\n" + "="*80)
    print("✅ ГЕНЕРАЦИЯ ЗАВЕРШЕНА")
    print(f"📊 Обработано объектов: {processed_sc + processed_db}")
    print("📁 Результаты сохранены в папках:")
    print(f"   - {spacecraft_dir}/ ({processed_sc} файлов) - ПОСЛЕДНИЕ {total_sc} КА")
    print(f"   - {debris_dir}/ ({processed_db} файлов) - ПОСЛЕДНИЕ {total_db} объектов мусора")
    print("\n📈 Каждый файл содержит 4 колонки:")
    print("   phi - фазовый угол (градусы)")
    print("   M - приведенная звездная величина")
    print("   alpha, beta - углы ориентации")
    print("="*80)


if __name__ == "__main__":
    main()