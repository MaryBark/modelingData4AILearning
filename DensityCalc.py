import json
import math
import numpy as np
from typing import Dict, List, Union, Optional, Tuple

class PhotometryCalculator:
    """
    Класс для расчёта фотометрических характеристик космических объектов
    на основе моделей отражения из инструкции.
    """
    
    # Константы
    S0 = 1376  # Вт/м^2 - плотность лучистого потока Солнца в околоземном пространстве
    S0_ALT = 1400  # альтернативное значение из инструкции
    
    def __init__(self):
        pass
    
    @staticmethod
    def deg_to_rad(degrees: float) -> float:
        """Преобразование градусов в радианы"""
        return degrees * math.pi / 180.0
    
    @staticmethod
    def rad_to_deg(radians: float) -> float:
        """Преобразование радианов в градусы"""
        return radians * 180.0 / math.pi
    
    def calculate_magnitude(self, E: float, d: float = None) -> float:
        """
        Расчёт звёздной величины по плотности потока
        
        Параметры:
        E - плотность потока на расстоянии d
        d - расстояние до объекта (не используется напрямую, но может быть нужно для логики)
        
        Возвращает:
        m - звёздная величина
        """
        if E <= 0:
            return float('inf')
        
        # m = m0 - 2.5 * lg(E / E0)
        # где m0 = -26.7 - звёздная величина Солнца
        # E0 = 1367 Вт/м^2 - плотность потока от Солнца
        m0 = -26.7
        E0 = 1367.0
        
        m = m0 - 2.5 * math.log10(E / E0)
        return m
    
    def reduced_magnitude(self, m: float, d: float, d0: float = 1.0) -> float:
        """
        Приведение звёздной величины к стандартному расстоянию
        
        M = m - 5 * lg(d / d0)
        
        Параметры:
        m - наблюдаемая звёздная величина
        d - расстояние от наблюдателя до объекта
        d0 - расстояние приведения (по умолчанию 1)
        
        Возвращает:
        M - приведённая звёздная величина
        """
        if d <= 0 or d0 <= 0:
            raise ValueError("Расстояния должны быть положительными")
        
        M = m - 5.0 * math.log10(d / d0)
        return M
    
    def sphere_diffuse(self, R: float, a: float, phi: float, d: float, use_alt_s0: bool = False) -> Dict:
        """
        Диффузно отражающая сфера
        
        E = 2/3 * a * S0 * R^2 * ((π - φ) * cos φ + sin φ) / (π * d^2)
        
        Параметры:
        R - радиус сферы
        a - коэффициент отражения (0-1)
        phi - фазовый угол (радианы)
        d - расстояние до наблюдателя
        use_alt_s0 - использовать альтернативное S0 (1400 вместо 1376)
        """
        S0 = self.S0_ALT if use_alt_s0 else self.S0
        
        # Функция f(φ) = ((π - φ) * cos φ + sin φ) / π
        f_phi = ((math.pi - phi) * math.cos(phi) + math.sin(phi)) / math.pi
        
        # Расчёт E
        E = (2.0 / 3.0) * a * S0 * R**2 * f_phi / (math.pi * d**2)
        
        m = self.calculate_magnitude(E)
        
        return {
            'E': E,
            'magnitude': m,
            'f_phi': f_phi,
            'model': 'sphere_diffuse'
        }
    
    def sphere_specular(self, R: float, a: float, d: float, use_alt_s0: bool = False) -> Dict:
        """
        Зеркально отражающая сфера
        
        E = a * S0 * R^2 / (4 * d^2)
        
        Параметры:
        R - радиус сферы
        a - коэффициент отражения
        d - расстояние до наблюдателя
        use_alt_s0 - использовать альтернативное S0
        """
        S0 = self.S0_ALT if use_alt_s0 else self.S0
        
        E = a * S0 * R**2 / (4 * d**2)
        m = self.calculate_magnitude(E)
        
        return {
            'E': E,
            'magnitude': m,
            'model': 'sphere_specular'
        }
    
    def cylinder_diffuse(self, R: float, h: float, a: float, 
                         alpha: float, beta: float, epsilon: float, 
                         d: float, use_alt_s0: bool = False) -> Dict:
        """
        Диффузно отражающий цилиндр
        
        E = 0.5 * a * S0 * R * h * (((π - ε) * cos ε + sin ε) / π) * sin α * sin β / (d^2)
        
        Параметры:
        R - радиус цилиндра
        h - высота цилиндра
        a - коэффициент отражения
        alpha - угол между осью цилиндра и направлением на Солнце (радианы)
        beta - угол между осью цилиндра и направлением на наблюдателя (радианы)
        epsilon - угол между плоскостями, образованными осью цилиндра и направлениями на Солнце и наблюдателя (радианы)
        d - расстояние до наблюдателя
        use_alt_s0 - использовать альтернативное S0
        """
        S0 = self.S0_ALT if use_alt_s0 else self.S0
        
        # Функция f(ε) = ((π - ε) * cos ε + sin ε) / π
        f_epsilon = ((math.pi - epsilon) * math.cos(epsilon) + math.sin(epsilon)) / math.pi
        
        E = 0.5 * a * S0 * R * h * f_epsilon * math.sin(alpha) * math.sin(beta) / (d**2)
        m = self.calculate_magnitude(E)
        
        return {
            'E': E,
            'magnitude': m,
            'f_epsilon': f_epsilon,
            'sin_alpha': math.sin(alpha),
            'sin_beta': math.sin(beta),
            'model': 'cylinder_diffuse'
        }
    
    def cylinder_specular(self, R: float, h: float, a: float, 
                          epsilon: float, d: float, use_alt_s0: bool = False) -> Dict:
        """
        Зеркально отражающий цилиндр
        
        E = a * S0 * R * h * cos(ε/2) / (d^2)
        
        Параметры:
        R - радиус цилиндра
        h - высота цилиндра
        a - коэффициент отражения
        epsilon - угол между плоскостями (радианы)
        d - расстояние до наблюдателя
        use_alt_s0 - использовать альтернативное S0
        """
        S0 = self.S0_ALT if use_alt_s0 else self.S0
        
        E = a * S0 * R * h * math.cos(epsilon / 2) / (d**2)
        m = self.calculate_magnitude(E)
        
        return {
            'E': E,
            'magnitude': m,
            'cos_epsilon2': math.cos(epsilon / 2),
            'model': 'cylinder_specular'
        }
    
    def plane_diffuse(self, F: float, a: float, alpha: float, beta: float, 
                      d: float, use_alt_s0: bool = False) -> Dict:
        """
        Диффузно отражающая плоскость
        
        E = a * S0 * F * cos α * cos β / (π * d^2)
        
        Параметры:
        F - площадь плоскости
        a - коэффициент отражения
        alpha - угол между нормалью к плоскости и направлением на Солнце (радианы)
        beta - угол между нормалью к плоскости и направлением на наблюдателя (радианы)
        d - расстояние до наблюдателя
        use_alt_s0 - использовать альтернативное S0
        """
        # Проверка условия α < π/2, β < π/2
        if alpha >= math.pi/2 or beta >= math.pi/2:
            return {
                'E': 0,
                'magnitude': float('inf'),
                'warning': 'Углы должны быть меньше π/2',
                'model': 'plane_diffuse'
            }
        
        S0 = self.S0_ALT if use_alt_s0 else self.S0
        
        E = a * S0 * F * math.cos(alpha) * math.cos(beta) / (math.pi * d**2)
        m = self.calculate_magnitude(E)
        
        return {
            'E': E,
            'magnitude': m,
            'cos_alpha': math.cos(alpha),
            'cos_beta': math.cos(beta),
            'model': 'plane_diffuse'
        }
    
    def plane_specular(self, F: float, a: float, alpha: float, gamma: float, 
                       k: float, d: float, use_alt_s0: bool = False) -> Dict:
        """
        Зеркально отражающая плоскость (модель Фонга)
        
        E = a * S0 * F * cos α * cos^k ɤ * (k+1) / (2 * π * d^2)
        
        Параметры:
        F - площадь плоскости
        a - коэффициент отражения
        alpha - угол между нормалью к плоскости и направлением на Солнце (радианы)
        gamma - угол между зеркально отраженным лучом и направлением на наблюдателя (радианы)
        k - эмпирическая константа (показатель Фонга)
        d - расстояние до наблюдателя
        use_alt_s0 - использовать альтернативное S0
        """
        # Проверка условия α < π/2, ɤ < π/2
        if alpha >= math.pi/2 or gamma >= math.pi/2:
            return {
                'E': 0,
                'magnitude': float('inf'),
                'warning': 'Углы должны быть меньше π/2',
                'model': 'plane_specular'
            }
        
        S0 = self.S0_ALT if use_alt_s0 else self.S0
        
        E = a * S0 * F * math.cos(alpha) * (math.cos(gamma) ** k) * (k + 1) / (2 * math.pi * d**2)
        m = self.calculate_magnitude(E)
        
        return {
            'E': E,
            'magnitude': m,
            'cos_alpha': math.cos(alpha),
            'cos_gamma_k': math.cos(gamma) ** k,
            'model': 'plane_specular',
            'phong_factor': k
        }


class ObjectPhotometry:
    """
    Класс для работы с данными объектов из JSON и расчёта их фотометрических характеристик
    """
    
    def __init__(self, debris_file: str, spacecraft_file: str):
        """
        Инициализация с загрузкой данных из JSON-файлов
        
        Параметры:
        debris_file - путь к файлу debris_20260307_202246.json
        spacecraft_file - путь к файлу spacecraft_20260307_202246.json
        """
        self.debris_data = self._load_json(debris_file)
        self.spacecraft_data = self._load_json(spacecraft_file)
        self.calculator = PhotometryCalculator()
        
        # Объединённый список объектов
        self.all_objects = self.debris_data + self.spacecraft_data
    
    def _load_json(self, filepath: str) -> List[Dict]:
        """Загрузка данных из JSON-файла"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Файл {filepath} не найден")
            return []
        except json.JSONDecodeError:
            print(f"Ошибка декодирования JSON в файле {filepath}")
            return []
    
    def get_object_by_name(self, name: str) -> Optional[Dict]:
        """Поиск объекта по имени"""
        for obj in self.all_objects:
            if obj.get('name') == name:
                return obj
        return None
    
    def get_object_by_cospar(self, cospar_id: str) -> Optional[Dict]:
        """Поиск объекта по COSPAR ID"""
        for obj in self.all_objects:
            if obj.get('cosparId') == cospar_id:
                return obj
        return None
    
    def get_object_by_satno(self, satno: int) -> Optional[Dict]:
        """Поиск объекта по NORAD ID"""
        for obj in self.all_objects:
            if obj.get('satno') == satno:
                return obj
        return None
    
    def calculate_for_object(self, obj: Dict, params: Dict) -> Dict:
        """
        Расчёт фотометрических характеристик для конкретного объекта
        
        Параметры:
        obj - словарь с данными объекта
        params - словарь с параметрами наблюдения:
            - d: расстояние до наблюдателя (м)
            - phi: фазовый угол (градусы) - для сферы
            - alpha: угол к Солнцу (градусы)
            - beta: угол к наблюдателю (градусы)
            - epsilon: угол между плоскостями (градусы)
            - gamma: угол зеркального отражения (градусы)
            - k: коэффициент Фонга (для зеркальной плоскости)
            - use_alt_s0: использовать альтернативное S0
            - model: модель ('sphere_diffuse', 'sphere_specular', 'cylinder_diffuse', 
                     'cylinder_specular', 'plane_diffuse', 'plane_specular')
            - a: коэффициент отражения (если не указан, используется 0.5)
        """
        
        shape = obj.get('shape', '')
        a = params.get('a', 0.5)  # коэффициент отражения по умолчанию
        d = params.get('d', 1000.0)  # расстояние по умолчанию 1000 м
        use_alt_s0 = params.get('use_alt_s0', False)
        model = params.get('model', '')
        
        # Если модель не указана, пытаемся определить по форме
        if not model:
            if shape == 'Sphere':
                model = 'sphere_diffuse'
            elif shape == 'Cyl':
                model = 'cylinder_diffuse'
            elif shape == 'Box':
                model = 'plane_diffuse'
            else:
                model = 'sphere_diffuse'  # по умолчанию
        
        result = {
            'object': obj.get('name', 'Unknown'),
            'cospar_id': obj.get('cosparId', ''),
            'satno': obj.get('satno', 0),
            'shape': shape,
            'model': model,
            'params': params
        }
        
        try:
            if model == 'sphere_diffuse':
                R = obj.get('diameter', 1.0) / 2 if obj.get('diameter') else 1.0
                phi_rad = self.calculator.deg_to_rad(params.get('phi', 0))
                calc_result = self.calculator.sphere_diffuse(R, a, phi_rad, d, use_alt_s0)
                
            elif model == 'sphere_specular':
                R = obj.get('diameter', 1.0) / 2 if obj.get('diameter') else 1.0
                calc_result = self.calculator.sphere_specular(R, a, d, use_alt_s0)
                
            elif model == 'cylinder_diffuse':
                R = obj.get('diameter', 1.0) / 2 if obj.get('diameter') else 1.0
                h = obj.get('height', 1.0) if obj.get('height') else 1.0
                alpha_rad = self.calculator.deg_to_rad(params.get('alpha', 45))
                beta_rad = self.calculator.deg_to_rad(params.get('beta', 45))
                epsilon_rad = self.calculator.deg_to_rad(params.get('epsilon', 0))
                calc_result = self.calculator.cylinder_diffuse(R, h, a, alpha_rad, beta_rad, epsilon_rad, d, use_alt_s0)
                
            elif model == 'cylinder_specular':
                R = obj.get('diameter', 1.0) / 2 if obj.get('diameter') else 1.0
                h = obj.get('height', 1.0) if obj.get('height') else 1.0
                epsilon_rad = self.calculator.deg_to_rad(params.get('epsilon', 0))
                calc_result = self.calculator.cylinder_specular(R, h, a, epsilon_rad, d, use_alt_s0)
                
            elif model == 'plane_diffuse':
                # Для плоскости оцениваем площадь как xSectAvg или рассчитываем
                F = obj.get('xSectAvg', 10.0)
                if F is None:
                    F = 10.0
                alpha_rad = self.calculator.deg_to_rad(params.get('alpha', 45))
                beta_rad = self.calculator.deg_to_rad(params.get('beta', 45))
                calc_result = self.calculator.plane_diffuse(F, a, alpha_rad, beta_rad, d, use_alt_s0)
                
            elif model == 'plane_specular':
                F = obj.get('xSectAvg', 10.0)
                if F is None:
                    F = 10.0
                alpha_rad = self.calculator.deg_to_rad(params.get('alpha', 45))
                gamma_rad = self.calculator.deg_to_rad(params.get('gamma', 0))
                k = params.get('k', 10.0)  # типичное значение для зеркальных поверхностей
                calc_result = self.calculator.plane_specular(F, a, alpha_rad, gamma_rad, k, d, use_alt_s0)
                
            else:
                result['error'] = f"Неизвестная модель: {model}"
                return result
            
            result.update(calc_result)
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def calculate_phase_portrait(self, obj: Dict, phi_range: Tuple[float, float] = (0, 180), 
                                 num_points: int = 50, **kwargs) -> Dict:
        """
        Расчёт фазового портрета объекта (зависимость блеска от фазового угла)
        
        Параметры:
        obj - словарь с данными объекта
        phi_range - диапазон фазовых углов (мин, макс) в градусах
        num_points - количество точек
        kwargs - дополнительные параметры для calculate_for_object
        """
        phi_min, phi_max = phi_range
        phi_values = np.linspace(phi_min, phi_max, num_points)
        
        magnitudes = []
        e_values = []
        
        for phi in phi_values:
            params = kwargs.copy()
            params['phi'] = phi
            params['model'] = params.get('model', 'sphere_diffuse')
            
            result = self.calculate_for_object(obj, params)
            if 'magnitude' in result and not math.isinf(result['magnitude']):
                magnitudes.append(result['magnitude'])
                e_values.append(result['E'])
            else:
                magnitudes.append(None)
                e_values.append(None)
        
        return {
            'object_name': obj.get('name', 'Unknown'),
            'phi_degrees': phi_values.tolist(),
            'magnitudes': magnitudes,
            'e_values': e_values,
            'parameters': kwargs
        }


def main():
    """
    Пример использования программы
    """
    
    # Пути к файлам
    debris_file = "debris_20260307_202246.json"
    spacecraft_file = "spacecraft_20260307_202246.json"
    
    # Создаём экземпляр класса для работы с объектами
    photometry = ObjectPhotometry(debris_file, spacecraft_file)
    
    # Пример 1: Расчёт для объекта Dragon Trunk
    dragon_trunk = photometry.get_object_by_name("Dragon Trunk")
    
    if dragon_trunk:
        print("=" * 60)
        print(f"Объект: {dragon_trunk['name']} (COSPAR: {dragon_trunk.get('cosparId', 'N/A')})")
        print(f"Форма: {dragon_trunk.get('shape', 'Unknown')}")
        print(f"Диаметр: {dragon_trunk.get('diameter', 'N/A')} м")
        print(f"Высота: {dragon_trunk.get('height', 'N/A')} м")
        print("=" * 60)
        
        # Параметры наблюдения для цилиндра
        params = {
            'd': 1000.0,  # расстояние 1000 м
            'alpha': 45.0,  # угол к Солнцу 45°
            'beta': 30.0,   # угол к наблюдателю 30°
            'epsilon': 10.0, # угол между плоскостями 10°
            'a': 0.7,       # коэффициент отражения
            'model': 'cylinder_diffuse',
            'use_alt_s0': False
        }
        
        # Расчёт для цилиндрической модели (подходит для Dragon Trunk)
        result = photometry.calculate_for_object(dragon_trunk, params)
        
        print("\nРезультаты расчёта (диффузный цилиндр):")
        print(f"Модель: {result.get('model', 'N/A')}")
        print(f"Плотность потока E = {result.get('E', 0):.6e} Вт/м²")
        print(f"Звёздная величина m = {result.get('magnitude', float('inf')):.2f}")
        
        # Расчёт фазового портрета
        print("\nРасчёт фазового портрета...")
        phase_portrait = photometry.calculate_phase_portrait(
            dragon_trunk, 
            phi_range=(0, 60),  # фазовые углы 0-60°
            num_points=10,
            **params
        )
        
        print("\nФазовый портрет (ϕ° → m):")
        for phi, mag in zip(phase_portrait['phi_degrees'][:5], phase_portrait['magnitudes'][:5]):
            if mag is not None:
                print(f"  ϕ = {phi:.1f}° → m = {mag:.2f}")
        print("  ...")
    
    # Пример 2: Поиск объекта по NORAD ID
    print("\n" + "=" * 60)
    obj_by_satno = photometry.get_object_by_satno(37253)
    if obj_by_satno:
        print(f"Найден объект с NORAD ID 37253: {obj_by_satno.get('name', 'Unknown')}")
    
    # Пример 3: Демонстрация различных моделей
    print("\n" + "=" * 60)
    print("Демонстрация различных моделей отражения")
    print("-" * 40)
    
    # Создаём тестовый объект для демонстрации
    test_obj = {
        'name': 'Test Object',
        'shape': 'Test',
        'diameter': 2.0,
        'height': 3.0,
        'xSectAvg': 10.0
    }
    
    models_to_test = [
        ('sphere_diffuse', {'phi': 30}),
        ('sphere_specular', {}),
        ('cylinder_diffuse', {'alpha': 45, 'beta': 45, 'epsilon': 10}),
        ('cylinder_specular', {'epsilon': 10}),
        ('plane_diffuse', {'alpha': 30, 'beta': 30}),
        ('plane_specular', {'alpha': 30, 'gamma': 5, 'k': 20})
    ]
    
    for model_name, extra_params in models_to_test:
        params = {
            'd': 1000.0,
            'a': 0.6,
            'model': model_name,
            **extra_params
        }
        result = photometry.calculate_for_object(test_obj, params)
        if 'magnitude' in result:
            print(f"{model_name:20s}: E = {result.get('E', 0):.6e} Вт/м², m = {result.get('magnitude', float('inf')):.2f}")


if __name__ == "__main__":
    main()