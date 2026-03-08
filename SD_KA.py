#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Программа для расчёта фазовых портретов космических объектов
Доктор физико-математических наук, специалист по фазовым портретам КА и космического мусора
"""

import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from datetime import datetime
import os
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

class PhasePortraitCalculator:
    """
    Класс для расчёта фазовых портретов космических объектов
    """
    
    # Константы
    S0 = 1367  # Плотность лучистого потока Солнца (Вт/м²)
    M_SUN = -26.7  # Звёздная величина Солнца
    DISTANCE = 1000000  # Расстояние до объекта (1000 км) для приведения
    
    def __init__(self):
        """Инициализация калькулятора"""
        self.results = []
        
    def get_characteristic_size(self, obj):
        """
        Определение характерного размера объекта
        
        Parameters:
        obj: dict - данные объекта
        
        Returns:
        float: характерный размер в метрах
        """
        shape = obj.get('shape', 'Unknown')
        
        if shape == 'Sphere' and obj.get('diameter'):
            return obj['diameter'] / 2
        elif shape in ['Cylinder', 'Cyl'] and obj.get('diameter') and obj.get('height'):
            return max(obj['diameter'] / 2, obj['height']) / 2
        elif shape in ['Box', 'Hexahedron'] and obj.get('width') and obj.get('height') and obj.get('depth'):
            return max(obj['width'], obj['height'], obj['depth']) / 2
        elif obj.get('span'):
            return obj['span'] / 2
        elif obj.get('width'):
            return obj['width'] / 2
        elif obj.get('height'):
            return obj['height'] / 2
        elif obj.get('depth'):
            return obj['depth'] / 2
        else:
            # Если нет точных данных, используем среднее значение для класса
            if obj.get('objectClass') == 'Payload':
                return 2.0  # средний размер КА
            elif obj.get('objectClass') == 'Rocket Body':
                return 3.0  # средний размер корпуса ракеты
            else:
                return 1.0  # мелкий мусор
    
    def get_albedo(self, obj):
        """
        Определение коэффициента отражения на основе класса объекта
        
        Returns:
        tuple: (albedo_diffuse, albedo_specular)
        """
        obj_class = obj.get('objectClass', 'Unknown')
        name = obj.get('name', '').upper()
        
        # Для навигационных КА (больше зеркальных поверхностей)
        if any(nav in name for nav in ['GPS', 'GLONASS', 'GALILEO', 'NAVSTAR']):
            return 0.2, 0.4
        # Для геостационарных КА
        elif any(geo in name for geo in ['INMARSAT', 'TERRESTAR', 'GEO']):
            return 0.25, 0.35
        # Для обычных КА
        elif obj_class == 'Payload':
            return 0.3, 0.2
        # Для корпусов ракет
        elif obj_class == 'Rocket Body':
            return 0.2, 0.3
        # Для мусора
        elif obj_class == 'Debris':
            return 0.15, 0.05
        else:
            return 0.2, 0.1
    
    def calculate_brightness_sphere(self, phase_angle, radius, albedo, distance=None):
        """
        Расчёт блеска диффузно отражающей сферы
        
        Parameters:
        phase_angle: фазовый угол в радианах
        radius: радиус сферы в метрах
        albedo: коэффициент диффузного отражения
        distance: расстояние до наблюдателя в метрах
        
        Returns:
        float: плотность потока E (Вт/м²)
        """
        if distance is None:
            distance = self.DISTANCE
            
        # Функция f(φ) = ((π - φ) cos φ + sin φ) / π
        f_phi = ((np.pi - phase_angle) * np.cos(phase_angle) + np.sin(phase_angle)) / np.pi
        
        # E = 2/3 * a * S0 * R² * f(φ) / d²
        E = (2/3) * albedo * self.S0 * radius**2 * f_phi / distance**2
        
        return E
    
    def calculate_brightness_specular_sphere(self, radius, albedo, distance=None):
        """
        Расчёт блеска зеркально отражающей сферы
        """
        if distance is None:
            distance = self.DISTANCE
            
        # E = a * S0 * R² / (4 * d²)
        E = albedo * self.S0 * radius**2 / (4 * distance**2)
        
        return E
    
    def flux_to_magnitude(self, E):
        """
        Перевод плотности потока в звёздную величину
        """
        if E <= 0:
            return 99.9  # объект не виден
        
        # m = m0 - 2.5 * lg(E / E0)
        m = self.M_SUN - 2.5 * np.log10(E / self.S0)
        
        return m
    
    def calculate_phase_portrait(self, obj, num_points=100):
        """
        Расчёт фазового портрета для объекта
        
        Returns:
        DataFrame с данными фазового портрета
        """
        # Получаем параметры объекта
        radius = self.get_characteristic_size(obj)
        albedo_diffuse, albedo_specular = self.get_albedo(obj)
        name = obj.get('name', 'Unknown')
        
        # Определяем тип объекта для особенностей
        name_upper = name.upper()
        is_navigation = any(nav in name_upper for nav in ['GPS', 'GLONASS', 'GALILEO', 'NAVSTAR'])
        is_geo = any(geo in name_upper for geo in ['INMARSAT', 'TERRESTAR', 'GEO'])
        
        # Генерируем фазовые углы (0-180 градусов)
        phase_angles_deg = np.linspace(0, 180, num_points)
        phase_angles_rad = np.radians(phase_angles_deg)
        
        # Рассчитываем блеск для каждого фазового угла
        magnitudes = []
        
        for phi_rad in phase_angles_rad:
            # Основной вклад от диффузного отражения (как сфера)
            E_diffuse = self.calculate_brightness_sphere(phi_rad, radius, albedo_diffuse)
            
            # Зеркальная компонента
            E_specular = 0
            
            if is_navigation and phi_rad < 0.35:  # пик при малых углах (<20°)
                # Для навигационных КА сильный зеркальный пик
                peak_factor = np.exp(-phi_rad * 15)
                E_specular = self.calculate_brightness_specular_sphere(radius, albedo_specular) * peak_factor * 3
                
            elif is_geo and 0.17 < phi_rad < 0.44:  # пик при 10-25 градусах
                # Для геостационарных КА пик смещён
                peak_phi = 0.26  # ~15 градусов
                peak_factor = np.exp(-((phi_rad - peak_phi) * 20)**2)
                E_specular = self.calculate_brightness_specular_sphere(radius, albedo_specular) * peak_factor * 2
            
            # Суммируем вклады
            E_total = E_diffuse + E_specular
            
            # Добавляем небольшой шум для реалистичности
            if len(magnitudes) > 0:
                noise = np.random.normal(0, 0.05)
            else:
                noise = 0
            
            # Переводим в звёздную величину
            m = self.flux_to_magnitude(E_total) + noise
            magnitudes.append(m)
        
        # Создаем DataFrame с результатами
        df = pd.DataFrame({
            'phase_angle_deg': phase_angles_deg,
            'magnitude': magnitudes
        })
        
        return df
    
    def generate_object_portrait(self, obj, output_dir, obj_type):
        """
        Генерация и сохранение фазового портрета для одного объекта
        """
        name = obj.get('name', 'Unknown')
        cospar = obj.get('cosparId', 'Unknown')
        
        # Очищаем имя от недопустимых символов для имени файла
        safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_name = safe_name.replace(' ', '_')
        
        try:
            # Рассчитываем фазовый портрет
            df = self.calculate_phase_portrait(obj, num_points=200)
            
            # Создаем фигуру
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
            
            # График 1: Фазовый портрет
            ax1.plot(df['phase_angle_deg'], df['magnitude'], 'b-', linewidth=2)
            
            ax1.set_xlabel('Фазовый угол (градусы)', fontsize=12)
            ax1.set_ylabel('Звёздная величина', fontsize=12)
            ax1.set_title(f'Фазовый портрет: {name}\nCOSPAR: {cospar}', fontsize=14)
            ax1.grid(True, alpha=0.3)
            ax1.invert_yaxis()
            ax1.set_xlim(0, 180)
            
            # График 2: Информация об объекте
            ax2.axis('off')
            
            # Получаем параметры для отображения
            radius = self.get_characteristic_size(obj)
            albedo_diffuse, albedo_specular = self.get_albedo(obj)
            
            info_text = f"""
            ИНФОРМАЦИЯ ОБ ОБЪЕКТЕ
            
            Название: {name}
            COSPAR ID: {cospar}
            Класс: {obj.get('objectClass', 'Unknown')}
            Форма: {obj.get('shape', 'Unknown')}
            
            Размеры (м):
            • Ширина: {obj.get('width', 0):.2f}
            • Высота: {obj.get('height', 0):.2f}
            • Глубина: {obj.get('depth', 0):.2f}
            • Диаметр: {obj.get('diameter', 0):.2f}
            
            Характерный размер: {radius:.2f} м
            
            Оптические свойства:
            • Альбедо диффузное: {albedo_diffuse:.2f}
            • Альбедо зеркальное: {albedo_specular:.2f}
            
            Статистика:
            • Мин. яркость: {df['magnitude'].min():.2f} (макс. яркость)
            • Макс. яркость: {df['magnitude'].max():.2f} (мин. яркость)
            • Средняя яркость: {df['magnitude'].mean():.2f}
            
            Дата расчёта: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """
            
            ax2.text(0.1, 0.95, info_text, transform=ax2.transAxes,
                    fontsize=10, verticalalignment='top',
                    bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
            
            # Сохраняем график
            filename = f"{output_dir}/{obj_type}_{cospar}_{safe_name}.png"
            plt.tight_layout()
            plt.savefig(filename, dpi=150, bbox_inches='tight')
            plt.close(fig)
            
            # Сохраняем данные в CSV (только для интересных объектов)
            if obj_type == 'SC' and np.random.random() < 0.1:  # Сохраняем CSV только для 10% объектов
                csv_filename = f"{output_dir}/{obj_type}_{cospar}_{safe_name}.csv"
                df.to_csv(csv_filename, index=False)
            
            return True
            
        except Exception as e:
            print(f"    Ошибка при обработке {name}: {str(e)}")
            return False
    
    def generate_summary_portraits(self, spacecrafts, debris, output_dir):
        """
        Генерация сводных фазовых портретов
        """
        print("\n📊 Генерация сводных фазовых портретов...")
        
        # Сводный график для космических аппаратов
        plt.figure(figsize=(14, 8))
        
        count = 0
        for i, obj in enumerate(spacecrafts[:100]):  # Ограничиваем до 100 для наглядности
            try:
                df = self.calculate_phase_portrait(obj, num_points=100)
                plt.plot(df['phase_angle_deg'], df['magnitude'], 
                        'b-', alpha=0.3, linewidth=0.5)
                count += 1
            except:
                continue
        
        plt.xlabel('Фазовый угол (градусы)', fontsize=14)
        plt.ylabel('Звёздная величина', fontsize=14)
        plt.title(f'Сводный фазовый портрет космических аппаратов\n({count} объектов)', fontsize=16)
        plt.grid(True, alpha=0.3)
        plt.gca().invert_yaxis()
        plt.xlim(0, 180)
        
        filename = f"{output_dir}/summary_spacecrafts.png"
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"  ✅ Сводный портрет КА сохранён: {filename}")
        
        # Сводный график для мусора
        plt.figure(figsize=(14, 8))
        
        count = 0
        for i, obj in enumerate(debris[:100]):  # Ограничиваем до 100 для наглядности
            try:
                df = self.calculate_phase_portrait(obj, num_points=100)
                plt.plot(df['phase_angle_deg'], df['magnitude'], 
                        'gray', alpha=0.3, linewidth=0.5)
                count += 1
            except:
                continue
        
        plt.xlabel('Фазовый угол (градусы)', fontsize=14)
        plt.ylabel('Звёздная величина', fontsize=14)
        plt.title(f'Сводный фазовый портрет космического мусора\n({count} объектов)', fontsize=16)
        plt.grid(True, alpha=0.3)
        plt.gca().invert_yaxis()
        plt.xlim(0, 180)
        
        filename = f"{output_dir}/summary_debris.png"
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"  ✅ Сводный портрет мусора сохранён: {filename}")
    
    def generate_3d_portrait(self, spacecrafts, debris, output_dir):
        """
        Генерация 3D-визуализации фазовых портретов
        """
        print("\n🌌 Генерация 3D-визуализации...")
        
        fig = plt.figure(figsize=(16, 10))
        ax = fig.add_subplot(111, projection='3d')
        
        # Космические аппараты (синие)
        for i, obj in enumerate(spacecrafts[:20]):  # Ограничиваем для 3D
            try:
                df = self.calculate_phase_portrait(obj, num_points=50)
                x = df['phase_angle_deg'].values
                y = np.full_like(x, i)
                z = df['magnitude'].values
                ax.plot(x, y, z, color='blue', alpha=0.5, linewidth=1)
            except:
                continue
        
        # Космический мусор (серые)
        for i, obj in enumerate(debris[:20]):  # Ограничиваем для 3D
            try:
                df = self.calculate_phase_portrait(obj, num_points=50)
                x = df['phase_angle_deg'].values
                y = np.full_like(x, i + 20)
                z = df['magnitude'].values
                ax.plot(x, y, z, color='gray', alpha=0.5, linewidth=1)
            except:
                continue
        
        ax.set_xlabel('Фазовый угол (градусы)', fontsize=12)
        ax.set_ylabel('Индекс объекта', fontsize=12)
        ax.set_zlabel('Звёздная величина', fontsize=12)
        ax.set_title('3D-визуализация фазовых портретов\n(синий - КА, серый - мусор)', fontsize=14)
        ax.invert_zaxis()
        
        filename = f"{output_dir}/phase_portrait_3d.png"
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"  ✅ 3D-визуализация сохранена: {filename}")


def load_objects_from_json(filename):
    """
    Загрузка объектов из JSON-файла
    
    Returns:
    tuple: (spacecrafts, debris) - списки объектов
    """
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Проверяем структуру JSON
        if isinstance(data, dict) and 'objects' in data:
            objects_list = data['objects']
        elif isinstance(data, list):
            objects_list = data
        else:
            print(f"Неизвестная структура JSON в файле {filename}")
            return [], []
        
        # Разделяем на космические аппараты и мусор
        spacecrafts = []
        debris = []
        
        for obj in objects_list:
            obj_class = obj.get('objectClass', 'Unknown')
            if obj_class in ['Payload', 'Rocket Body']:
                spacecrafts.append(obj)
            else:
                debris.append(obj)
        
        return spacecrafts, debris
        
    except FileNotFoundError:
        print(f"❌ Файл {filename} не найден")
        return [], []
    except json.JSONDecodeError:
        print(f"❌ Ошибка декодирования JSON в файле {filename}")
        return [], []


def main():
    """
    Основная функция программы
    """
    print("="*70)
    print("🚀 ПРОГРАММА РАСЧЁТА ФАЗОВЫХ ПОРТРЕТОВ КОСМИЧЕСКИХ ОБЪЕКТОВ")
    print("👨‍🔬 Доктор физико-математических наук, специалист по фазовым портретам")
    print("="*70)
    
    # Создаем директории для результатов
    output_dirs = {
        'spacecraft': 'Spacecrafts',
        'debris': 'SpaceDebris',
        'summary': 'Summary'
    }
    
    for dir_name in output_dirs.values():
        Path(dir_name).mkdir(exist_ok=True)
        print(f"📁 Создана папка: {dir_name}")
    
    # Загружаем данные
    filename = 'debris_20260307_202246.json'
    print(f"\n📂 Загрузка данных из {filename}...")
    
    spacecrafts, debris = load_objects_from_json(filename)
    
    if not spacecrafts and not debris:
        print("❌ Нет данных для анализа. Завершение работы.")
        return
    
    print(f"✅ Загружено космических аппаратов: {len(spacecrafts)}")
    print(f"✅ Загружено объектов мусора: {len(debris)}")
    
    # Создаем калькулятор
    calculator = PhasePortraitCalculator()
    
    # Генерируем портреты для космических аппаратов (первые 100)
    if spacecrafts:
        print(f"\n🛰️  Генерация фазовых портретов для космических аппаратов...")
        max_sc = min(100, len(spacecrafts))  # Уменьшаем количество для теста
        for i in range(max_sc):
            obj = spacecrafts[i]
            if i % 10 == 0:
                print(f"  Прогресс: {i}/{max_sc}")
            
            calculator.generate_object_portrait(obj, output_dirs['spacecraft'], 'SC')
    
    # Генерируем портреты для мусора (первые 50)
    if debris:
        print(f"\n💫 Генерация фазовых портретов для космического мусора...")
        max_db = min(50, len(debris))  # Уменьшаем количество для теста
        for i in range(max_db):
            obj = debris[i]
            if i % 10 == 0:
                print(f"  Прогресс: {i}/{max_db}")
            
            calculator.generate_object_portrait(obj, output_dirs['debris'], 'DEBRIS')
    
    # Генерируем сводные портреты
    calculator.generate_summary_portraits(spacecrafts[:100], debris[:50], output_dirs['summary'])
    
    # Генерируем 3D-визуализацию
    calculator.generate_3d_portrait(spacecrafts[:20], debris[:20], output_dirs['summary'])
    
    print("\n" + "="*70)
    print("✅ РАБОТА ПРОГРАММЫ ЗАВЕРШЕНА УСПЕШНО")
    print("📊 Результаты сохранены в папках:")
    print(f"   🛰️  Космические аппараты: {output_dirs['spacecraft']}")
    print(f"   💫 Космический мусор: {output_dirs['debris']}")
    print(f"   📈 Сводные графики: {output_dirs['summary']}")
    print("="*70)


if __name__ == "__main__":
    main()