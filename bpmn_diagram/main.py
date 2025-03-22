import xml.etree.ElementTree as ET
from copy import deepcopy

from progress.bar import IncrementalBar
import networkx as nx
from networkx import *

from .techchains import get_all_ways


def get_x_y(op: ET.Element):
    x = 0
    y = {}
    x = int(op.get('interval'))*100
    if op.get('interval') in y:
        y[op.get('interval')] += 10
    else:
        y[op.get('interval')] = 10
    return (x,y[op.get('interval')])

def get_operations(filename):
    if isinstance(filename, str):
        tree = ET.parse(filename)
    elif isinstance(filename, ET.ElementTree):
        tree = filename
    else:
        raise TypeError("Filename not str or ElementTree")
    root = tree.getroot()
    plan = root.find('report/plan')
    operations = []
    input_flows = []
    result_flows = []
    process_s = []
    to_process_s = []
    from_process_s = []
    transports = []
    to_transports = []
    from_transports = []
    storages = []
    losts = []
    operations_num = 0

    i = 0
    for i, inputflow in enumerate(plan.findall('inputflow')):
        operations.append(inputflow)
        input_flows.append(inputflow)
    input_flows = sorted(input_flows, key = lambda x: x.get('interval'))
    operations_num += i

    for i, process in enumerate(plan.findall('process')):
        operations.append(process)
        process_s.append(process)
    process_s = sorted(process_s, key = lambda x: x.get('interval'))
    operations_num += i

    for i, to_process in enumerate(plan.findall('to_process')):
        operations.append(to_process)
        to_process_s.append(to_process)
    to_process_s = sorted(to_process_s, key = lambda x: x.get('interval'))
    operations_num += i

    for i, from_process in enumerate(plan.findall('from_process')):
        operations.append(from_process)
        from_process_s.append(from_process)
    from_process_s = sorted(from_process_s, key = lambda x: x.get('interval'))
    operations_num += i

    for i, transport in enumerate(plan.findall('transport')):
        operations.append(transport)
        transports.append(transport)
    transports = sorted(transports, key = lambda x: x.get('interval'))
    operations_num += i

    for i, to_transport in enumerate(plan.findall('to_transport')):
        operations.append(to_transport)
        to_transports.append(to_transport)
    to_transports = sorted(to_transports, key = lambda x: x.get('interval'))
    operations_num += i

    for i, from_transport in enumerate(plan.findall('from_transport')):
        operations.append(from_transport)
        from_transports.append(from_transport)
    from_transports = sorted(from_transports, key = lambda x: x.get('interval'))
    operations_num += i

    for i, storage in enumerate(plan.findall('storage')):
        operations.append(storage)
        storages.append(storage)
    storages = sorted(storages, key = lambda x: x.get('interval'))
    operations_num += i

    for i, lost in enumerate(plan.findall('lost')):
        operations.append(lost)
        losts.append(lost)
    losts = sorted(losts, key = lambda x: x.get('interval'))
    operations_num += i

    for i, resultflow in enumerate(plan.findall('resultflow')):
        operations.append(resultflow)
        result_flows.append(resultflow)
    result_flows = sorted(result_flows, key = lambda x: x.get('interval'))
    operations_num += i

    operations = sorted(operations, key = lambda x: x.get('interval'))

    return operations, input_flows, result_flows, process_s, to_process_s, from_process_s, transports, to_transports, from_transports, storages, losts
        

def is_next_operation(operation: ET.Element, kandidat_operation: ET.Element):
    '''Проверка является ли kandidat_operation той операцией, которая может идти следом за operation'''
    is_operation = False
    type_op, interval, flow, obj, to_obj, tech, value = (operation.tag, int(operation.get('interval')), operation.get('flow'), operation.get('object'), operation.get('to_object'), operation.get('tech'), float(operation.text)) 
    k_type_op, k_interval, k_flow, k_obj, k_to_obj, k_tech, k_value = (kandidat_operation.tag, int(kandidat_operation.get('interval')), kandidat_operation.get('flow'), kandidat_operation.get('object'), kandidat_operation.get('to_object'), kandidat_operation.get('tech'), float(operation.text)) 
    
    # TWEEKS
    # связанные операции в пределах одного-двух интервалов (последнее про хранение)
    if not (interval <= k_interval <= interval + 1): return False    # не является операцией по интервалу

    # ВХОДНОЙ ПОТОК
    # Передаем входной поток напрямую на выход
    if type_op == 'inputflow' and k_type_op == 'resultflow':
        if interval == k_interval:
            if obj == k_obj:
                if flow == k_flow:
                    is_operation = True
    # Сохраняем входной поток в ЗУ
    if type_op == 'inputflow' and k_type_op == 'storage':
        if interval == k_interval:
            if obj == k_obj:
                if flow == k_flow:
                    is_operation = True
    # Передаем входной поток на обработку
    if type_op == 'inputflow' and k_type_op == 'to_process':
        if interval == k_interval:
            if obj == k_obj:
                if flow == k_flow:
                    is_operation = True
    # Передаем входной поток на передачу
    if type_op == 'inputflow' and k_type_op == 'to_transport':
        if interval == k_interval:
            if obj == k_obj:
                if flow == k_flow:
                    is_operation = True
    # Теряем входной поток
    if type_op == 'inputflow' and k_type_op == 'lost':
        if interval == k_interval:
            if obj == k_obj:
                if flow == k_flow:
                    is_operation = True

    # ПОТОК ПОСЛЕ ОБРАБОТКИ
    # Передаем поток на выход
    if type_op == 'from_process' and k_type_op == 'resultflow':
        if interval == k_interval:
            if obj == k_obj:
                if flow == k_flow:
                    is_operation = True
    # Сохраняем поток в ЗУ
    if type_op == 'from_process' and k_type_op == 'storage':
        if interval == k_interval:
            if obj == k_obj:
                if flow == k_flow:
                    is_operation = True
    # Передаем поток на обработку
    if type_op == 'from_process' and k_type_op == 'to_process':
        if interval == k_interval:
            if obj == k_obj:
                if flow == k_flow:
                    is_operation = True
    # Передаем входной поток на передачу
    if type_op == 'from_process' and k_type_op == 'to_transport':
        if interval == k_interval:
            if obj == k_obj:
                if flow == k_flow:
                    is_operation = True
    # Теряем поток
    if type_op == 'from_process' and k_type_op == 'lost':
        if interval == k_interval:
            if obj == k_obj:
                if flow == k_flow:
                    is_operation = True

    # ПОТОК ПОСЛЕ ПЕРЕДАЧИ
    # Передаем поток на выход
    if type_op == 'from_transport' and k_type_op == 'resultflow':
        if interval == k_interval:
            if to_obj == k_obj:
                if flow == k_flow:
                    is_operation = True
    # Сохраняем поток в ЗУ
    if type_op == 'from_transport' and k_type_op == 'storage':
        if interval == k_interval:
            if to_obj == k_obj:
                if flow == k_flow:
                    is_operation = True
    # Передаем поток на обработку
    if type_op == 'from_transport' and k_type_op == 'to_process':
        if interval == k_interval:
            if to_obj == k_obj:
                if flow == k_flow:
                    is_operation = True
    # Передаем входной поток на передачу
    if type_op == 'from_transport' and k_type_op == 'to_transport':
        if interval == k_interval:
            if to_obj == k_obj:
                if flow == k_flow:
                    is_operation = True
    # Теряем поток
    if type_op == 'from_transport' and k_type_op == 'lost':
        if interval == k_interval:
            if to_obj == k_obj:
                if flow == k_flow:
                    is_operation = True

    # ПОТОК ПОСЛЕ ХРАНЕНИЯ
    # Передаем поток на выход
    if type_op == 'storage' and k_type_op == 'resultflow':
        if int(interval) + 1 == int(k_interval):
            if obj == k_obj:
                if flow == k_flow:
                    is_operation = True
    # Сохраняем поток в ЗУ
    if type_op == 'storage' and k_type_op == 'storage':
        if int(interval) + 1 == int(k_interval):
            if obj == k_obj:
                if flow == k_flow:
                    is_operation = True
    # Передаем поток на обработку
    if type_op == 'storage' and k_type_op == 'to_process':
        if int(interval) + 1 == int(k_interval):
            if obj == k_obj:
                if flow == k_flow:
                    is_operation = True
    # Передаем входной поток на передачу
    if type_op == 'storage' and k_type_op == 'to_transport':
        if int(interval) + 1 == int(k_interval):
            if obj == k_obj:
                if flow == k_flow:
                    is_operation = True
    # Теряем поток
    if type_op == 'storage' and k_type_op == 'lost':
        if int(interval) + 1 == int(k_interval):
            if obj == k_obj:
                if flow == k_flow:
                    is_operation = True

    # ПРЕОБРАЗОВАНИЕ ПОТОКОВ
    # Преобразуем поток через обработку
    if type_op == 'to_process' and k_type_op == 'process':
        if interval == k_interval:
            if obj == k_obj:
                if tech == k_tech:
                    is_operation = True
    if type_op == 'process' and k_type_op == 'from_process':
        if interval == k_interval:
            if obj == k_obj:
                if tech == k_tech:
                    is_operation = True
    # Преобразуем поток через передачу
    if type_op == 'to_transport' and k_type_op == 'transport':
        if interval == k_interval:
            if obj == k_obj and to_obj == k_to_obj:
                if tech == k_tech:
                    is_operation = True
    if type_op == 'transport' and k_type_op == 'from_transport':
        if interval == k_interval:
            if obj == k_obj and to_obj == k_to_obj:
                if tech == k_tech:
                    is_operation = True

    return is_operation

def make_techchains_bpmn_from_report(filename=None, XMLReport=None, NotDraw=False, task_name = None, NotDiagram=False):
    if not task_name:
        task_name = filename
    if not filename and not XMLReport:
        raise Exception('No BPMN in parameters (str filename or ElementTree)')
    plan_report = filename if filename else XMLReport
    operations, input_flows, result_flows, _, _, _, _, _, _, storages, losts = get_operations(plan_report)

    ops1 = input_flows[:] + storages[:]
    ops2 = result_flows[:] + losts[:] + storages[:]
    
    # Формируем граф связей операций напрямую из плана
    # Формируем вершины
    nodes = set()
    labels = {}
    for node in operations:
            nodes.add(node)
            labels[node] = node.tag

    # Формируем связи
    edges = []
    edge_labels = {}
    bar = IncrementalBar('Поиск связей\t\t', max = len(operations))
    all_ops1 = sorted(operations, key = lambda x: x.get('interval'))
    all_ops2 = sorted(operations, key = lambda x: x.get('interval'))
    for i,op1 in enumerate(all_ops1):
        for op2 in all_ops2:
            is_link = is_next_operation(op1, op2)
            if is_link:
                val1 = float(op1.text)
                val2 = float(op2.text)
                val = val1
                # Визуальная очистка графа от потокового мусора
                if op1.tag not in ('process', 'transport') and op2.tag not in ('process', 'transport'): # это потоки
                    val = min([val1, val2])
                edges.append((op1, op2, str(val)))
                edge_labels[(op1,op2)] = str(val)
        bar.next()

    DG = nx.DiGraph()
    nodes = set()
    labels = {}
    pos = {}
    for op1, op2, _ in edges:
        nodes.add(op1)
        nodes.add(op2)

        pos[op1] = get_x_y(op1)
        pos[op2] = get_x_y(op2)

        labels[op1] = op1.tag
        labels[op2] = op2.tag
    DG.add_nodes_from(nodes)
    DG.add_weighted_edges_from(edges)

    print()
    paths = []
    bar = IncrementalBar('Поиск цепочек в графе\t', max = len(ops1))
    for op1 in ops1:
        if DG.has_node(op1) and not list(DG.predecessors(op1)):
            for op2 in ops2:
                if DG.has_node(op2) and not list(DG.successors(op2)):
                    paths.extend(get_all_ways(start=op1, finish=op2, is_next_operation=is_next_operation, DG=DG))
        bar.next()

    # Формируем ИЛИ из И-ИЛИ
    sub_DG2 = nx.DiGraph()
    sub_nodes2 = set()
    labels2 = {}
    edge_labels2 = {}
    paths2 = []
    for way in paths:
        way2 = []
        for i,elem in enumerate(way):
            if elem.tag in ('process', 'transport', 'lost', 'storage', 'resultflow', 'inputflow'):
                way2.append(deepcopy(elem))
            sub_DG2.add_node(way2[-1])
            labels2[way2[-1]] = way2[-1].tag
        for elem1, elem2 in zip(way2, way2[1:]):
            sub_DG2.add_edge(elem1, elem2)
            edge_labels2[(elem1,elem2)] = ''
        paths2.append(way2)
    
    chains = paths2
    chains_for_constraints = deepcopy(paths2)
    for i, path in enumerate(chains_for_constraints):
        new_path = [el for el in path if el.tag in ('transport', 'process')]
        chains_for_constraints[i] = new_path
    chains_for_constraints_in_intervals = set()     # создаем set уникальных цепочек операций
    for i, path in enumerate(chains_for_constraints):
        while path:
            interval = path[0].attrib['interval']   # берем интервал первого элемента
            chain = [el for el in path if el.attrib['interval'] == interval]    # выбираем элементы с тем же интервалом
            chains_for_constraints_in_intervals.add(tuple(chain))  # вставляем в итоговый set
            for el in chain:
                chains_for_constraints[i].remove(el)    # удаляем элементы, выбранные из path
    chains_for_constraints_in_intervals = list(chains_for_constraints_in_intervals)

    return None, chains, chains_for_constraints_in_intervals