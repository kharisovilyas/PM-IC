# -*- coding: utf-8 -*-
__author__ = 'Дмитрий Александрович Павлов'
__version__ = '0.3.0'

from copy import copy, deepcopy
import xml.etree.ElementTree as ET
from typing import TypeVar, Iterable, Tuple, Callable, Any, Mapping
from itertools import combinations

from pulp import LpProblem, LpVariable, LpMinimize, LpMaximize
from pulp import PULP_CBC_CMD, LpContinuous, lpDot

from bpmn_diagram.main import make_techchains_bpmn_from_report

#have_stars = False

def elprint(j: ET.Element, tab=0):
    print('  '*tab, j, j.attrib, j.text)
    tab += 1
    for i in j.findall('*'):
        elprint(i, tab+1)

def get_key(__d: Any, __value: Any) -> Any:
    """Получение ключа по значению value из произвольного словаря d
    Если такого ключа нет - возвращает None"""
    for k, v in __d.items():
        if v == __value:
            return k
    return None

def indent(elem: ET.Element, level: int=0) -> None:
    """Делает отступы и переносы строк в XML"""
    i = "\n" + level*"    "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "    "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

def iterfind(elem: ET.Element, id, tag: str='selector') -> ET.Element:
    """Ищет во всем поддереве удовлетворяющий СЕЛЕКТОР"""
    for i in elem.findall(tag):
        new_elem = iterfind(i, id)
        if new_elem:
            return new_elem
    #print(elem.tag, tag, elem.attrib['id'] if 'id' in elem.attrib else False, id)
    #print(type(elem.tag), type(tag), type(elem.attrib['id'] if 'id' in elem.attrib else False), type(id))
    #input()
    if (elem.tag == tag and str(elem.attrib['id']) == str(id) if 'id' in elem.attrib else False):
        #print('Founded!')
        #input()
        return elem
    else:
        return None

def deep_attrib_replace(elem: ET.Element, replace_tag: str, attr: dict, attr_replace: str, replace: tuple, tag: str='selector'):
    """Рекурсивная замена значений аттрибутов тэгов"""
    for i in elem:
        deep_attrib_replace(i, replace_tag, attr, attr_replace, replace, tag)
    check_attrib = True
    for k in attr:
        if k in elem.attrib and elem.attrib[k] != attr[k]:
            check_attrib = False
            break
    if replace_tag == elem.tag and attr_replace in elem.attrib:
        if check_attrib:
            if elem.attrib[attr_replace] == str(replace[0]):
                elem.attrib[attr_replace] = str(replace[1])

#ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ ПАРСИНГА КЛЮЧЕЙ ПЕРЕМЕННЫХ
def get_key_from_ET(elem: ET.Element) -> Iterable:
    """Получение КЛЮЧА переменной из XML-элемента"""
    if elem.tag == 'inputflow':
        return (elem.tag,
                int(elem.attrib['object']),
                int(elem.attrib['flow']),
                int(elem.attrib['interval']),
        )
    elif elem.tag == 'resultflow':
        return (elem.tag,
                int(elem.attrib['object']),
                int(elem.attrib['flow']),
                int(elem.attrib['interval']),
        )
    elif elem.tag == 'process_all':
        return (elem.tag,
                int(elem.attrib['object']),
                int(elem.attrib['interval']),
        )
    elif elem.tag == 'to_process':
        return (elem.tag,
                int(elem.attrib['object']),
                int(elem.attrib['flow']),
                int(elem.attrib['tech']),
                int(elem.attrib['interval']),
        )
    elif elem.tag == 'process':
        return (elem.tag,
                int(elem.attrib['object']),
                int(elem.attrib['tech']),
                int(elem.attrib['interval']),
        )
    elif elem.tag == 'from_process':
        return (elem.tag,
                int(elem.attrib['object']),
                int(elem.attrib['flow']),
                int(elem.attrib['tech']),
                int(elem.attrib['interval']),
        )
    elif elem.tag == 'transport_all':
        return (elem.tag,
                int(elem.attrib['object']),
                int(elem.attrib['to_object']),
                int(elem.attrib['interval']),
        )
    elif elem.tag == 'to_transport':
        return (elem.tag,
                int(elem.attrib['object']),
                int(elem.attrib['to_object']),
                int(elem.attrib['flow']),
                int(elem.attrib['tech']),
                int(elem.attrib['interval']),
        )
    elif elem.tag == 'transport':
        return (elem.tag,
                int(elem.attrib['object']),
                int(elem.attrib['to_object']),
                int(elem.attrib['tech']),
                int(elem.attrib['interval']),
        )
    elif elem.tag == 'from_transport':
        return (elem.tag,
                int(elem.attrib['object']),
                int(elem.attrib['to_object']),
                int(elem.attrib['flow']),
                int(elem.attrib['tech']),
                int(elem.attrib['interval']),
        )
    elif elem.tag == 'storage':
        return (elem.tag,
                int(elem.attrib['object']),
                int(elem.attrib['flow']),
                int(elem.attrib['tech']),
                int(elem.attrib['interval']),
        )
    elif elem.tag == 'lost':
        return (elem.tag,
                int(elem.attrib['object']),
                int(elem.attrib['flow']),
                int(elem.attrib['interval']),
        )
    elif elem.tag == 'time':
        return (elem.tag,
                int(elem.attrib['interval']),
        )
    else:
        return (elem.tag)

def get_dict_from_key(key: Iterable) -> dict:
    """Возвращает словарь из значения ключа ПЕРЕМЕННОЙ"""
    attr = {'object':str(get_key_object(key)),
            'to_object':str(get_key_object2(key)),
            'flow':str(get_key_flow(key)),
            'tech':str(get_key_tech(key)),
            'interval':str(get_key_interval(key)),
    }
    #вычищаем аттрибуты со значениями "None"
    while "None" in attr.values():
        attr.pop(get_key(attr,"None"))
    return attr

def get_key_type(key: Iterable):
    """возвращает ТИП ключа ПЕРЕМЕННОЙ key"""
    if isinstance(key, str):
        return key
    else:
        return key[0]

def get_key_interval(key: Iterable):
    """возвращает ИНТЕРВАЛ ключа ПЕРЕМЕННОЙ key"""
    if get_key_type(key) in ['time']:
        return key[1]
    elif get_key_type(key) in ['process_all']:
        return key[2]
    elif get_key_type(key) in [  'inputflow',
                                 'process',
                                 'resultflow',
                                 'transport_all',
                                 'lost',
                                ]:
        return key[3]
    elif get_key_type(key) in [     'transport',
                                    'from_process',
                                    'to_process',
                                    'storage'
                                ]:
        return key[4]
    elif get_key_type(key) in [      'to_transport',
                                    'from_transport'
                                ]:
        return key[5]
    else:
        return None

def get_key_object(key: Iterable):
    """возвращает ОБЪЕКТ ключа ПЕРЕМЕННОЙ key"""
    if get_key_type(key) in [   'process_all',
                                'inputflow',
                                'process',
                                'resultflow',
                                'transport_all',
                                'lost',
                                'transport',
                                'from_process',
                                'to_process',
                                'storage',
                                'to_transport',
                                'from_transport',
                                'time'
                            ]:
        return key[1]
    else:
        return None

def get_key_object2(key: Iterable):
    """возвращает ВТОРОЙ ОБЪЕКТ ключа ПЕРЕМЕННОЙ key"""
    if get_key_type(key) in [   'transport',
                                'to_transport',
                                'from_transport',
                                'transport_all'
                            ]:
        return key[2]
    else:
        return None

def get_key_flow(key: Iterable):
    """возвращает ТИП ПОТОКА ключа ПЕРЕМЕННОЙ key"""
    if get_key_type(key) in [   #'transport',
                                'to_transport',
                                'from_transport'
                            ]:
        return key[3]
    elif get_key_type(key) in [ 'inputflow',
                                #'process',
                                'to_process',
                                'from_process',
                                'storage',
                                'lost',
                                'resultflow'
                                ]:
        return key[2]
    else:
        return None

def get_key_tech(key: Iterable):
    """возвращает ТЕХНОЛОГИЮ ключа ПЕРЕМЕННОЙ key"""
    if get_key_type(key) in ['to_transport',
                             'from_transport']:
        return key[4]
    elif get_key_type(key) in [ 'transport',
                                'to_process',
                                'from_process',
                                'storage']:
        return key[3]
    elif get_key_type(key) in ['process']:
        return key[2]
    else:
        return None

PDAConstraint = TypeVar('T', bound='PDAConstraint')
class PDAConstraint(object):
    """Класс ОГРАНИЧЕНИЕ"""
    def __init__(self: PDAConstraint, Sign: str='==') -> None:
        """конструктор класса ОГРАНИЧЕНИЕ"""
        super(PDAConstraint, self).__init__()
        self._ACoeffDict = {}
        self._Sign = Sign
        self._BValue = 0

    def _convert_coeff_key(self: PDAConstraint, ACoeffKey: Iterable) -> tuple:
        """Преобразует все "ключи" ПЕРЕМЕННЫХ в int, кроме типа ПЕРЕМЕННОЙ (0-позиция)"""
        if isinstance(ACoeffKey,str):
            return ACoeffKey
        ACoeffKey_ = list(ACoeffKey)
        for i in range(1, len(ACoeffKey_)):
            ACoeffKey_[i] = int(ACoeffKey_[i])
        return tuple(ACoeffKey_)

    def setACoeffDict(self: PDAConstraint, AcoeffDict: dict) -> None:
        """установка словаря коэффициентов при переменных в ОГРАНИЧЕНИИ"""
        self._ACoeffDict = AcoeffDict

    def getACoeffDict(self: PDAConstraint) -> dict:
        """получение словаря коэффициентов при переменных из ОГРАНИЧЕНИЯ"""
        return self._ACoeffDict

    def setCoeff(self: PDAConstraint, ACoeffKey: Iterable, ACoeffValue: float) -> None:
        """установка коэффициента при переменной с именем ACoeffKey в ОГРАНИЧЕНИЕ"""
        self._ACoeffDict[self._convert_coeff_key(ACoeffKey)] = ACoeffValue

    def getCoeff(self: PDAConstraint, ACoeffKey: Iterable) -> float:
        """получение коэффициента при переменной с именем ACoeffKey из ОГРАНИЧЕНИЯ"""
        if self._convert_coeff_key(ACoeffKey) in self._ACoeffDict:
            return self._ACoeffDict[self._convert_coeff_key(ACoeffKey)]
        else:
            return None

    def setSign(self: PDAConstraint, Sign: str) -> None:
        """установка знака Sign в ОГРАНИЧЕНИЕ"""
        self._Sign = Sign

    def getSign(self: PDAConstraint) -> str:
        """получение знака Sign из ОГРАНИЧЕНИЯ"""
        return self._Sign

    def setBValue(self: PDAConstraint, BValue: float) -> None:
        """установка значения BValue в ОГРАНИЧЕНИЕ"""
        self._BValue = BValue

    def getBValue(self: PDAConstraint) -> float:
        """получение значения BValue из ОГРАНИЧЕНИЯ"""
        return self._BValue

    def getAVector(self: PDAConstraint, VariablesDict: Mapping[Iterable,int]) -> Iterable[float]:
        """получение вектора А ОГРАНИЧЕНИЯ"""
        AVector = [0 for i in range(len(VariablesDict))]
        for i in iter(self._ACoeffDict):
            AVector[VariablesDict[i]] = self._ACoeffDict[i]
        return AVector

    def product_all(self: PDAConstraint, sign: float=1.0) -> None:
        """Перемножить все коэффициенты на sign"""
        for i in self._ACoeffDict:
            self._ACoeffDict[i] *= sign

    def line_combine(self: PDAConstraint, constr: PDAConstraint) -> PDAConstraint:
        """Линейная комбинация векторов ограничений (или целевой)"""
        new_constr = copy(self)
        for k, v in constr.getACoeffDict().items():
            if k in new_constr._ACoeffDict:
                new_constr._ACoeffDict[k] = new_constr._ACoeffDict[k] + v
            else:
                new_constr._ACoeffDict[k] = v
        return new_constr


PDAPlan = TypeVar('T', bound='PDAPlan')
class PDAPlan(object):
    """Класс ПЛАН"""
    def __init__(self, PlanDict: dict={}, ResultVariables=None, VariablesDict: dict=None):
        """Конструктор класса ПЛАН"""
        super(PDAPlan, self).__init__()
        self._PPlanDict = PlanDict
        if (ResultVariables) and (VariablesDict):
            for v in ResultVariables:
                vkey = get_key(VariablesDict, int(str(v.name).split('x_')[1]))
                vvalue = v.varValue
                self._PPlanDict[vkey] = vvalue

    def getPVector(self, VariablesDict: Mapping[Iterable,int]) -> Iterable[float]:
        """возвращает вектор-ПЛАН"""
        PVector = [0 for i in range(len(VariablesDict))]
        for i in self._PPlanDict:
            PVector[VariablesDict[i]] = self._PPlanDict[i]
        return PVector

    def getPDict(self, with_zeroe_values=True) -> dict:
        """возвращает ПЛАН в виде словаря"""
        if not with_zeroe_values:
            return {k:v for k, v in self._PPlanDict.items() if v != 0}
        return copy(self._PPlanDict)

    @property
    def SumValues(self) -> float:
        """возвращает сумму элементов ПЛАНА"""
        return sum(self._PPlanDict.values())

    #@property
    def LineCombineValue(self, constr: PDAConstraint):
        res = 0
        d = constr.getACoeffDict()
        for k in d:
            if k in self._PPlanDict:
                res += d[k]*self._PPlanDict[k]
        return res

    def _Lister(self, func: Callable[[Iterable],Any]) -> dict:
        """возвращает ВСЕ ТИПЫ переменных в ПЛАНЕ"""
        PlanDict = set(map(func, self._PPlanDict)) #используем set для исключения повторений
        #удаление None из списка
        if None in PlanDict:
            PlanDict.remove(None)
        return PlanDict

    @property
    def TypesList(self) -> dict:
        """возвращает ВСЕ ТИПЫ переменных в ПЛАНЕ"""
        return self._Lister(get_key_type)

    @property
    def ObjectsList(self) -> dict:
        """возвращает ВСЕ ОБЪЕКТЫ переменных в ПЛАНЕ"""
        return self._Lister(get_key_object)

    @property
    def Objects2List(self) -> dict:
        """возвращает ВСЕ ОБЪЕКТЫ2 переменных в ПЛАНЕ"""
        return self._Lister(get_key_object2)

    @property
    def FlowsList(self) -> dict:
        """возвращает ВСЕ ПОТОКИ переменных в ПЛАНЕ"""
        return self._Lister(get_key_flow)

    @property
    def IntervalsList(self) -> dict:
        """возвращает ВСЕ ИНТЕРВАЛЫ переменных в ПЛАНЕ"""
        return self._Lister(get_key_interval)

    @property
    def TechsList(self) -> dict:
        """возвращает ВСЕ ТЕХНОЛОГИИ переменных в ПЛАНЕ"""
        return self._Lister(get_key_tech)

    def _Selector(self: PDAPlan, func: Callable[[Iterable],Any], Values: list=None) -> PDAPlan:
        """возвращает новый объект-ПЛАН с выбранными СВОЙСТВАМИ переменных (ОБОБЩЕННЫЙ СЕЛЕКТОР)"""
        if not Values:
            return PDAPlan(self._PPlanDict)
        else:
            PlanDict = {}
            for k,v in self._PPlanDict.items():
                if func(k) in Values: #здесь происходит проверка на необходимость добавлять в новый список
                    PlanDict[k] = v
            return PDAPlan(PlanDict)

    def getTypes(self: PDAPlan, Values: Iterable) -> PDAPlan:
        """возвращает новый объект-ПЛАН с выбранными ТИПАМИ переменных"""
        return self._Selector(get_key_type, Values)

    def getObjects(self: PDAPlan, Values: Iterable) -> PDAPlan:
        """возвращает новый объект-ПЛАН с выбранными ОБЪЕКТАМИ переменных"""
        return self._Selector(get_key_object, Values)

    def getObjects2(self: PDAPlan, Values: Iterable) -> PDAPlan:
        """возвращает новый объект-ПЛАН с выбранными ВТОРЫМИ ОБЪЕКТАМИ переменных (для передачи потоков)"""
        return self._Selector(get_key_object2, Values)

    def getFlows(self: PDAPlan, Values: Iterable) -> PDAPlan:
        """возвращает новый объект-ПЛАН с выбранными ПОТОКАМИ переменных"""
        return self._Selector(get_key_flow, Values)

    def getIntervals(self: PDAPlan, Values: Iterable) -> PDAPlan:
        """возвращает новый объект-ПЛАН с выбранными ИНТЕРВАЛАМИ переменных"""
        return self._Selector(get_key_interval, Values)

    def getTechs(self: PDAPlan, Values: Iterable) -> PDAPlan:
        """возвращает новый объект-ПЛАН с выбранными ТЕХНОЛОГИЯМИ переменных"""
        return self._Selector(get_key_tech, Values)



PDATask = TypeVar('T', bound='PDATask')
class PDATask(object):
    """Класс ЗАДАЧА
    Основной класс библиотеки
    """

    def __str__(self) -> str:
        """строковое представление ЗАДАЧИ (краткая информация)"""
        res = 'TASK info:' + '\n'
        res += '\tFILENAME: ' + str(self.filename) + '\n'
        res += '\tSIZE: ' + str(self.variablesCount) + ' x ' + str(self.constraintsCount)
        return res

    def __init__(self, Filename: str=None, XML: ET=None, Name = None, TimeLimit: float=None) -> None:
        """конструктор класса ЗАДАЧА"""
        self.Name = str(Name) if Name else 'Noname_task'
        #
        self._Filename = Filename # str
        self._Tree = None # XML
        #
        self._Variables = {} # dict
        self._Objective = PDAConstraint() # PDAConstraint
        self._Constraints = [] # List[PDAConstraint]
        #
        self._Plan = None # PDAPlan
        self._Report = None # XML

        self.TimeLimit = TimeLimit

        if Filename:
            self.fromFile(Filename=Filename)
        elif XML:
            tree = deepcopy(XML)
            self.fromXML(XML=tree)

    def setObjective(self, Objective: PDAConstraint) -> None:
        """установка целевой функции в ЗАДАЧУ"""
        self._Objective = Objective

    def addConstraint(self, Constraint: PDAConstraint) -> None:
        """добавление ОГРАНИЧЕНИЯ в ЗАДАЧУ"""
        self._Constraints.append(Constraint)

    def collectVariables(self) -> None:
        """формирование ассоциативных переменных из ЗАДАЧИ (из self._Objective + self.Constarints)"""
        # нет необходимости собирать дополнительные ПЕРЕМЕННЫЕ из свободных СЕЛЕКТОРОВ
        self._Variables = copy(self._Objective.getACoeffDict())
        for constr in self._Constraints:
            self._Variables.update(constr.getACoeffDict())

        # присвоение номеров ПЕРЕМЕННЫМ
        num = 0
        for i in iter(self._Variables):
            self._Variables[i] = num
            num += 1

    @property
    def filename(self) -> str:
        """Выдача имени файла ЗАДАЧИ"""
        return self._Filename

    @property
    def AMatrix(self) -> Iterable[Iterable[float]]:
        """формирование и выдача матрицы А"""
        return [constr.getAVector(self._Variables) for constr in self._Constraints]

    @property
    def BVector(self) -> Iterable[float]:
        """выдача вектора B (вектор ресурсов)"""
        return [b.getBValue() for b in self._Constraints]

    @property
    def CVector(self) -> Iterable[float]:
        """выдача вектора C (целевая функция)"""
        return self._Objective.getAVector(self._Variables)

    @property
    def PVector(self) -> Iterable[float]:
        """выдача вектора P (план)"""
        if not self._Plan:
            self.solve()
        return self._Plan.getPVector(self._Variables)

    @property
    def PDict(self) -> dict:
        """выдача словаря-плана"""
        if not self._Plan:
            self.solve()
        return self._Plan.getPDict()

    @property
    def ObjectiveValue(self):
        """возвращает значение ЦЕЛЕВОЙ ФУНКЦИИ"""
        return self.getLineCombineValue(LineCombine=self._Objective)


    @property
    def PLAN(self) -> PDAPlan:
        """выдача ПЛАНА (решение задачи и выдача плана - если не решалась)"""
        if not self._Plan:
            self.solve()
        return self._Plan

    @property
    def isMaximize(self) -> bool:
        """выдача True, если целевая функция стремится в максимум"""
        return (self._Objective.getSign() == 'MAX')

    @property
    def isMinimize(self) -> bool:
        """выдача True, если целевая функция стремится в минимум"""
        return (self._Objective.getSign() == 'MIN')

    @property
    def variablesCount(self) -> int:
        """число ПЕРЕМЕННЫХ ЗАДАЧИ"""
        return len(self._Variables)

    @property
    def constraintsCount(self) -> int:
        """число ОГРАНИЧЕНИЙ ЗАДАЧИ"""
        return len(self._Constraints)

    @property
    def REPORT(self):
        if not self._Report and self.PLAN:
            self._Report = self.getXMLReport()
            self.BPMN_diagram(NotDiagram=True)
        return self._Report
    
    #@property
    def BPMN_diagram(self, NotDiagram=False, NotDraw=True):
        new_tree_report_full = deepcopy(self._Tree)
        new_root_report_full = new_tree_report_full.getroot()
        new_root_report_full.append(self.REPORT.getroot())
        indent(new_root_report_full)
        bpmn_diagram_ET,_,techchains = make_techchains_bpmn_from_report(XMLReport=new_tree_report_full, NotDraw=NotDraw, task_name=self.Name, NotDiagram = NotDiagram)
        
        report_techchains = ET.Element('techchains')
        for techchain in techchains:
            chain = ET.Element('chain', {'interval':techchain[0].attrib['interval']})
            for el in techchain:
                chain.append(el)
            report_techchains.append(chain)
        report = self._Report.getroot()
        report.append(report_techchains)
        return bpmn_diagram_ET

    def getLineCombine(self, id) -> PDAConstraint:
        """Получение ЛИНЕЙНОЙ КОМБИНАЦИИ СЕЛЕКТОРА с id"""
        root = self._Tree.getroot().find('task').find('selectors')
        for fsel in root.findall('selector'):
            sel = iterfind(fsel, id) # вложенный поиск СЕЛЕКТОРА с id == sel_id
            if sel:
                break
        if sel is None:
            print(sel, id); input()
        if sel and 'sign' in sel.attrib:
            sel_sign = float(sel.attrib['sign'])
        else:
            sel_sign = 1.0
        #print(sel)
        a_tmp = self._deep_line_combine(sel) # сбор вложенных линейных комбинаций
        a_tmp.product_all(sel_sign) # перемножить все коэффициенты на sign
        return a_tmp

    def getLineCombineValue(self, id: int=None, LineCombine: PDAConstraint=None) -> float:
        """Получение ЗНАЧЕНИЯ LineCombine или ЛИНЕЙНОЙ КОМБИНАЦИИ по СЕЛЕКТОРУ id"""
        if LineCombine:
            return self.PLAN.LineCombineValue(LineCombine)
        elif id:
            return self.PLAN.LineCombineValue(self.getLineCombine(id))
        else:
            return None


    def buildIOFlows(self) -> None:
        """формирование ОГРАНИЧЕНИЙ входов и выходов системы"""
        root = self._Tree.getroot().find('task')
        a_new = PDAConstraint()
        a_new.setCoeff(('price_all'), -1) # дополнительная переменная
        for k in root.findall('struct'):
            for p in root.find('flows').findall('type'):
                for i in k.findall('elem'):
                    if 'output_' + str(p.attrib['id']) in i.attrib:
                        a_new.setCoeff(
                            (
                                'resultflow',
                                i.attrib['id'],
                                p.attrib['id'],
                                k.attrib['id']
                            ),
                            float(p.attrib['price'])
                        )
                        if i.attrib['output_' + str(p.attrib['id'])] != "":
                            a_new2 = PDAConstraint('<=')
                            a_new2.setCoeff(
                                (
                                    'resultflow',
                                    i.attrib['id'],
                                    p.attrib['id'],
                                    k.attrib['id']
                                ),
                                1
                            )
                            a_new2.setBValue(
                                float(i.attrib['output_'
                                + str(p.attrib['id'])])
                            )
                            self.addConstraint(a_new2)
        self.addConstraint(a_new)

        a_new = PDAConstraint()
        a_new.setCoeff(('loss_all'), -1) # дополнительная переменная
        for k in root.findall('struct'):
            for p in root.find('flows').findall('type'):
                for ii in k.findall('elem'):
                    a_new.setCoeff(
                        (
                            'lost',
                            ii.attrib['id'],
                            p.attrib['id'],
                            k.attrib['id']
                        ),
                        float(p.attrib['loss'])
                    )
        self.addConstraint(a_new)

        a_new = PDAConstraint()
        a_new.setCoeff(('rashod_all'), -1) # дополнительная переменная
        for k in root.findall('struct'):
            for p in root.find('flows').findall('type'):
                for i in k.findall('elem'):
                    for j in k.findall("./link/[@id1='"
                        + str(i.attrib['id']) + "']"):
                        for per in root.find('transport').findall('type'):
                            if 'transport_' + str(per.attrib['id']) in j.attrib:
                                for resurs in per.find('input').findall('type'):
                                    if resurs.attrib['id'] == p.attrib['id']:
                                        a_new.setCoeff(
                                            (
                                                'to_transport',
                                                i.attrib['id'],
                                                j.attrib['id2'],
                                                p.attrib['id'],
                                                per.attrib['id'],
                                                k.attrib['id']
                                            ),
                                            float(p.attrib['rashod'])
                                        )
                    for j in k.findall("./link/[@id2='"
                        + str(i.attrib['id']) + "']"):
                        for per in root.find('transport').findall('type'):
                            if 'transport_' + str(per.attrib['id']) in j.attrib:
                                for resurs in per.find('input').findall('type'):
                                    if resurs.attrib['id'] == p.attrib['id']:
                                        a_new.setCoeff(
                                            (
                                                'to_transport',
                                                i.attrib['id'],
                                                j.attrib['id1'],
                                                p.attrib['id'],
                                                per.attrib['id'],
                                                k.attrib['id']
                                            ),
                                            float(p.attrib['rashod'])
                                        )

                    for o in root.find('process').findall('type'):
                        if 'process_' + str(o.attrib['id']) in i.attrib:
                            for resurs in o.find('input').findall('type'):
                                if resurs.attrib['id'] == p.attrib['id']:
                                    a_new.setCoeff(
                                        (
                                            'to_process',
                                            i.attrib['id'],
                                            p.attrib['id'],
                                            o.attrib['id'],
                                            k.attrib['id']
                                        ),
                                        float(p.attrib['rashod'])
                                    )
        self.addConstraint(a_new)

    def _deep_line_combine(self: PDATask, elem: ET.Element) -> PDAConstraint:
        """Рекурсивный сбор вложенных линейных комбинаций СЕЛЕКТОРОВ"""
        c_new = PDAConstraint()
        for i in elem:
            c_tmp = PDAConstraint()
            if 'sign' in i.attrib:
                sign = float(i.attrib['sign'])
            else:
                sign = 1.0
            if i.tag != 'selector': # игнорируем тэг вложенности
                new_tuple = get_key_from_ET(i)
                c_tmp.setCoeff(new_tuple, sign)
            else:
                c_tmp = self._deep_line_combine(i)
                c_tmp.product_all(sign) # перемножить все коэффициенты на sign
            c_new = c_new.line_combine(c_tmp)
        return c_new

    def buildCriterion(self: PDATask) -> None:
        """Формирование ЦЕЛЕВОЙ ФУНКЦИИ из СЕЛЕКТОРОВ"""
        root = self._Tree.getroot().find('task')
        criterion = root.find('criterion')
        c_new = PDAConstraint(criterion.attrib['sign'])
        # рекурсивный обход дерева СЕЛЕКТОРОВ и формирование итоговых коэффициентов
        for selector in criterion.findall('selector'):
            sel_id = selector.attrib['id']
            c_new = c_new.line_combine(self.getLineCombine(sel_id))
        self.setObjective(c_new)

    def buildConstraints(self: PDATask) -> None:
        """Формирование ПОЛЬЗОВАТЕЛЬСКИХ ОГРАНИЧЕНИЙ из СЕЛЕКТОРОВ"""
        root = self._Tree.getroot().find('task')
        constraints = root.find('constraints')
        for constr in constraints.findall('constraint'):
            sign = constr.attrib['sign']
            if sign == 'less':
                sign = '<='
            elif sign == 'equally':
                sign = '=='
            elif sign == 'more':
                sign = '>='
            else:
                raise Exception('SIGN!')
            a_new = PDAConstraint(sign)
            a_new.setBValue(float(constr.attrib['value']))
            # рекурсивный обход дерева СЕЛЕКТОРОВ и формирование итоговых коэффициентов
            for selector in constr.findall('selector'):
                sel_id = selector.attrib['id']
                a_new = a_new.line_combine(self.getLineCombine(sel_id))
            self.addConstraint(a_new)

    def buildTechnolog(self: PDATask) -> None:
        """формирование ТЕХНОЛОГИЧЕСКИХ ОГРАНИЧЕНИЙ"""
        root = self._Tree.getroot().find('task')
        for k in root.findall('struct'):
            for p in root.find('flows').findall('type'):
                for i in k.findall('elem'):
                    a_new = PDAConstraint()
                    for j in k.findall("./link/[@id1='"
                        + str(i.attrib['id']) + "']"):
                        for per in root.find('transport').findall('type'):
                            if 'transport_' + str(per.attrib['id']) in j.attrib:
                                for resurs in per.find('input').findall('type'):
                                    if resurs.attrib['id'] == p.attrib['id']:
                                        a_new.setCoeff(
                                            (
                                                'to_transport',
                                                i.attrib['id'],
                                                j.attrib['id2'],
                                                p.attrib['id'],
                                                per.attrib['id'],
                                                k.attrib['id']
                                            ),
                                            1
                                        )
                    for j in k.findall("./link/[@id2='"
                        + str(i.attrib['id']) + "']"):
                        for per in root.find('transport').findall('type'):
                            if 'transport_' + str(per.attrib['id']) in j.attrib:
                                for resurs in per.find('input').findall('type'):
                                    if resurs.attrib['id'] == p.attrib['id']:
                                        a_new.setCoeff(
                                            (
                                                'to_transport',
                                                i.attrib['id'],
                                                j.attrib['id1'],
                                                p.attrib['id'],
                                                per.attrib['id'],
                                                k.attrib['id']
                                            ),
                                            1
                                        )

                    for j in k.findall("./link/[@id1='"
                        + str(i.attrib['id']) + "']"):
                        for per in root.find('transport').findall('type'):
                            if 'transport_' + str(per.attrib['id']) in j.attrib:
                                for resurs in per.find('output').findall('type'):
                                    if resurs.attrib['id'] == p.attrib['id']:
                                        a_new.setCoeff(
                                            (
                                                'from_transport',
                                                j.attrib['id2'],
                                                i.attrib['id'],
                                                p.attrib['id'],
                                                per.attrib['id'],
                                                k.attrib['id']
                                            ),
                                            -1
                                        )

                    for j in k.findall("./link/[@id2='"
                        + str(i.attrib['id']) + "']"):
                        for per in root.find('transport').findall('type'):
                            if 'transport_' + str(per.attrib['id']) in j.attrib:
                                for resurs in per.find('output').findall('type'):
                                    if resurs.attrib['id'] == p.attrib['id']:
                                        a_new.setCoeff(
                                            (
                                                'from_transport',
                                                j.attrib['id1'],
                                                i.attrib['id'],
                                                p.attrib['id'],
                                                per.attrib['id'],
                                                k.attrib['id']
                                            ),
                                            -1
                                        )

                    for s in root.find('storage').findall('type'):
                        if 'storage_' + str(s.attrib['id']) in i.attrib:
                            for resurs in s.find('input').findall('type'):
                                if resurs.attrib['id'] == p.attrib['id']:
                                    a_new.setCoeff(
                                        (
                                            'storage',
                                            i.attrib['id'],
                                            p.attrib['id'],
                                            s.attrib['id'],
                                            k.attrib['id']
                                        ),
                                        1
                                    )

                    for k_pred in root.findall('struct'):  # хранение на предыдущем интервале
                        if k_pred.attrib['id'] == str(int(k.attrib['id']) - 1):
                            for s in root.find('storage').findall('type'):
                                if 'storage_' + str(s.attrib['id']) in i.attrib:
                                    for resurs in s.find('input').findall('type'):
                                        if resurs.attrib['id'] == p.attrib['id']:
                                            a_new.setCoeff(
                                                (
                                                    'storage',
                                                    i.attrib['id'],
                                                    p.attrib['id'],
                                                    s.attrib['id'],
                                                    k_pred.attrib['id']
                                                ),
                                                -1
                                            )

                    for o in root.find('process').findall('type'):
                        if 'process_' + str(o.attrib['id']) in i.attrib:
                            for resurs in o.find('input').findall('type'):
                                if resurs.attrib['id'] == p.attrib['id']:
                                    a_new.setCoeff(
                                        (
                                            'to_process',
                                            i.attrib['id'],
                                            p.attrib['id'],
                                            o.attrib['id'],
                                            k.attrib['id']
                                        ),
                                        1
                                    )

                    for o in root.find('process').findall('type'):
                        if 'process_' + str(o.attrib['id']) in i.attrib:
                            for resurs in o.find('output').findall('type'):
                                if resurs.attrib['id'] == p.attrib['id']:
                                    a_new.setCoeff(
                                        (
                                            'from_process',
                                            i.attrib['id'],
                                            p.attrib['id'],
                                            o.attrib['id'],
                                            k.attrib['id']
                                        ),
                                        -1
                                    )

                    a_new.setCoeff(
                        (
                            'lost',
                            i.attrib['id'],
                            p.attrib['id'],
                            k.attrib['id']
                        ),
                        1
                    )

                    for elem in k.findall("./elem/[@id='"
                        + str(i.attrib['id']) + "']"):
                        if 'input_' + str(p.attrib['id']) in elem.attrib:
                            if elem.attrib["input_" + str(p.attrib['id'])] != "":
                                # если имеется входной ресурс, то добавляем ограничение на выходной поток
                                a_new2 = PDAConstraint()
                                a_new2.setBValue(
                                    float(
                                        elem.attrib["input_"
                                        + str(p.attrib['id'])]
                                    )
                                )
                                a_new2.setCoeff(
                                    (
                                        'inputflow',
                                        i.attrib['id'],
                                        p.attrib['id'],
                                        k.attrib['id']
                                    ),
                                    1
                                )
                                self.addConstraint(a_new2)
                            a_new.setCoeff(
                                (
                                    'inputflow',
                                    i.attrib['id'],
                                    p.attrib['id'],
                                    k.attrib['id']
                                ),
                                -1
                            )

                    for elem in k.findall("./elem/[@id='"
                        + str(i.attrib['id']) + "']"):
                        if 'output_' + str(p.attrib['id']) in elem.attrib:
                            if elem.attrib["output_" + str(p.attrib['id'])] != "":
                                # если имеется входной ресурс, то добавляем ограничение на выходной поток
                                a_new2 = PDAConstraint()
                                a_new2.setBValue(
                                    float(
                                        elem.attrib["output_"
                                        + str(p.attrib['id'])]
                                    )
                                )
                                a_new2.setCoeff(
                                    (
                                        'resultflow',
                                        i.attrib['id'],
                                        p.attrib['id'],
                                        k.attrib['id']
                                    ),
                                    1
                                )
                                self.addConstraint(a_new2)
                            a_new.setCoeff(
                                (
                                    'resultflow',
                                    i.attrib['id'],
                                    p.attrib['id'],
                                    k.attrib['id']
                                ),
                                1
                            )

                    self.addConstraint(a_new)

        # Формирование связей времени/объема в технологиях обработки
        for k in root.findall('struct'):
            for i in k.findall('elem'):
                for o in root.find('process').findall('type'):
                    if 'process_' + str(o.attrib['id']) in i.attrib:
                        for resurs in o.find('input').findall('type'):
                            a_new = PDAConstraint()
                            a_new.setCoeff(
                                (
                                    'process',
                                    i.attrib['id'],
                                    o.attrib['id'],
                                    k.attrib['id']
                                ),
                                float(resurs.attrib['size'])
                            )
                            a_new.setCoeff(
                                (
                                    'to_process',
                                    i.attrib['id'],
                                    resurs.attrib['id'],
                                    o.attrib['id'],
                                    k.attrib['id']
                                ),
                                -1*float(o.attrib['time'])
                            )
                            self.addConstraint(a_new)
                        for resurs2 in o.find('output').findall('type'):
                            a_new = PDAConstraint()
                            a_new.setCoeff(
                                (
                                    'process',
                                    i.attrib['id'],
                                    o.attrib['id'],
                                    k.attrib['id']
                                ),
                                float(resurs2.attrib['size'])
                            )
                            a_new.setCoeff(
                                (
                                    'from_process',
                                    i.attrib['id'],
                                    resurs2.attrib['id'],
                                    o.attrib['id'],
                                    k.attrib['id']
                                ),
                                -1*float(o.attrib['time'])
                            )
                            self.addConstraint(a_new)

        # Формирование связей времени/объема в технологиях передачи
        for k in root.findall('struct'):
            for j in k.findall('link'):
                for per in root.find('transport').findall('type'):
                    if 'transport_' + str(per.attrib['id']) in j.attrib:
                        # прямая связь
                        for resurs in per.find('input').findall('type'):
                            a_new = PDAConstraint()
                            a_new.setCoeff(
                                (
                                    'transport',
                                    j.attrib['id1'],
                                    j.attrib['id2'],
                                    per.attrib['id'],
                                    k.attrib['id']
                                ),
                                float(resurs.attrib['size'])
                            )
                            a_new.setCoeff(
                                (
                                    'to_transport',
                                    j.attrib['id1'],
                                    j.attrib['id2'],
                                    resurs.attrib['id'],
                                    per.attrib['id'],
                                    k.attrib['id']
                                ),
                                -1*float(per.attrib['time'])
                            )
                            self.addConstraint(a_new)
                        for resurs2 in per.find('output').findall('type'):
                            a_new = PDAConstraint()
                            a_new.setCoeff(
                                (
                                    'transport',
                                    j.attrib['id1'],
                                    j.attrib['id2'],
                                    per.attrib['id'],
                                    k.attrib['id']
                                ),
                                float(resurs2.attrib['size'])
                            )
                            a_new.setCoeff(
                                (
                                    'from_transport',
                                    j.attrib['id1'],
                                    j.attrib['id2'],
                                    resurs2.attrib['id'],
                                    per.attrib['id'],
                                    k.attrib['id']
                                ),
                                -1*float(per.attrib['time'])
                            )
                            self.addConstraint(a_new)
                        # обратная связь
                        for resurs in per.find('input').findall('type'):
                            a_new = PDAConstraint()
                            a_new.setCoeff(
                                (
                                    'transport',
                                    j.attrib['id2'],
                                    j.attrib['id1'],
                                    per.attrib['id'],
                                    k.attrib['id']
                                ),
                                float(resurs.attrib['size'])
                            )
                            a_new.setCoeff(
                                (
                                    'to_transport',
                                    j.attrib['id2'],
                                    j.attrib['id1'],
                                    resurs.attrib['id'],
                                    per.attrib['id'],
                                    k.attrib['id']
                                ),
                                -1*float(per.attrib['time'])
                            )
                            self.addConstraint(a_new)
                        for resurs2 in per.find('output').findall('type'):
                            a_new = PDAConstraint()
                            a_new.setCoeff(
                                (
                                    'transport',
                                    j.attrib['id2'],
                                    j.attrib['id1'],
                                    per.attrib['id'],
                                    k.attrib['id']
                                ),
                                float(resurs2.attrib['size'])
                            )
                            a_new.setCoeff(
                                (
                                    'from_transport',
                                    j.attrib['id2'],
                                    j.attrib['id1'],
                                    resurs2.attrib['id'],
                                    per.attrib['id'],
                                    k.attrib['id']
                                ),
                                -1*float(per.attrib['time'])
                            )
                            self.addConstraint(a_new)
    # Формирование связей времени/объема в технологиях хранения - в разработке!

    def buildTechnique(self: PDATask) -> None:
        """формирование ТЕХНИЧЕСКИХ ОГРАНИЧЕНИЙ"""
        root = self._Tree.getroot().find('task')
        for k in root.findall('struct'):
            for i in k.findall('elem'):
                for s in root.find('storage').findall('type'):
                    if 'storage_' + str(s.attrib['id']) in i.attrib:
                        a_new = PDAConstraint('<=')
                        for resurs in s.find('input').findall('type'):
                            a_new.setCoeff(
                                (
                                    'storage',
                                    i.attrib['id'],
                                    resurs.attrib['id'],
                                    s.attrib['id'],
                                    k.attrib['id']
                                ),
                                1
                            )
                        if i.attrib['storage_' + str(s.attrib['id'])] != "":
                            a_new.setBValue(
                                float(
                                    i.attrib['storage_' + str(s.attrib['id'])]
                                )
                            )

                        self.addConstraint(a_new)

                # добавляем дополнительную переменную process_all и завязываем на нее все технологии обработки на узле
                a_new = PDAConstraint()
                for o in root.find('process').findall('type'):
                    if 'process_' + str(o.attrib['id']) in i.attrib:
                        a_new.setCoeff(
                            (
                                'process',
                                i.attrib['id'],
                                o.attrib['id'],
                                k.attrib['id']
                            ),
                            1
                        )
                a_new.setCoeff(
                    (
                        'process_all',
                        i.attrib['id'],
                        k.attrib['id']
                    ),
                    -1
                )

                self.addConstraint(a_new)

                # ограничиваем переменную process_all (не превышение времени интервала)
                a_new = PDAConstraint('<=')
                a_new.setCoeff(
                    (
                        'process_all',
                        i.attrib['id'],
                        k.attrib['id']
                    ),
                    1
                )
                # если время интервала задано, то формируем BValue
                if 'time' in k.attrib and k.attrib['time'] != "":
                    a_new2 = PDAConstraint()
                    a_new2.setCoeff(
                        (
                            'time',
                            k.attrib['id']
                        ),
                        1
                    )
                    a_new2.setBValue(
                        float(k.attrib['time'])
                    )
                    self.addConstraint(a_new2)
                a_new.setCoeff(
                    (
                        'time',
                        k.attrib['id']
                    ),
                    -1
                )

                self.addConstraint(a_new)

            # ограничиваем передачу в рамках одного двухстороннего канала передачи
            for i in k.findall('link'):
                a_new = PDAConstraint()
                # добавляем дополнительную переменную transport_all и завязываем на нее все технологии передачи на канале
                for per in root.find('transport').findall('type'):
                    if 'transport_' + str(per.attrib['id']) in i.attrib:
                        for resurs in per.find('input').findall('type'):
                            a_new.setCoeff(
                                (
                                    'transport',
                                    i.attrib['id1'],
                                    i.attrib['id2'],
                                    per.attrib['id'],
                                    k.attrib['id']
                                ),
                                1
                            )
                a_new.setCoeff(
                    (
                        'transport_all',
                        i.attrib['id1'],
                        i.attrib['id2'],
                        k.attrib['id']
                    ),
                    -1
                )

                self.addConstraint(a_new)

                a_new = PDAConstraint()
                for per in root.find('transport').findall('type'):
                    if 'transport_' + str(per.attrib['id']) in i.attrib:
                        for resurs in per.find('input').findall('type'):
                            a_new.setCoeff(
                                (
                                    'transport',
                                    i.attrib['id2'],
                                    i.attrib['id1'],
                                    per.attrib['id'],
                                    k.attrib['id']
                                ),
                                1
                            )
                a_new.setCoeff(
                    (
                        'transport_all',
                        i.attrib['id2'],
                        i.attrib['id1'],
                        k.attrib['id']
                    ),
                    -1
                )

                self.addConstraint(a_new)

                # ограничиваем переменную transport_all (не превышение времени интервала)
                a_new = PDAConstraint('<=')
                a_new.setCoeff(
                    (
                        'transport_all',
                        i.attrib['id1'],
                        i.attrib['id2'],
                        k.attrib['id']
                    ),
                    1
                )
                a_new.setCoeff(
                    (
                        'transport_all',
                        i.attrib['id2'],
                        i.attrib['id1'],
                        k.attrib['id']
                    ),
                    1
                )
                # если время интервала задано, то формируем BValue
                if 'time' in k.attrib and k.attrib['time'] != "":
                    a_new2 = PDAConstraint()
                    a_new2.setCoeff(
                        (
                            'time',
                            k.attrib['id']
                        ),
                        1
                    )
                    a_new2.setBValue(
                        float(k.attrib['time'])
                    )
                    self.addConstraint(a_new2)
                a_new.setCoeff(
                    (
                        'time',
                        k.attrib['id']
                    ),
                    -1
                )

                self.addConstraint(a_new)

    def fromFile(self: PDATask, Filename: str) -> None:
        """формирование ЗАДАЧИ из XML-файла"""
        self.fromXML(ET.parse(Filename))
        self._Filename = Filename

    def toFile(self: PDATask, Filename = None, just_task = False) -> bool:
        """сохранение ЗАДАЧИ в XML-файл"""
        if not just_task:
            self._Tree.getroot().append(self.REPORT.getroot())
        indent(self._Tree.getroot())
        if Filename:
            return self._Tree.write(Filename)
        else:
            if self._Report:
                return self._Tree.write(self.Name + '_report.xml')
            else:
                return self._Tree.write(self.Name + '.xml')

    def fromXML(self: PDATask, XML: ET) -> None:
        """формирование ЗАДАЧИ из XML (Etree)"""
        self._Filename = 'Generated from XML'
        self._Tree = deepcopy(XML)
        root = self._Tree.getroot()

        # Разбираем * в номерах индексов
        def check_stars():
            '''Проверка на наличие "*"'''
            for selector in root.find('task/selectors'):
                for variable in selector:
                    if "*" in variable.attrib.values():
                        return True
            return False
        def make_stars():
            #global have_stars
            #have_stars = False
            # функции генерации переменных
            def get_intervals():
                return sorted(set([elem.attrib['id'] for elem in root.findall('task/struct')]))
            def get_flows():
                return sorted(set([elem.attrib['id'] for elem in root.findall('task/flows/type')]))
            def get_objects():
                return sorted(set([elem.attrib['id'] for elem in root.findall('task/struct/elem')]))
            def get_to_objects():
                return sorted(set([elem.attrib['id1'] for elem in root.findall('task/struct/link')] + \
                        [elem.attrib['id2'] for elem in root.findall('task/struct/link')]))
            def get_techs():
                return sorted(set([elem.attrib['id'] for elem in root.findall('task/process/type')] + \
                        [elem.attrib['id'] for elem in root.findall('task/transport/type')] + \
                        [elem.attrib['id'] for elem in root.findall('task/storage/type')]
                        ))
            
            def get_variables_from_stars(variable):
                '''Получение переборных значений для указанного тэга где "*"'''
                star_tags = [k for k,v in variable.attrib.items() if v == "*"]  # Список тэгов, которые надо распаковать ("*")
                
                # При рекурсивном вызове могут быть недопустимые сочетания индексов тэгов, нужно их проверить
                variable_for_check = get_key_from_ET(variable) if not star_tags else ()
                if variable_for_check not in self._Variables and not star_tags: # переменная бракуется, если она без "звезд" и ее нет среди переменных задачи
                    return []
                
                # Если нет звёздочек, возвращаем переменную как есть
                if not star_tags:
                    return [variable]
                else:
                    pass
                    #global have_stars
                    #have_stars = True

                variables_from_stars = []
                # Порядок проверок важен, т.к. существуют зависимости внутри интервалов и т.п., не все переменные простым перебором существуют
                if "interval" in star_tags:
                    for interval in get_intervals():
                        new_variable = deepcopy(variable)
                        new_variable.attrib["interval"] = interval
                        new_star_variables = get_variables_from_stars(new_variable)
                        if new_star_variables:
                            variables_from_stars.extend(new_star_variables)
                elif "flow" in star_tags:
                    for flow in get_flows():
                        new_variable = deepcopy(variable)
                        new_variable.attrib["flow"] = flow
                        new_star_variables = get_variables_from_stars(new_variable)
                        if new_star_variables:
                            variables_from_stars.extend(new_star_variables)
                elif "object" in star_tags:
                    for obj in get_objects():
                        new_variable = deepcopy(variable)
                        new_variable.attrib["object"] = obj
                        new_star_variables = get_variables_from_stars(new_variable)
                        if new_star_variables:
                            variables_from_stars.extend(new_star_variables)
                elif "to_object" in star_tags:
                    for to_object in get_to_objects():
                        new_variable = deepcopy(variable)
                        new_variable.attrib["to_object"] = to_object
                        new_star_variables = get_variables_from_stars(new_variable)
                        if new_star_variables:
                            variables_from_stars.extend(new_star_variables)
                elif "tech" in star_tags:
                    for tech in get_techs():
                        new_variable = deepcopy(variable)
                        new_variable.attrib["tech"] = tech
                        new_star_variables = get_variables_from_stars(new_variable)
                        if new_star_variables:
                            variables_from_stars.extend(new_star_variables)
                return variables_from_stars #if variables_from_stars else [variable]
            
            # Чтобы учесть все доп. переменные из доп. ограничений необходимо отследить чтобы все генерируемые переменные существовали
            self.collectVariables()
            task = selectors = root.find('task')
            selectors = root.find('task/selectors')
            selectors_tmp = ET.Element(selectors.tag, selectors.attrib)
            
            for selector in selectors.findall('selector'):
                selector_tmp = ET.Element(selector.tag, selector.attrib)
                selectors_tmp.append(selector_tmp)
                
                for variable in selector:
                    # Добавляем "распакованные" переменные
                    new_star_variables = get_variables_from_stars(variable)
                    if new_star_variables:
                        for variable_from_stars in new_star_variables:
                            selector_tmp.append(variable_from_stars)
                    # Если переменная не содержала звёздочек, добавляем её как есть
                    else:
                        selector_tmp.append(deepcopy(variable))
            
            # Заменяем старые селекторы на новые
            task.remove(selectors)
            task.append(selectors_tmp)

        self.buildTechnolog()
        self.buildTechnique()
        #elprint(root.find('task/selectors'))
        #global have_stars
        #while not have_stars:
        make_stars()    # Преобразуем "звездные" переменные в селекторах в нормальные с указанными индексами для формирования целевой функции
        #elprint(root.find('task/selectors'))
        self.buildConstraints()
        #while not have_stars:
        make_stars()
        #elprint(root.find('task/selectors'))
        self.buildCriterion()
        # после формирования ограничений и целевой функции НЕОБХОДИМО собрать переменные с итоговыми индексами
        self.collectVariables()

    def solve(self: PDATask, first_decision_only=False) -> None:
        """Стандартное решение задачи линейного программирования"""
        if self.isMaximize:
            prob = LpProblem(self._Filename, LpMaximize)
        else:
            prob = LpProblem(self._Filename, LpMinimize)

        x = LpVariable.matrix("x",
        (list(range(len(self.CVector)))), 0, None, LpContinuous)

        # формирование целевой функции
        prob += lpDot(x, self.CVector)

        # формирование ограничений
        for constr in self._Constraints:
            if constr.getSign() == '==':
                prob += lpDot(x, constr.getAVector(self._Variables)) == constr.getBValue()
            elif constr.getSign() == '<=':
                prob += lpDot(x, constr.getAVector(self._Variables)) <= constr.getBValue()
            elif constr.getSign() == '>=':
                prob += lpDot(x, constr.getAVector(self._Variables)) >= constr.getBValue()

        prob.solve(PULP_CBC_CMD(msg=0, timeLimit=self.TimeLimit))
        #print(prob.status)
        #print({k:v for k,v in self._Objective.getACoeffDict().items() if v !=0})
        # сбор плана происходит только в случае, если решается вторичная задача (во избежание зацикливания)
        if first_decision_only:
            self._Plan = PDAPlan(
                ResultVariables=prob.variables(),
                VariablesDict=self._Variables
            )
            # убрали вторичный вывов целевой функции
            return

        # Повторное решение задачи ЛП с минимизацией общего времени выполнения операций (отсечка лишних цепочек операций)
        NEW_TASK = deepcopy(self)
        
        # целевая функция на минимизацию суммарного времени всех операций
        c_new = PDAConstraint('MIN')
        root = NEW_TASK._Tree.getroot().find('task')
        for k in root.findall('struct'):
            for i in k.findall('elem'):
                c_new.setCoeff(
                    (
                        'process_all',
                        i.attrib['id'],
                        k.attrib['id']
                    ),
                    1
                )
            for i in k.findall('link'):
                c_new.setCoeff(
                    (
                        'transport_all',
                        i.attrib['id1'],
                        i.attrib['id2'],
                        k.attrib['id']
                    ),
                    1
                )
                c_new.setCoeff(
                    (
                        'transport_all',
                        i.attrib['id2'],
                        i.attrib['id1'],
                        k.attrib['id']
                    ),
                    1
                )
        NEW_TASK.setObjective(c_new)
        
        # ограничение на недопущение снижения качества по полученной ранее целевой функции
        obj_val = prob.objective.value()
        a_new = deepcopy(self._Objective)
        a_new.setSign('==')
        a_new.setBValue(obj_val)
        NEW_TASK.addConstraint(a_new)
        # сбор переменных не нужен, т.к. новых переменных нет

        # запускаем повторную задачу на решение
        NEW_TASK.solve(first_decision_only=True)
        # заменяем полученный ранее план новым, целевую функцию оставляем старую
        self._Plan = copy(NEW_TASK._Plan)
        print('objective', obj_val)

    # Работаем с ТЕХНОЛОГИЯМИ
    def tech_input_set(self: PDATask, Tech: ET.Element) -> set:
        """Возвращает перечень входных потоков технологии Tech"""
        return set([i.attrib['id'] for i in Tech.find('input').findall('type')])

    def tech_output_set(self: PDATask, Tech: ET.Element) -> set:
        """Возвращает перечень входных потоков технологии Tech"""
        return set([i.attrib['id'] for i in Tech.find('output').findall('type')])

    def compareTECH(self: PDATask, Tech1: ET.Element, Tech2: ET.Element) -> bool:
        """Сравнение технологий (по наборам входов и выходов)"""
        return (
            self.tech_input_set(Tech1) == self.tech_input_set(Tech2)
            ) and (
            self.tech_output_set(Tech1) == self.tech_output_set(Tech2)
        )

    def buildMETATech(self: PDATask, tag: str) -> Iterable[Tuple[int,int]]:
        """автоматическое формирование МЕТАТЕХНОЛОГИЙ из XML
        (поиск таких технологий, которые делают из одинакового набора потоков на входе также одинаковый набор потоков на выходе)"""
        root = self._Tree.getroot().find('task')
        return [(int(t1.attrib['id']),int(t2.attrib['id']))
            for (t1,t2) in combinations(root.find(tag).findall('type'),2)
            if self.compareTECH(t1,t2)]

    def buildMETAProcess(self: PDATask) -> Iterable[Tuple[int,int]]:
        """автоматическое формирование МЕТАТЕХНОЛОГИЙ обработки из XML"""
        return self.buildMETATech('process')

    def buildMETATransport(self: PDATask) -> Iterable[Tuple[int,int]]:
        """автоматическое формирование МЕТАТЕХНОЛОГИЙ передачи из XML"""
        return self.buildMETATech('transport')

    def modify_selector_tree(self: PDATask, elem: ET.Element, tag: str='selector'):
        """Модифицируем дерево СЕЛЕКТОРОВ (добавление значений линейных комбинаций)"""
        for i in elem.findall(tag):
            self.modify_selector_tree(i)
        if elem.tag == tag:
            elem.attrib['value'] = str(self.getLineCombineValue(int(elem.attrib['id'])))

    def getXMLReport(self: PDATask) -> ET.ElementTree:
        """возвращает ОТЧЕТ в виде XML-дерева"""
        root = ET.Element('report')
        tree = ET.ElementTree(root)
        # формируем СБОРНЫЙ результат
        summary = ET.SubElement(root, 'summary')
        criterion = ET.SubElement(summary, 'criterion', attrib={'value':str(self.ObjectiveValue)})
        for sel in self._Tree.getroot().find('task').find('criterion').findall('selector'): # ищем по селекторам верхнего уровня КРИТЕРИЯ
            selector = ET.SubElement(criterion, 'selector', attrib={'id':sel.attrib['id'], 'value':str(self.getLineCombineValue(int(sel.attrib['id'])))})
        selectors = deepcopy(self._Tree.getroot().find('task').find('selectors')) # формируем дерево СЕЛЕКТОРОВ со значениями их ЛИНЕЙНЫХ КОМБИНАЦИЙ
        self.modify_selector_tree(selectors)
        summary.append(selectors)
        # формируем подраздел ПЛАН со значениями ПЕРЕМЕННЫХ
        plan = ET.SubElement(root, 'plan')
        for item in sorted(self.PLAN.getPDict().items(), key=lambda t: str(t[0])):
            key = item[0]
            val = item[1]
            if val > 0: # не выводить ПЕРЕМЕННЫЕ со значениями 0
                attr = get_dict_from_key(key)
                itemXML = ET.SubElement(plan, get_key_type(key), attrib=attr)
                itemXML.text = str(val)

        indent(root) # делаем отступы и переносы строк в XML
        return tree