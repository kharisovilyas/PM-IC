##!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import argparse
from time import time
import xml.etree.ElementTree as ET
import warnings

from pdalib import PDATask


warnings.filterwarnings("ignore")

class Profiler(object):
    """Класс для профилирования времени выполнения кода"""
    def __init__(self,info=''):
        self.info = info
    def __enter__(self):
        self._startTime = time()
    def __exit__(self, type, value, traceback):
        print(self.info, "\nElapsed time: {:.3f} sec\n".format(time() - self._startTime))

filename1 = 'simple.xml'

import os
import shutil

arg = argparse.ArgumentParser()
arg.add_argument('--filename', '-f', nargs='+')
arg.add_argument('--output_dir', '-o', nargs='+')
args = arg.parse_args()

if args.output_dir:
    dir = args.output_dir[0]
else:
    dir = 'results'

if args.filename:
    filename1 = str(args.filename[0])
filename = os.path.join(dir,filename1.split('.')[0])
filename_synth = filename + '_by_synth.xml'
filename_report = filename + '_report.xml'

if os.path.exists(dir):
    shutil.rmtree(dir)
os.makedirs(dir)

def main():
    '''Стандартное решение задачи - для всех интервалов сразу'''
    TASK = PDATask(Filename=filename1, Name=filename)

    print('ЗАДАЧА ЛП\n', len(TASK.CVector), 'переменных и', len(TASK.BVector), 'ограничений')
    print('Начали оптимизацию...')

    with Profiler('TASK solved'):
        TASK.PLAN
        print(TASK)
        print('PLAN')
        print(TASK.PLAN)
        print('/PLAN')

    print('Расчет окончен.')

    print('Формируем отчет...')
    with Profiler('REPORT formed'):
        TASK.REPORT
    print('Отчет сформирован.')
    return TASK

if __name__ == '__main__':
    with Profiler("Общее время выполнения задания") as p:
        with Profiler("Время непосредственных расчетов"):
            TASK = main()
            TASK.Name = filename
        with Profiler("Время формирования отчета"):
            TASK.REPORT
        with Profiler("Время сохранения отчета"):
            TASK.toFile()