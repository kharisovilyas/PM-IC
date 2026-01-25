#import json
import json
from pprint import pprint
from lxml import objectify
import xml.etree.ElementTree as ET


def elprint(j: ET.Element, tab=0):
    print('  '*tab, j.tag, j.attrib, j.text)
    tab += 1
    for i in j.findall('*'):
        elprint(i, tab+1)

flows_set = set()   # глобальная переменная - id потоков
process_set = set()
transport_set = set()
process_workers_map = {}
transport_links_map = {}
selectors_dict = {}      # глобальная переменная - селекторы (ключ - имя, значение - номер)


def make_flows(json_data):
    # учитываем все входные и выходные потоки из task (входные потоки) и operations (входные и выходные потоки)
    flows = objectify.Element('flows')
    for flow in json_data['task']['flows']:
        flows_set.add(flow['flow_type_id'])
    for oper in json_data['environment']['operations']:
        flows_set.add(oper['input_flow_type_id'])
        flows_set.add(oper['output_flow_type_id'])
    for flow_id in sorted(flows_set):
        elem = objectify.Element('type')
        elem.set('id', str(flow_id))
        flows.append(elem)
    return flows

def make_process(json_data):
    # производительность замеряется на неком базовом процессоре и умножается на "во сколько тактовая частота раз отличается от текущей" 
    process = objectify.Element("process")
    for worker in json_data['environment']['workers']:
        for oper in json_data['environment']['operations']:
            worker_oper_ids = [worker['operation_ids']] if not isinstance(worker['operation_ids'], (list, tuple)) else worker['operation_ids']
            if oper['operation_id'] in worker_oper_ids:
                time = str(1/(oper['difficult']*worker['proc_speed']))
                inp_type = str(oper['input_flow_type_id'])
                out_type = str(oper['output_flow_type_id'])
                proc = (time,inp_type,out_type)
                process_set.add(proc)
                worker_ids = [worker['worker_id']] if not isinstance(worker['worker_id'], (list, tuple)) else worker['worker_id']
                for worker_id in worker_ids:
                    if worker_id not in process_workers_map:
                        process_workers_map[worker_id] = set([proc])
                    else:
                        process_workers_map[worker_id].add(proc)

    pprint(process_set)
    pprint(process_workers_map)

    for k,v in process_workers_map.items():
        process_workers_map[k] = [list(process_set).index(v) + 1 for v in process_workers_map[k]]
    pprint(process_workers_map)

    for i, uniq_proc in enumerate(process_set):
        time,inp_type,out_type = uniq_proc
        elem = objectify.Element('type')
        elem.set('id', str(i+1))
        elem.set('time', time)
        
        inp = objectify.Element('input')
        intype = objectify.Element('type')
        intype.set('id', inp_type)
        intype.set('size', '1')   # добавить получение размера данных
        inp.append(intype)
        
        outp = objectify.Element('output')
        outtype = objectify.Element('type')
        outtype.set('id', out_type)
        outtype.set('size', '1')  # добавить получение размера данных
        outp.append(outtype)

        elem.append(inp)
        elem.append(outp)
        process.append(elem)
    return process

def make_transport(json_data):
    # формируем все возможные связи между узлами с минимальной скоростью передачи данных
    transport = objectify.Element("transport")
    for worker1 in json_data['environment']['workers'][:]:
        for worker2 in json_data['environment']['workers'][:]:
            for flow in json_data['task']['flows']:
                #if worker1['worker_id'] < worker2['worker_id']:
                speed = min(worker1['net_speed'], worker2['net_speed'])
                inp_type = str(flow['flow_type_id'])
                out_type = str(flow['flow_type_id'])
                trans = (speed,inp_type,out_type)
                transport_set.add(trans)
                worker1_ids = [worker1['worker_id']] if not isinstance(worker1['worker_id'], (list, tuple)) else worker1['worker_id']
                worker2_ids = [worker2['worker_id']] if not isinstance(worker2['worker_id'], (list, tuple)) else worker2['worker_id']
                for w_id1 in worker1_ids:
                    for w_id2 in worker2_ids:
                        if w_id1 < w_id2:
                            if (w_id1, w_id2) not in transport_links_map:
                                transport_links_map[(w_id1, w_id2)] = set([trans])
                                #transport_links_map[(w_id2, w_id1)] = set([trans])
                            else:
                                transport_links_map[(w_id1, w_id2)].add(trans)
                                #transport_links_map[(w_id2, w_id1)].add(trans)
    pprint(transport_set)
    pprint(transport_links_map)
    for k,v in transport_links_map.items():
        transport_links_map[k] = [list(transport_set).index(v) + 1 for v in transport_links_map[k]]
    pprint(transport_links_map)

    for i, uniq_trans in enumerate(transport_set):
                    speed,inp_type,out_type = uniq_trans
                    elem = objectify.Element('type')
                    elem.set('id', str(i+1))
                    elem.set('time', '1')

                    inp = objectify.Element('input')
                    intype = objectify.Element('type')
                    intype.set('id', inp_type)
                    intype.set('size', str(speed))
                    inp.append(intype)

                    outp = objectify.Element('output')
                    outtype = objectify.Element('type')
                    outtype.set('id', out_type)
                    outtype.set('size', str(speed))
                    outp.append(outtype)

                    elem.append(inp)
                    elem.append(outp)
                    transport.append(elem)
    return transport

def make_storage(json_data):
    #делаем 1 технологию хранения (после тиражируем ее для узлов)
    storage = objectify.Element("storage")
    elem = objectify.Element('type')
    elem.set('id', '1')     # id - единая технология хранения информации
    inp = objectify.Element('input')
    for flow_type in flows_set:
        intype = objectify.Element('type')
        intype.set('id', str(flow_type))
        inp.append(intype)
    elem.append(inp)
    storage.append(elem)
    return storage

def make_struct(json_data, struct_info):
    struct = objectify.Element("struct")
    struct.set('id', str(struct_info['id']))
    struct.set('time', str(struct_info['interval']))
    struct.set('start_time', str(struct_info['start_time']))
    struct.set('end_time', str(struct_info['end_time']))

    # Расставляем рабочие узлы
    for worker in json_data['environment']['workers']:
        worker_ids = sorted([worker['worker_id']] if not isinstance(worker['worker_id'], (list, tuple)) else worker['worker_id'])
        for worker_id in worker_ids:
            elem = objectify.Element("elem")
            elem.set('id', str(worker_id))
            # вставляем входные потоки (и выходные потоки)
            for flow in struct_info['data']:
                if (worker_id in flow['input_workers'] if 'input_workers' in flow else False) or (worker_id in flow['output_workers'] if 'output_workers' in flow else False):
                    ### ЗДЕСЬ ФОРМИРУЕМ ИТОГОВЫЕ СТРУКТУРЫ ИСХОДЯ ИЗ ИНТЕРВАЛОВ (ГДЕ УЖЕ БУДУТ УКАЗАНЫ ВХОДНЫЕ И ВЫХОДНЫЕ ПОТОКИ)
                    p = str(flow['flow_type_id'])
                    if 'input_time_start' in flow and 'input_time_finish' in flow:
                        size = str(flow['input_size']) if 'input_size' in flow else ""
                        elem.set('input_' + p, size)
                    elif 'output_time_start' in flow and 'output_time_finish' in flow:
                        size = str(flow['output_size']) if 'output_size' in flow else ""
                        elem.set('output_' + p, size)
            # вставляем операции обработки и хранения
            if worker_id in process_workers_map:
                for oper in process_workers_map[worker_id]:
                    elem.set('process_' + str(oper), '')
            elem.set('storage_1', str(worker['storage_size']))
            struct.append(elem)
    
    # Делаем связи
    for workers_ids in struct_info['connected']:
        link = objectify.Element("link")
        link.set('id1', str(workers_ids[0]))
        link.set('id2', str(workers_ids[1]))
        workers_ids_int = tuple(sorted(int(i) for i in workers_ids))
        if workers_ids_int in transport_links_map:
            for oper in transport_links_map[workers_ids_int]:
                link.set('transport_' + str(oper), '')   # откуда-куда-какой поток
        elif reversed(workers_ids_int) in transport_links_map:
            for oper in transport_links_map[reversed(workers_ids_int)]:
                link.set('transport_' + str(oper), '')   # откуда-куда-какой поток
        else:
            raise Exception('Transport error')
        struct.append(link)
    return struct

def make_criterion(json_data):
    json_crit = json_data['task']['criterion']
    criterion = objectify.Element("criterion")
    criterion.set('sign',str(json_crit['sign']))
    for indicator, sign in json_crit['indicators'].items():
        selector = objectify.Element("selector")
        selector.set('id', str(selectors_dict[indicator]))
        criterion.append(selector)
    return criterion

def make_constraints(json_data):
    constraints = objectify.Element("constraints")
    json_constr = json_data['task']['constraints']
    id_gen = new_id()
    constraint = None
    for constr in json_constr:
        constraint = objectify.Element("constraint")
        constraint.set('id', str(next(id_gen)))
        constraint.set('sign', str(constr['sign'][0]))
        constraint.set('value', str(constr['sign'][1]))
        for indicator, sign in constr['indicators'].items():
            selector = objectify.Element("selector")
            selector.set('id', str(selectors_dict[indicator]))
            selector.set('sign', str(sign))
        constraint.append(selector)
    if constraint:
        constraints.append(constraint)
    return constraints

def new_id():
    x = 0
    while True:
        x += 1
        yield x

def make_selectors(json_data):
    selectors = objectify.Element("selectors")
    json_indic = json_data['task']['indicators']
    id_gen = new_id()
    for indicator, templates in json_indic.items():
        selectors_dict[indicator] = next(id_gen)
        selector = objectify.Element("selector")
        selector.set('id', str(selectors_dict[indicator]))
        selector.set('sign', str(json_data['task']['criterion']['indicators'][indicator]))
        for template in templates:
            selector_part = objectify.Element(template['type'])
            for k,v in template.items():
                if k == 'type':
                    continue
                selector_part.set(k, str(v))
            selector.append(selector_part)
        selectors.append(selector)
    return selectors


if __name__ =="__main__":
    request = json.load(open('request_template.json','r'))
    make_process(request)
    make_transport(request)
    from finding_cycle import get_strdin
    str_din = get_strdin(request)
    for struct_info in str_din:
        elprint(make_struct(request, struct_info))