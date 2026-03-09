#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Простая программа для построения фазового портрета из одного файла
"""

import pandas as pd
import matplotlib.pyplot as plt
import sys
import os

def plot_simple_portrait(filename):
    """
    Строит простой фазовый портрет из файла
    """
    # Читаем данные
    df = pd.read_excel(filename)
    
    # Создаем график
    plt.figure(figsize=(10, 8))
    
    # Строим точки
    plt.scatter(df['phi'], df['M'], c='blue', s=30, alpha=0.7)
    
    # Настройки как на картинке
    plt.xlabel('φ (фазовый угол, градусы)', fontsize=14)
    plt.ylabel('M (звездная величина)', fontsize=14)
    plt.title(f'Фазовый портрет: {os.path.basename(filename)}', fontsize=16)
    plt.grid(True, alpha=0.3)
    plt.gca().invert_yaxis()  # Важно! Инвертируем ось Y
    plt.xlim(0, 180)
    
    # Сохраняем
    output = filename.replace('.xlsx', '_portrait.png')
    plt.savefig(output, dpi=150, bbox_inches='tight')
    plt.show()  # Показываем график
    plt.close()
    
    print(f"✅ График сохранен: {output}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        filename = sys.argv[1]
        if os.path.exists(filename):
            plot_simple_portrait(filename)
        else:
            print(f"❌ Файл {filename} не найден")
    else:
        print("Использование: python plot_portrait.py <файл.xlsx>")