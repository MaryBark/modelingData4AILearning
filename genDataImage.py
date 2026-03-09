#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ПОЛНЫЙ КОМПЛЕКС ДЛЯ ФАЗОВЫХ ПОРТРЕТОВ
Исправленная версия с корректными фотометрическими моделями
Основано на инструкции из Portrets_copy.pdf
"""

import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import os
import math
import random
import glob

# ==================== КОНСТАНТЫ ИЗ ИНСТРУКЦИИ ====================

S0 = 1367  # Вт/м² - плотность потока солнечного излучения
m_sun = -26.7  # звездная величина Солнца
d0 = 10000  # расстояние приведения (км)

class PhasePortraitGenerator:
    """
    Генератор фазовых портретов на основе моделей из инструкции
    """
    
    def __init__(self):
        self.S0 = S0
        self.m_sun = m_sun
        self.d0 = d0
        
    def flux_to_magnitude(self, E, d):
        """
        Перевод плотности потока в звездную величину
        m = m_sun - 2.5 * lg(E/E0), где E0 = S0
        """
        if E <= 0:
            return 30.0  # очень слабый объект
        
        m = self.m_sun - 2.5 * math.log10(E / self.S0)
        return m
    
    def magnitude_to_flux(self, m, d):
        """
        Обратный перевод: из звездной величины в плотность потока
        """
        E = self.S0 * 10 ** ((self.m_sun - m) / 2.5)
        return E
    
    def diffuse_sphere(self, R, a, phi_deg, d):
        """
        Диффузно отражающая сфера
        E = 2/3 * a * S0 * R^2 * ((π-φ)cos φ + sin φ)/(π d^2)
        """
        phi = math.radians(phi_deg)
        
        # Функция f(φ) = ((π-φ)cos φ + sin φ)/π
        f_phi = ((math.pi - phi) * math.cos(phi) + math.sin(phi)) / math.pi
        
        E = (2.0/3.0) * a * self.S0 * R**2 * f_phi / d**2
        return E
    
    def specular_sphere(self, R, a, d):
        """
        Зеркально отражающая сфера
        E = a * S0 * R^2 / (4 * d^2)
        Не зависит от фазового угла (в малом угле)
        """
        E = a * self.S0 * R**2 / (4 * d**2)
        return E
    
    def diffuse_cylinder(self, R, h, a, alpha_deg, beta_deg, epsilon_deg, d):
        """
        Диффузно отражающий цилиндр
        E = 0.5 * a * S0 * R * h * ((π-ε)cos ε + sin ε)/π * sin α * sin β / d^2
        """
        alpha = math.radians(alpha_deg)
        beta = math.radians(beta_deg)
        epsilon = math.radians(epsilon_deg)
        
        f_epsilon = ((math.pi - epsilon) * math.cos(epsilon) + math.sin(epsilon)) / math.pi
        
        E = (0.5 * a * self.S0 * R * h * f_epsilon * 
             math.sin(alpha) * math.sin(beta) / d**2)
        return E
    
    def specular_cylinder(self, R, h, a, epsilon_deg, d):
        """
        Зеркально отражающий цилиндр
        E = a * S0 * R * h * cos(ε/2) / d^2
        """
        epsilon = math.radians(epsilon_deg)
        
        E = a * self.S0 * R * h * math.cos(epsilon/2) / d**2
        return E
    
    def diffuse_plane(self, F, a, alpha_deg, beta_deg, d):
        """
        Диффузно отражающая плоскость
        E = a * S0 * F * cos α * cos β / (π d^2)
        (α < 90°, β < 90°)
        """
        alpha = math.radians(alpha_deg)
        beta = math.radians(beta_deg)
        
        if alpha >= math.pi/2 or beta >= math.pi/2:
            return 0
        
        E = a * self.S0 * F * math.cos(alpha) * math.cos(beta) / (math.pi * d**2)
        return E
    
    def specular_plane_phong(self, F, a, alpha_deg, gamma_deg, k, d):
        """
        Зеркально отражающая плоскость (модель Фонга)
        E = a * S0 * F * cos α * cos^k γ * (k+1) / (2π d^2)
        (α < 90°, γ < 90°)
        """
        alpha = math.radians(alpha_deg)
        gamma = math.radians(gamma_deg)
        
        if alpha >= math.pi/2 or gamma >= math.pi/2:
            return 0
        
        E = (a * self.S0 * F * math.cos(alpha) * 
             (math.cos(gamma) ** k) * (k + 1) / (2 * math.pi * d**2))
        return E
    
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
    
    def calculate_phase_portrait(self, obj, num_points=500):
        """
        Расчет фазового портрета с использованием моделей из инструкции
        """
        R = self.get_object_radius(obj)
        name = str(obj.get('name', '')).upper()
        obj_class = str(obj.get('objectClass', '')).upper()
        
        # Устанавливаем seed для воспроизводимости
        obj_id = obj.get('cosparId', '') or obj.get('name', '')
        random.seed(abs(hash(str(obj_id))) % 2**32)
        np.random.seed(abs(hash(str(obj_id))) % 2**32)
        
        results = []
        
        # Типовые параметры для разных классов объектов
        if any(x in name for x in ['GPS', 'NAVSTAR', 'GLONASS']):
            # Навигационные КА - есть зеркальный пик при малых фазовых углах
            obj_type = 'navigation'
        elif any(x in name for x in ['GEO', 'INMARSAT', 'TERRESTAR']):
            # Геостационарные КА - пик при 10-15 градусах
            obj_type = 'geostationary'
        elif 'DEBRIS' in obj_class or 'DB' in name:
            # Космический мусор - в основном диффузное отражение
            obj_type = 'debris'
        else:
            # Другие КА - смешанный тип
            obj_type = 'other'
        
        # Расстояние до наблюдателя (случайное в разумных пределах)
        d = random.uniform(500, 40000)  # км
        
        for i in range(num_points):
            # Генерируем фазовый угол
            if obj_type == 'navigation':
                # Больше точек при малых углах для пика
                if random.random() < 0.4:
                    phi_d = random.uniform(0, 30)
                else:
                    phi_d = random.uniform(30, 180)
            elif obj_type == 'geostationary':
                # Больше точек в области пика 10-15°
                if random.random() < 0.4:
                    phi_d = random.uniform(5, 25)
                else:
                    phi_d = random.uniform(25, 180)
            else:
                phi_d = random.uniform(0, 180)
            
            # Генерируем углы для сложных моделей
            alpha_d = random.uniform(0, 90)  # угол к Солнцу
            beta_d = random.uniform(0, 90)   # угол к наблюдателю
            
            # Угол между плоскостями (для цилиндров)
            epsilon_d = abs(phi_d - random.uniform(0, 30))
            if epsilon_d > 180:
                epsilon_d = 360 - epsilon_d
            
            # Угол отклонения от зеркального отражения (для модели Фонга)
            gamma_d = random.uniform(0, 45)
            
            # Коэффициенты отражения
            a_diffuse = random.uniform(0.1, 0.4)
            a_specular = random.uniform(0.05, 0.3)
            
            # Параметр Фонга (чем больше, тем уже пик)
            k_phong = random.uniform(10, 50)
            
            # Расчет суммарного потока от разных элементов
            E_total = 0
            
            # 1. Диффузная сфера (корпус)
            E_total += self.diffuse_sphere(R, a_diffuse, phi_d, d) * random.uniform(0.5, 1.5)
            
            # 2. Солнечные батареи (моделируем как плоскости или цилиндры)
            if obj_type == 'navigation':
                # У навигационных КА батареи всегда на Солнце
                F_solar = math.pi * R**2 * random.uniform(2, 5)  # площадь батарей
                E_total += self.diffuse_plane(F_solar, a_diffuse, alpha_d, beta_d, d) * 0.5
                
                # Зеркальный пик при малых фазовых углах
                if phi_d < 20:
                    # Зеркальное отражение от батарей
                    E_total += self.specular_plane_phong(F_solar, a_specular, 
                                                         alpha_d, phi_d, k_phong, d) * 5
                    
            elif obj_type == 'geostationary':
                F_solar = math.pi * R**2 * random.uniform(3, 6)
                E_total += self.diffuse_plane(F_solar, a_diffuse, alpha_d, beta_d, d) * 0.5
                
                # Пик при 10-15 градусах
                if 5 < phi_d < 25:
                    # Смещенный зеркальный пик
                    effective_gamma = abs(phi_d - 13)  # отклонение от 13°
                    E_total += self.specular_plane_phong(F_solar, a_specular,
                                                         alpha_d, effective_gamma, k_phong, d) * 8
            
            elif obj_type == 'debris':
                # Мусор - в основном диффузное отражение
                E_total += self.diffuse_sphere(R, a_diffuse * 0.7, phi_d, d)
                
                # Иногда добавляем зеркальные элементы
                if random.random() < 0.1:
                    F_debris = math.pi * R**2 * 0.5
                    E_total += self.specular_plane_phong(F_debris, a_specular * 0.3,
                                                         alpha_d, gamma_d, k_phong/2, d)
            else:
                # Смешанный тип
                F_solar = math.pi * R**2 * random.uniform(1, 3)
                E_total += self.diffuse_plane(F_solar, a_diffuse, alpha_d, beta_d, d)
                
                # Небольшой зеркальный пик
                if phi_d < 15:
                    E_total += self.specular_plane_phong(F_solar, a_specular * 0.3,
                                                         alpha_d, phi_d, k_phong/3, d)
            
            # Добавляем цилиндрические элементы (антенны, корпуса)
            if random.random() < 0.3:
                h_cyl = R * random.uniform(1, 3)
                if random.random() < 0.5:
                    E_total += self.diffuse_cylinder(R*0.3, h_cyl, a_diffuse,
                                                     alpha_d, beta_d, epsilon_d, d)
                else:
                    E_total += self.specular_cylinder(R*0.3, h_cyl, a_specular,
                                                      epsilon_d, d)
            
            # Добавляем шум измерений
            noise_percent = random.uniform(5, 15)  # 5-15% шума
            E_total *= (1 + random.gauss(0, noise_percent/100))
            
            # Переводим в звездную величину
            M = self.flux_to_magnitude(E_total, d)
            
            # Приводим к стандартному расстоянию d0
            # M_obs = m - 5 * lg(d/d0)
            # где m - наблюдаемая величина, M_obs - приведенная
            m_obs = M  # здесь M уже включает зависимость от d
            M_reduced = m_obs - 5 * math.log10(d / self.d0)
            
            # Ограничиваем разумными пределами
            M_reduced = max(5, min(18, M_reduced))
            
            results.append({
                'phi': round(phi_d, 2),
                'M': round(M_reduced, 2),
                'alpha': round(alpha_d, 2),
                'beta': round(beta_d, 2),
                'epsilon': round(epsilon_d, 2)
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
            filename = f"{base}_{random.randint(1000, 9999)}{ext}"
            filepath = os.path.join(output_dir, filename)
        
        try:
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Фазовый портрет', index=False)
            
            return filepath
        except Exception as e:
            print(f"Ошибка сохранения: {e}")
            return None


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
    plt.ylabel('M (приведенная звездная величина)', fontsize=14)
    plt.title(f'Фазовый портрет: {name_without_ext}', fontsize=16)
    plt.grid(True, alpha=0.3, linestyle='--')
    
    # Инвертируем ось Y (чем меньше величина, тем ярче)
    plt.gca().invert_yaxis()
    
    # Устанавливаем пределы для звездных величин
    plt.xlim(0, 180)
    plt.ylim(5, 18)  # Типичный диапазон для приведенных величин
    
    # Добавляем горизонтальные линии
    for y in range(6, 19, 2):
        plt.axhline(y=y, color='gray', linestyle='-', alpha=0.1)
    
    # Добавляем вертикальные линии
    for x in range(0, 181, 30):
        plt.axvline(x=x, color='gray', linestyle='-', alpha=0.1)
    
    plt.legend(loc='upper right')
    
    # Сохраняем
    output_file = os.path.join(output_dir, f'{name_without_ext}_portrait.png')
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"    ✅ График: {os.path.basename(output_file)}")
    
    return output_file


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


def main():
    print("="*80)
    print("🚀 ФОТОМЕТРИЧЕСКИЙ КОМПЛЕКС (по инструкции Portrets_copy.pdf)")
    print("📊 Модели: диффузная/зеркальная сфера, цилиндр, плоскость, модель Фонга")
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
    
    # Генерация данных
    print("\n" + "="*80)
    print("🛠️  ГЕНЕРАЦИЯ ДАННЫХ")
    print("="*80)
    
    # Генерация для КА (первые 5 для теста)
    print("\n🛰️  Генерация для КА...")
    for i, obj in enumerate(spacecraft[:5]):
        if generator.generate_object_portrait(obj, data_dir_sc):
            print(f"  {i+1}. {obj.get('name', 'Unknown')}")
    
    # Генерация для мусора (первые 5 для теста)
    print("\n💫 Генерация для мусора...")
    for i, obj in enumerate(debris[:5]):
        if generator.generate_object_portrait(obj, data_dir_db):
            print(f"  {i+1}. {obj.get('name', 'Unknown')}")
    
    # Построение графиков
    print("\n" + "="*80)
    print("📈 ПОСТРОЕНИЕ ГРАФИКОВ")
    print("="*80)
    
    # Индивидуальные графики
    print("\n🖼️  Индивидуальные графики:")
    
    sc_files = glob.glob(os.path.join(data_dir_sc, '*.xlsx'))[:5]
    for filename in sc_files:
        plot_phase_portrait_from_file(filename, os.path.join(plots_dir, 'individual'))
    
    db_files = glob.glob(os.path.join(data_dir_db, '*.xlsx'))[:5]
    for filename in db_files:
        plot_phase_portrait_from_file(filename, os.path.join(plots_dir, 'individual'))
    
    print("\n" + "="*80)
    print("✅ ГЕНЕРАЦИЯ ЗАВЕРШЕНА")
    print(f"📁 Данные сохранены в {data_dir_sc}/ и {data_dir_db}/")
    print(f"📁 Графики сохранены в {plots_dir}/")
    print("="*80)


if __name__ == "__main__":
    main()