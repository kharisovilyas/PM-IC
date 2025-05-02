'''Данная программа переводит потенциалы доступности КА между собой или другими объектами в интервалы структуропостоянста'''
from copy import copy
import json
from pprint import pprint

from progress.bar import IncrementalBar

def diap_gen(points):
    '''Получаем дианазоны из временных точек'''
    yield points[0], points[1]
    for i,_ in enumerate(points[2:]):
        yield points[i+1], points[i+2]

# получаем события видимости из файла
def get_strdin(request):
    events = copy(request['connections'])
    print('events:',len(events))
    flow_events = request['task']['flows']
    print('flow_events:',len(flow_events))

    # получаем отсортированную последовательность уникальных моментов времени, когда что-то в принципе изменялось в зонах видимости
    points = sorted(list(set([event['begin'] for event in events] + [event['end'] for event in events])))
    # добавляем фиктивные события по прибытию потоков данных вне диапазона структурной динамики
    flow_points = set()
    for flow_event in flow_events:
        flow_start = flow_event.get('input_time_start') or flow_event.get('output_time_start')
        flow_finish = flow_event.get('input_time_finish') or flow_event.get('output_time_finish')
        if flow_start and flow_finish:
            events.append({'begin': flow_start, 'end': flow_finish})
        if flow_start < points[0] or flow_start > points[-1]: flow_points.add(flow_start)
        if flow_finish < points[0] or flow_finish > points[-1]: flow_points.add(flow_finish)
    points = sorted(points + list(flow_points))
    print('points:',len(points))


    # определяем кто кого видит на интервала постоянства (diap_gen)
    bar = IncrementalBar('Разбивка интервалов', max = len(points) - 1)
    str_din = []
    for i, diap in enumerate(diap_gen(points)):
        now = set()
        for event in events:
            if event['begin'] <= diap[0] and diap[1] <= event['end']:
                from_event = event.get('gsLabel') or event.get('scLable1')
                to_event = event.get('scLabel') or event.get('scLable2')
                if from_event and to_event:
                    now.add((from_event, to_event))
                data = []
        str_din.append({'id': i+1,'interval': diap[1] - diap[0], 'start_time': diap[0], 'end_time': diap[1], 'connected': sorted(now), 'data': data})
        bar.next()
    bar.finish()
    
    # определяем когда и какие потоки поступают на вход и на выход системы
    def data_flows_sorter(flows):
        '''Сортируем интервалы по началу'''
        return sorted(flows, key = lambda x: x['input_time_start'] if 'input_time_start' in x else x['output_time_start'])

    def data_flow_split(flow, points):
        '''Разбиваем интервал в соответствии с временными отметками пропорционально ВХОДНОЙ data
        points должны быть отсортированы'''
        start = flow['input_time_start'] if 'input_time_start' in flow else flow['output_time_start'] 
        finish = flow['input_time_finish'] if 'input_time_finish' in flow else flow['output_time_finish']
        big_diap = finish - start
        diaps = list(diap_gen([point for point in points if start <= point <= finish]))
        splited_flow = []
        for diap in diaps:
            new_flow = copy(flow)
            if 'input_time_start' in flow and 'input_time_finish' in flow:
                new_flow['input_time_start'] = diap[0]
                new_flow['input_time_finish'] = diap[1]
                # Делим пророрционально ВХОДНОЙ поток
                if 'input_size' in flow:
                    new_flow['input_size'] = flow['input_size']*(diap[1] - diap[0])/big_diap
            elif 'output_time_start' in flow and 'output_time_finish' in flow:
                new_flow['output_time_start'] = diap[0]
                new_flow['output_time_finish'] = diap[1]
                # Делим пророрционально ВЫХОДНОЙ поток
                if 'output_size' in flow:
                    new_flow['output_size'] = flow['output_size']*(diap[1] - diap[0])/big_diap
            splited_flow.append(new_flow)
        return splited_flow
    
    def get_points_from_flows_and_points(flows, points):
        '''Получаем все уникальные временные точки из потоков и диапазонов'''
        all_points =  [flow['input_time_start'] for flow in flows if 'input_time_start' in flow]
        all_points += [flow['input_time_finish'] for flow in flows if 'input_time_finish' in flow]
        all_points += [flow['output_time_start'] for flow in flows if 'output_time_start' in flow]
        all_points += [flow['output_time_finish'] for flow in flows if 'output_time_finish' in flow]
        all_points += points
        all_points =  sorted(list(set(all_points)))
        return all_points
    
    def split_flows(flows,points):
        '''Разбиваем ВХОДНЫЕ и ВЫХОДНЫЕ потоки в соответствии с пересечениями их интервалов и интервалами структуропостоянства'''
        all_points = get_points_from_flows_and_points(flows, points)
        print(all_points)
        new_flows = []
        bar = IncrementalBar('Формирование потоков', max = len(flows))
        for flow in flows:
            new_flows += data_flow_split(flow,all_points)
            bar.next()
        bar.finish()
        new_flows = data_flows_sorter(new_flows)
        return new_flows

    def get_flows_from_diap(diap, flows):
        '''Ищем какой поток входит по указанному диапазону'''
        selected_flows = []
        for flow in flows:
            if  (flow['input_time_start'] == diap[0] if 'input_time_start' in flow else False) and (flow['input_time_finish'] == diap[1] if 'input_time_finish' in flow else False) or \
                (flow['output_time_start'] == diap[0] if 'output_time_start' in flow else False) and (flow['output_time_finish'] == diap[1]  if 'output_time_finish' in flow else False):
                selected_flows.append(flow)
        return selected_flows

    def spllit_intervals_with_adding_flowdata(intervals,flows,points):
        bar = IncrementalBar('Наложение потоков', max = len(intervals))
        interval_id = 0
        new_intervals = []
        all_points = get_points_from_flows_and_points(flows, points)
        for interval in intervals:
            start = interval['start_time']
            finish = interval['end_time']
            big_diap = finish - start
            diaps = list(diap_gen([point for point in all_points if start <= point <= finish]))
            print(diaps)
            for diap in diaps:
                interval_id += 1
                new_interval = copy(interval)
                new_interval['id'] = interval_id
                # Формируем правильный временной диапазон
                new_interval['start_time'] = diap[0]
                new_interval['end_time'] = diap[1]
                new_interval['interval'] = diap[1] - diap[0]
                # Накладываем входные и выходные потоки
                new_interval['data'] = get_flows_from_diap(diap, flows)
                new_intervals.append(new_interval)
            bar.next()
        bar.finish()
        return new_intervals


    #Разбиваем входные и выходные потоки и накладываем на интервалы постоянства структуры
    flows = request['task']['flows']
    new_flows = split_flows(flows,points)
    pprint(new_flows)
    new_str_din = spllit_intervals_with_adding_flowdata(intervals=str_din,flows=new_flows,points=points)
    pprint(new_str_din)
    print('\nstr_din:',len(new_str_din))

    return new_str_din