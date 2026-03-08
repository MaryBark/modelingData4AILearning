import json
import numpy as np
import pandas as pd
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import math

class PhasePortraitCalculator:
    """
    Калькулятор фазовых портретов космических объектов на основе фотометрических моделей
    """
    
    def __init__(self):
        # Константы из документа
        self.S0 = 1367  # плотность лучистого потока Солнца (Вт/м²)
        self.m0 = -26.7  # звездная величина Солнца
        
        # Параметры из изображения
        self.orientation_modes = ['инерциальная', 'на Землю', 'по скорости', 'на Солнце', 'хаотичная']
        self.rotation_speed = 10  # об/мин
        
        # Параметры по умолчанию
        self.default_params = {
            'date': '2024-03-21',
            'time': '00:00:00',
            'M_error': 0.5,
            'num_points': 500,
            'time_scale': 10000,
            'orbit_type': 'навигация',
            'eccentricity': 0.001,
            'inclination': 55,
            'raan': 0,
            'perigee': 0,
            'anomaly': 0
        }
        
    def get_object_dimensions(self, obj: Dict) -> Dict:
        """
        Извлекает размеры объекта на основе его формы
        """
        shape = obj.get('shape', '').upper()
        dimensions = {
            'type': shape,
            'radius': None,
            'height': None,
            'length': None,
            'width': None,
            'depth': None,
            'area': None
        }
        
        if shape == 'SPHERE' or 'SPHERE' in shape:
            dimensions['type'] = 'sphere'
            dimensions['radius'] = obj.get('diameter', 0.58) / 2 if obj.get('diameter') else obj.get('width', 0.58) / 2
            dimensions['area'] = 4 * np.pi * (dimensions['radius'] ** 2)
            
        elif shape == 'CYL' or 'CYLINDER' in shape:
            dimensions['type'] = 'cylinder'
            dimensions['radius'] = obj.get('diameter', 0.4) / 2 if obj.get('diameter') else 0.2
            dimensions['height'] = obj.get('height', 3) or 3
            # Площадь боковой поверхности + торцы
            dimensions['area'] = 2 * np.pi * dimensions['radius'] * dimensions['height'] + \
                                2 * np.pi * (dimensions['radius'] ** 2)
            
        elif shape == 'BOX' or 'RECTANGLE' in shape or shape == 'PAYLOAD':
            dimensions['type'] = 'box'
            dimensions['length'] = obj.get('width', 1) or 1
            dimensions['height'] = obj.get('height', 1) or 1
            dimensions['width'] = obj.get('depth', 1) or 1
            # Площадь поверхности параллелепипеда
            dimensions['area'] = 2 * (dimensions['length'] * dimensions['height'] + \
                                      dimensions['length'] * dimensions['width'] + \
                                      dimensions['height'] * dimensions['width'])
            
        else:  # По умолчанию - сфера по среднему сечению
            dimensions['type'] = 'sphere'
            dimensions['radius'] = math.sqrt(obj.get('xSectAvg', 0.2642) / np.pi)
            dimensions['area'] = obj.get('xSectAvg', 0.2642) * 4
            
        return dimensions
    
    def diffuse_sphere_flux(self, R: float, phi: float, a: float = 0.2, d: float = 1000) -> float:
        """
        Диффузно отражающая сфера
        E = 2/3 * a * S0 * R^2 * ((π - φ)cos φ + sin φ) / (π * d^2)
        """
        if phi < 0 or phi > np.pi:
            return 0
            
        f_phi = ((np.pi - phi) * np.cos(phi) + np.sin(phi)) / np.pi
        E = (2/3) * a * self.S0 * (R ** 2) * f_phi / (np.pi * (d ** 2))
        return E
    
    def specular_sphere_flux(self, R: float, a: float = 0.8, d: float = 1000) -> float:
        """
        Зеркально отражающая сфера
        E = a * S0 * R^2 / (4 * d^2)
        """
        E = a * self.S0 * (R ** 2) / (4 * (d ** 2))
        return E
    
    def diffuse_cylinder_flux(self, R: float, h: float, alpha: float, beta: float, 
                               epsilon: float, a: float = 0.2, d: float = 1000) -> float:
        """
        Диффузно отражающий цилиндр
        E = 0.5 * a * S0 * R * h * (((π - ε)cos ε + sin ε)/π) * sin α * sin β / d^2
        """
        if alpha < 0 or alpha > np.pi or beta < 0 or beta > np.pi:
            return 0
            
        f_epsilon = ((np.pi - epsilon) * np.cos(epsilon) + np.sin(epsilon)) / np.pi
        E = 0.5 * a * self.S0 * R * h * f_epsilon * np.sin(alpha) * np.sin(beta) / (d ** 2)
        return E
    
    def specular_cylinder_flux(self, R: float, h: float, epsilon: float, 
                                 a: float = 0.8, d: float = 1000) -> float:
        """
        Зеркально отражающий цилиндр
        E = a * S0 * R * h * cos(ε/2) / d^2
        """
        E = a * self.S0 * R * h * np.cos(epsilon / 2) / (d ** 2)
        return E
    
    def diffuse_plane_flux(self, F: float, alpha: float, beta: float, 
                            a: float = 0.2, d: float = 1000) -> float:
        """
        Диффузно отражающая плоскость
        E = a * S0 * F * cos α * cos β / (π * d^2)  (α < π/2, β < π/2)
        """
        if alpha >= np.pi/2 or beta >= np.pi/2:
            return 0
            
        E = a * self.S0 * F * np.cos(alpha) * np.cos(beta) / (np.pi * (d ** 2))
        return E
    
    def specular_plane_flux(self, F: float, alpha: float, gamma: float, 
                             k: float = 1, a: float = 0.8, d: float = 1000) -> float:
        """
        Зеркально отражающая плоскость (модель Фонга)
        E = a * S0 * F * cos α * cos^k γ * (k+1) / (2π * d^2)  (α < π/2, γ < π/2)
        """
        if alpha >= np.pi/2 or gamma >= np.pi/2:
            return 0
            
        E = a * self.S0 * F * np.cos(alpha) * (np.cos(gamma) ** k) * (k + 1) / (2 * np.pi * (d ** 2))
        return E
    
    def flux_to_magnitude(self, E: float) -> float:
        """
        Перевод плотности потока в звездную величину
        m = m0 - 2.5 * lg(E / S0)
        """
        if E <= 0:
            return 30  # очень слабый объект
        
        m = self.m0 - 2.5 * np.log10(E / self.S0)
        return m
    
    def reduced_magnitude(self, m: float, d: float, d0: float = 1000) -> float:
        """
        Приведение блеска к стандартному расстоянию
        M = m - 5 * lg(d / d0)
        """
        return m - 5 * np.log10(d / d0)
    
    def calculate_phase_angles(self, num_points: int = 100) -> np.ndarray:
        """
        Генерирует массив фазовых углов от 0 до 180 градусов
        """
        return np.linspace(0, np.pi, num_points)
    
    def calculate_orientation_angles(self, obj: Dict, phase_angles: np.ndarray, 
                                      orientation_mode: str = 'на Солнце') -> Tuple:
        """
        Рассчитывает углы ориентации для разных режимов
        """
        if orientation_mode == 'на Солнце':
            # Панели СБ всегда на Солнце
            alpha = np.abs(phase_angles)  # угол между осью и Солнцем
            beta = np.abs(phase_angles * 0.8)  # угол между осью и наблюдателем
            epsilon = np.abs(phase_angles * 0.5)  # угол между плоскостями
            
        elif orientation_mode == 'на Землю':
            alpha = np.abs(np.pi/2 - phase_angles)
            beta = np.abs(np.pi/2 - phase_angles * 0.7)
            epsilon = np.abs(phase_angles * 0.3)
            
        elif orientation_mode == 'по скорости':
            alpha = np.abs(phase_angles * 0.6)
            beta = np.abs(phase_angles * 0.6)
            epsilon = np.abs(phase_angles * 0.4)
            
        elif orientation_mode == 'инерциальная':
            alpha = np.abs(phase_angles * 0.3 + 0.2)
            beta = np.abs(phase_angles * 0.4 + 0.1)
            epsilon = np.abs(phase_angles * 0.2)
            
        else:  # хаотичная
            np.random.seed(hash(obj.get('cosparId')) % 2**32)
            alpha = np.abs(phase_angles + np.random.normal(0, 0.3, len(phase_angles)))
            beta = np.abs(phase_angles + np.random.normal(0, 0.3, len(phase_angles)))
            epsilon = np.abs(phase_angles + np.random.normal(0, 0.2, len(phase_angles)))
        
        return alpha, beta, epsilon
    
    def calculate_phase_portrait(self, obj: Dict, num_points: int = 100) -> pd.DataFrame:
        """
        Рассчитывает полный фазовый портрет для объекта
        """
        # Получаем размеры объекта
        dims = self.get_object_dimensions(obj)
        
        # Массив фазовых углов (в радианах)
        phi = self.calculate_phase_angles(num_points)
        
        # Расстояние до наблюдателя (км)
        d = 1000 + np.random.normal(0, 100)  # вариации расстояния
        
        # Коэффициент отражения (зависит от класса объекта)
        if 'Payload' in obj.get('objectClass', ''):
            a_diffuse = 0.3  # для рабочих аппаратов
            a_specular = 0.7
            reflection_type = 'mixed'
        else:
            a_diffuse = 0.2  # для мусора
            a_specular = 0.4
            reflection_type = 'diffuse'
        
        results = []
        
        for i, phase in enumerate(phi):
            phase_deg = np.degrees(phase)
            
            # Рассчитываем углы ориентации для данного фазового угла
            alpha, beta, epsilon = self.calculate_orientation_angles(obj, phase, 'на Солнце')
            
            # Расчет потока в зависимости от формы объекта
            if dims['type'] == 'sphere':
                # Сферический объект
                if reflection_type == 'specular' or (reflection_type == 'mixed' and phase_deg < 30):
                    # Зеркальная компонента
                    E_spec = self.specular_sphere_flux(dims['radius'], a_specular, d)
                    E = E_spec
                else:
                    # Диффузная компонента
                    E_diff = self.diffuse_sphere_flux(dims['radius'], phase, a_diffuse, d)
                    E = E_diff
                    
            elif dims['type'] == 'cylinder':
                # Цилиндрический объект
                if reflection_type == 'specular':
                    E = self.specular_cylinder_flux(dims['radius'], dims['height'], 
                                                     epsilon[i], a_specular, d)
                else:
                    E = self.diffuse_cylinder_flux(dims['radius'], dims['height'],
                                                    alpha[i], beta[i], epsilon[i], 
                                                    a_diffuse, d)
                    
            elif dims['type'] == 'box':
                # Корпус (параллелепипед) + панели СБ
                # Площадь одной грани
                face_area = dims['length'] * dims['height']
                
                if reflection_type == 'specular':
                    # Зеркальное отражение от корпуса
                    E_body = self.specular_plane_flux(face_area, alpha[i], epsilon[i], 
                                                       k=2, a=a_specular, d=d)
                else:
                    # Диффузное отражение от корпуса
                    E_body = self.diffuse_plane_flux(face_area, alpha[i], beta[i], 
                                                      a_diffuse, d)
                
                # Добавляем панели солнечных батарей
                panel_area = 5.0  # площадь панелей (из изображения)
                # Зеркальный блик от панелей при малых фазовых углах
                if phase_deg < 30:
                    E_panels = self.specular_plane_flux(panel_area, phase * 0.5, 
                                                         phase * 0.3, k=5, a=0.9, d=d)
                else:
                    E_panels = self.diffuse_plane_flux(panel_area, alpha[i], beta[i], 
                                                        0.1, d)
                
                E = E_body + E_panels
                
            else:
                # По умолчанию - сфера по сечению
                R_equiv = math.sqrt(dims.get('area', 1) / (4 * np.pi))
                E = self.diffuse_sphere_flux(R_equiv, phase, a_diffuse, d)
            
            # Перевод в звездную величину
            magnitude = self.flux_to_magnitude(E)
            
            # Приведение к стандартному расстоянию
            reduced_mag = self.reduced_magnitude(magnitude, d)
            
            # Добавляем небольшую погрешность
            error = np.random.normal(0, 0.5)
            
            results.append({
                'phi_deg': round(phase_deg, 2),
                'phi_rad': round(phase, 4),
                'magnitude': round(magnitude + error, 3),
                'reduced_magnitude': round(reduced_mag + error, 3),
                'alpha_deg': round(np.degrees(alpha[i]), 2),
                'beta_deg': round(np.degrees(beta[i]), 2),
                'epsilon_deg': round(np.degrees(epsilon[i]), 2),
                'distance_km': round(d, 0),
                'flux_W_m2': round(E, 8)
            })
        
        return pd.DataFrame(results)
    
    def generate_object_portrait(self, obj: Dict, output_dir: str, obj_type: str):
        """
        Генерирует фазовый портрет для одного объекта и сохраняет в файл
        """
        # Создаем имя файла на основе COSPAR ID и названия
        cospar = obj.get('cosparId', 'unknown').replace('/', '_').replace('\\', '_')
        name = obj.get('name', 'unknown').replace(' ', '_').replace('/', '_')
        filename = f"{cospar}_{name}.xlsx"
        
        # Полный путь к файлу
        filepath = os.path.join(output_dir, filename)
        
        # Рассчитываем фазовый портрет
        df = self.calculate_phase_portrait(obj, num_points=200)
        
        # Добавляем информацию об объекте
        obj_info = pd.DataFrame([{
            'Параметр': 'COSPAR ID',
            'Значение': obj.get('cosparId', 'N/A')
        }, {
            'Параметр': 'Название',
            'Значение': obj.get('name', 'N/A')
        }, {
            'Параметр': 'Тип объекта',
            'Значение': obj.get('objectClass', 'N/A')
        }, {
            'Параметр': 'Форма',
            'Значение': obj.get('shape', 'N/A')
        }, {
            'Параметр': 'Масса (кг)',
            'Значение': obj.get('mass', 'N/A')
        }, {
            'Параметр': 'Сечение (м²)',
            'Значение': round(obj.get('xSectAvg', 0), 3)
        }])
        
        # Сохраняем в Excel с несколькими листами
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            obj_info.to_excel(writer, sheet_name='Информация', index=False)
            df.to_excel(writer, sheet_name='Фазовый портрет', index=False)
        
        print(f"  ✅ {filename} - {len(df)} точек, магнитуда: {df['magnitude'].min():.1f}-{df['magnitude'].max():.1f}")
        
        return filepath

def main():
    """
    Основная функция
    """
    print("="*70)
    print("🚀 ГЕНЕРАЦИЯ ФАЗОВЫХ ПОРТРЕТОВ КОСМИЧЕСКИХ ОБЪЕКТОВ")
    print("="*70)
    
    # Пути к файлам
    spacecraft_file = 'spacecraft_20260307_202246.json'
    debris_file = 'debris_20260307_202246.json'
    
    # Проверяем наличие файлов
    if not os.path.exists(spacecraft_file):
        print(f"❌ Файл не найден: {spacecraft_file}")
        return
    if not os.path.exists(debris_file):
        print(f"❌ Файл не найден: {debris_file}")
        return
    
    # Создаем папки для результатов
    output_dirs = {
        'spacecraft': 'Spacecrafts',
        'debris': 'SpaceDebris'
    }
    
    for dir_name in output_dirs.values():
        os.makedirs(dir_name, exist_ok=True)
        print(f"📁 Создана папка: {dir_name}")
    
    # Загружаем данные
    print("\n📂 Загрузка данных...")
    with open(spacecraft_file, 'r', encoding='utf-8') as f:
        spacecraft = json.load(f)
    with open(debris_file, 'r', encoding='utf-8') as f:
        debris = json.load(f)
    
    print(f"✅ Загружено космических аппаратов: {len(spacecraft)}")
    print(f"✅ Загружено объектов мусора: {len(debris)}")
    
    # Создаем калькулятор
    calculator = PhasePortraitCalculator()
    
    # Обрабатываем космические аппараты
    print("\n🛰️  Генерация фазовых портретов для космических аппаратов...")
    spacecraft_files = []
    for i, obj in enumerate(spacecraft):
        if i < 10 or (i + 1) % 10 == 0:  # Показываем прогресс
            print(f"\n  Объект {i+1}/{len(spacecraft)}: {obj.get('name', 'Unknown')}")
        filepath = calculator.generate_object_portrait(obj, output_dirs['spacecraft'], 'spacecraft')
        spacecraft_files.append(filepath)
    
    # Обрабатываем космический мусор
    print("\n💥 Генерация фазовых портретов для космического мусора...")
    debris_files = []
    for i, obj in enumerate(debris):
        if i < 10 or (i + 1) % 10 == 0:
            print(f"\n  Объект {i+1}/{len(debris)}: {obj.get('name', 'Unknown')}")
        filepath = calculator.generate_object_portrait(obj, output_dirs['debris'], 'debris')
        debris_files.append(filepath)
    
    # Создаем сводный отчет
    print("\n📊 Создание сводного отчета...")
    
    summary_data = []
    for obj in spacecraft[:20]:  # Первые 20 КА
        summary_data.append({
            'Тип': 'КА',
            'COSPAR': obj.get('cosparId', 'N/A'),
            'Название': obj.get('name', 'N/A'),
            'Масса (кг)': obj.get('mass', 0),
            'Сечение (м²)': round(obj.get('xSectAvg', 0), 3),
            'Форма': obj.get('shape', 'N/A')
        })
    
    for obj in debris[:20]:  # Первые 20 объектов мусора
        summary_data.append({
            'Тип': 'Мусор',
            'COSPAR': obj.get('cosparId', 'N/A'),
            'Название': obj.get('name', 'N/A'),
            'Масса (кг)': obj.get('mass', 0),
            'Сечение (м²)': round(obj.get('xSectAvg', 0), 3),
            'Форма': obj.get('shape', 'N/A')
        })
    
    summary_df = pd.DataFrame(summary_data)
    summary_file = 'phase_portrait_summary.xlsx'
    summary_df.to_excel(summary_file, index=False)
    print(f"✅ Сводный отчет сохранен: {summary_file}")
    
    # Итоговая статистика
    print("\n" + "="*70)
    print("✅ ГЕНЕРАЦИЯ ЗАВЕРШЕНА")
    print("="*70)
    print(f"📁 Космические аппараты: {len(spacecraft_files)} файлов в папке {output_dirs['spacecraft']}")
    print(f"📁 Космический мусор: {len(debris_files)} файлов в папке {output_dirs['debris']}")
    print(f"📊 Сводный отчет: {summary_file}")
    print("\n📋 Пример структуры файла:")
    print("  - Лист 'Информация': параметры объекта")
    print("  - Лист 'Фазовый портрет': колонки:")
    print("    * phi_deg - фазовый угол (градусы)")
    print("    * magnitude - звездная величина")
    print("    * reduced_magnitude - приведенная звездная величина")
    print("    * alpha_deg, beta_deg, epsilon_deg - углы ориентации")
    print("    * distance_km - расстояние до наблюдателя")
    print("    * flux_W_m2 - плотность потока")

if __name__ == "__main__":
    main()