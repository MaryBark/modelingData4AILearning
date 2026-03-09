#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Программа для построения фазовых портретов из сгенерированных данных
Читает файлы из папок Spacecrafts_site_1000 и SpaceDebris_site_1000
Строит графики M(φ) с правильным диапазоном звездных величин (0-26)
"""

import pandas as pd
import matplotlib.pyplot as plt
import os
import glob
import numpy as np

def normalize_magnitude(m_value, original_min=10000, original_max=55000, target_min=0, target_max=26):
    """
    Нормализует значение M из диапазона 10000-55000 в диапазон 0-26
    """
    # Инвертируем, так как меньшая звездная величина = ярче
    normalized = target_max - ((m_value - original_min) / (original_max - original_min)) * (target_max - target_min)
    return np.clip(normalized, target_min, target_max)

def plot_phase_portrait_from_file(filename, output_dir='phase_portraits'):
    """
    Строит фазовый портрет из одного файла с нормализованными значениями M
    """
    # Создаем папку для графиков
    os.makedirs(output_dir, exist_ok=True)
    
    # Читаем данные
    df = pd.read_excel(filename)
    
    # Нормализуем M в диапазон 0-26
    df['M_norm'] = df['M'].apply(normalize_magnitude)
    
    # Извлекаем имя файла без расширения
    base_name = os.path.basename(filename)
    name_without_ext = os.path.splitext(base_name)[0]
    
    # Создаем график
    plt.figure(figsize=(12, 8))
    
    # Строим точки
    plt.scatter(df['phi'], df['M_norm'], c='blue', s=30, alpha=0.7, edgecolors='none')
    
    # Настройки графика как на картинке
    plt.xlabel('φ (фазовый угол, градусы)', fontsize=14)
    plt.ylabel('M (звездная величина)', fontsize=14)
    plt.title(f'Фазовый портрет: {name_without_ext}', fontsize=16)
    plt.grid(True, alpha=0.3, linestyle='--')
    
    # Устанавливаем пределы как на картинке
    plt.xlim(0, 180)
    plt.ylim(26, 0)  # Инвертированный диапазон (0 вверху, 26 внизу)
    
    # Добавляем горизонтальные линии как на картинке
    for y in range(0, 27, 2):
        plt.axhline(y=y, color='gray', linestyle='-', alpha=0.2)
    
    # Добавляем вертикальные линии для основных углов
    for x in range(0, 181, 30):
        plt.axvline(x=x, color='gray', linestyle='-', alpha=0.1)
    
    # Сохраняем график
    output_file = os.path.join(output_dir, f'{name_without_ext}_portrait.png')
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"  ✅ График сохранен: {output_file} (M: 0-26)")
    
    return output_file

def plot_combined_portraits(folder_path, output_dir='phase_portraits', max_files=30):
    """
    Строит несколько фазовых портретов на одном графике для сравнения
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Находим все Excel файлы в папке
    excel_files = glob.glob(os.path.join(folder_path, '*.xlsx'))
    
    if not excel_files:
        print(f"❌ В папке {folder_path} нет Excel файлов")
        return
    
    # Берем первые max_files файлов
    files_to_plot = excel_files[:max_files]
    
    plt.figure(figsize=(14, 10))
    
    colors = plt.cm.tab20(np.linspace(0, 1, len(files_to_plot)))
    
    for i, filename in enumerate(files_to_plot):
        try:
            df = pd.read_excel(filename)
            df['M_norm'] = df['M'].apply(normalize_magnitude)
            base_name = os.path.basename(filename)
            name_without_ext = os.path.splitext(base_name)[0][:20]
            
            plt.scatter(df['phi'], df['M_norm'], c=[colors[i]], s=15, alpha=0.6,
                       label=name_without_ext, edgecolors='none')
        except Exception as e:
            print(f"  ⚠ Ошибка чтения {filename}: {e}")
            continue
    
    plt.xlabel('φ (фазовый угол, градусы)', fontsize=14)
    plt.ylabel('M (звездная величина)', fontsize=14)
    plt.title(f'Сравнение фазовых портретов (первые {len(files_to_plot)} объектов)', fontsize=16)
    plt.grid(True, alpha=0.3, linestyle='--')
    plt.xlim(0, 180)
    plt.ylim(26, 0)
    
    # Добавляем горизонтальные линии
    for y in range(0, 27, 2):
        plt.axhline(y=y, color='gray', linestyle='-', alpha=0.1)
    
    for x in range(0, 181, 30):
        plt.axvline(x=x, color='gray', linestyle='-', alpha=0.1)
    
    plt.legend(loc='best', fontsize=8, ncol=2)
    
    folder_name = os.path.basename(folder_path)
    output_file = os.path.join(output_dir, f'comparison_{folder_name}.png')
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"  ✅ Сравнительный график сохранен: {output_file}")

def plot_summary_portrait(folder_path, output_dir='phase_portraits'):
    """
    Строит сводный график со всеми объектами из папки
    """
    os.makedirs(output_dir, exist_ok=True)
    
    excel_files = glob.glob(os.path.join(folder_path, '*.xlsx'))
    
    if not excel_files:
        print(f"❌ В папке {folder_path} нет Excel файлов")
        return
    
    plt.figure(figsize=(14, 10))
    
    for filename in excel_files[:200]:  # Ограничиваем до 200 для читаемости
        try:
            df = pd.read_excel(filename)
            df['M_norm'] = df['M'].apply(normalize_magnitude)
            
            # Определяем цвет по имени файла
            base_name = os.path.basename(filename).upper()
            if 'GPS' in base_name or 'NAVSTAR' in base_name or 'GLONASS' in base_name:
                color = 'red'
                alpha = 0.3
            elif 'GEO' in base_name or 'INMARSAT' in base_name or 'TERRESTAR' in base_name:
                color = 'green'
                alpha = 0.3
            elif 'PAYLOAD' in base_name or 'SC' in base_name:
                color = 'blue'
                alpha = 0.2
            elif 'ROCKET' in base_name:
                color = 'orange'
                alpha = 0.2
            else:
                color = 'gray'
                alpha = 0.1
            
            plt.scatter(df['phi'], df['M_norm'], c=color, s=5, alpha=alpha, edgecolors='none')
            
        except Exception:
            continue
    
    plt.xlabel('φ (фазовый угол, градусы)', fontsize=16)
    plt.ylabel('M (звездная величина)', fontsize=16)
    plt.title('Сводный фазовый портрет\n(красный - навигационные, зеленый - геостационарные, синий - КА, серый - мусор)', 
              fontsize=18)
    plt.grid(True, alpha=0.3, linestyle='--')
    plt.xlim(0, 180)
    plt.ylim(26, 0)
    
    # Добавляем горизонтальные линии
    for y in range(0, 27, 2):
        plt.axhline(y=y, color='gray', linestyle='-', alpha=0.1)
    
    for x in range(0, 181, 30):
        plt.axvline(x=x, color='gray', linestyle='-', alpha=0.1)
    
    # Добавляем легенду
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='red', alpha=0.5, label='Навигационные КА'),
        Patch(facecolor='green', alpha=0.5, label='Геостационарные КА'),
        Patch(facecolor='blue', alpha=0.5, label='Другие КА'),
        Patch(facecolor='orange', alpha=0.5, label='Ракеты'),
        Patch(facecolor='gray', alpha=0.5, label='Мусор')
    ]
    plt.legend(handles=legend_elements, loc='upper right', fontsize=10)
    
    folder_name = os.path.basename(folder_path)
    output_file = os.path.join(output_dir, f'summary_{folder_name}.png')
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"  ✅ Сводный график сохранен: {output_file}")

def plot_individual_portraits(folder_path, output_dir='phase_portraits', max_files=10):
    """
    Строит индивидуальные графики для первых нескольких файлов
    """
    excel_files = glob.glob(os.path.join(folder_path, '*.xlsx'))
    
    if not excel_files:
        return
    
    # Создаем подпапку для индивидуальных графиков
    indiv_dir = os.path.join(output_dir, 'individual', os.path.basename(folder_path))
    os.makedirs(indiv_dir, exist_ok=True)
    
    print(f"\n  📊 Индивидуальные графики для {os.path.basename(folder_path)}:")
    
    for i, filename in enumerate(excel_files[:max_files]):
        try:
            plot_phase_portrait_from_file(filename, indiv_dir)
        except Exception as e:
            print(f"    ⚠ Ошибка: {e}")

def create_grid_portrait(folder_path, output_dir='phase_portraits', grid_size=(4, 4)):
    """
    Создает сетку из нескольких фазовых портретов
    """
    excel_files = glob.glob(os.path.join(folder_path, '*.xlsx'))
    
    if not excel_files:
        return
    
    n_rows, n_cols = grid_size
    n_plots = n_rows * n_cols
    
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(n_cols*5, n_rows*4))
    axes = axes.flatten()
    
    for i, filename in enumerate(excel_files[:n_plots]):
        try:
            df = pd.read_excel(filename)
            df['M_norm'] = df['M'].apply(normalize_magnitude)
            base_name = os.path.basename(filename)
            name_without_ext = os.path.splitext(base_name)[0][:20]
            
            ax = axes[i]
            ax.scatter(df['phi'], df['M_norm'], c='blue', s=10, alpha=0.6)
            ax.set_xlim(0, 180)
            ax.set_ylim(26, 0)
            ax.grid(True, alpha=0.3)
            ax.set_title(name_without_ext, fontsize=8)
            
            if i >= n_plots - n_cols:
                ax.set_xlabel('φ', fontsize=8)
            if i % n_cols == 0:
                ax.set_ylabel('M', fontsize=8)
        except Exception:
            axes[i].text(0.5, 0.5, 'Ошибка', ha='center', va='center')
            axes[i].set_xlim(0, 1)
            axes[i].set_ylim(0, 1)
    
    # Скрываем лишние подграфики
    for i in range(len(excel_files[:n_plots]), n_plots):
        axes[i].set_visible(False)
    
    plt.tight_layout()
    
    folder_name = os.path.basename(folder_path)
    output_file = os.path.join(output_dir, f'grid_{folder_name}.png')
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"  ✅ Сетка графиков сохранена: {output_file}")

def analyze_magnitude_range(folder_path):
    """
    Анализирует диапазон значений M в файлах
    """
    excel_files = glob.glob(os.path.join(folder_path, '*.xlsx'))
    
    if not excel_files:
        return
    
    all_m = []
    for filename in excel_files[:50]:
        try:
            df = pd.read_excel(filename)
            all_m.extend(df['M'].values)
        except:
            continue
    
    if all_m:
        print(f"\n  📊 Анализ значений M в {os.path.basename(folder_path)}:")
        print(f"     Исходный диапазон: {min(all_m):.0f} - {max(all_m):.0f}")
        
        # Нормализованные значения
        norm_m = [normalize_magnitude(x) for x in all_m]
        print(f"     Нормализованный: {min(norm_m):.1f} - {max(norm_m):.1f}")

def main():
    print("="*80)
    print("📊 ПОСТРОЕНИЕ ФАЗОВЫХ ПОРТРЕТОВ")
    print("📁 Чтение файлов из папок Spacecrafts_site_1000 и SpaceDebris_site_1000")
    print("📈 Диапазон звездных величин: 0-26 (как на классических графиках)")
    print("="*80)
    
    # Папки с данными
    folders = {
        'Космические аппараты': 'Spacecrafts_site_1000',
        'Космический мусор': 'SpaceDebris_site_1000'
    }
    
    # Папка для графиков
    plots_dir = 'PhasePortraits_plots_normalized'
    os.makedirs(plots_dir, exist_ok=True)
    
    for folder_name, folder_path in folders.items():
        if not os.path.exists(folder_path):
            print(f"\n❌ Папка {folder_path} не найдена")
            continue
        
        print(f"\n📁 Обработка: {folder_name}")
        
        # Находим все Excel файлы
        excel_files = glob.glob(os.path.join(folder_path, '*.xlsx'))
        print(f"   Найдено файлов: {len(excel_files)}")
        
        if len(excel_files) == 0:
            continue
        
        # Анализируем диапазон M
        analyze_magnitude_range(folder_path)
        
        # 1. Индивидуальные графики для первых 10 файлов
        plot_individual_portraits(folder_path, plots_dir, max_files=10)
        
        # 2. Сравнительный график для первых 30 файлов
        print(f"\n  📊 Сравнительный график...")
        plot_combined_portraits(folder_path, plots_dir, max_files=30)
        
        # 3. Сводный график всех объектов
        print(f"  📊 Сводный график...")
        plot_summary_portrait(folder_path, plots_dir)
        
        # 4. Сетка графиков 4x4
        print(f"  📊 Сетка графиков...")
        create_grid_portrait(folder_path, plots_dir, grid_size=(4, 4))
    
    print("\n" + "="*80)
    print("✅ ВСЕ ГРАФИКИ СОЗДАНЫ")
    print(f"📁 Результаты в папке: {plots_dir}/")
    print("   Структура:")
    print("   - individual/ - индивидуальные графики")
    print("   - comparison_*.png - сравнительные графики")
    print("   - summary_*.png - сводные графики")
    print("   - grid_*.png - сетки графиков")
    print(f"\n📈 Диапазон звездных величин: 0-26")
    print("="*80)


if __name__ == "__main__":
    # Проверяем наличие необходимых библиотек
    try:
        import matplotlib
        import numpy
    except ImportError as e:
        print(f"❌ Ошибка: {e}")
        print("Установите необходимые библиотеки:")
        print("pip install matplotlib pandas numpy openpyxl")
        exit(1)
    
    main()