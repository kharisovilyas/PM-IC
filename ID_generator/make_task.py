import argparse
import json
from typing import Iterable
from copy import copy

from lxml import etree, objectify
from progress.bar import IncrementalBar
from finding_cycle import get_strdin

from make_task_lib import make_flows
from make_task_lib import make_process, make_transport, make_storage
from make_task_lib import make_struct
from make_task_lib import make_criterion, make_constraints, make_selectors

filename1 = 'request_template.json'

arg = argparse.ArgumentParser()
arg.add_argument('--filename', '-f', nargs='+')
args = arg.parse_args()
if args.filename:
    filename1 = str(args.filename[0])
filename = filename1.split('.')[0]
filename_result = filename + '.xml'

#input('Для запуска ' + filename1 + ' нажмите ENTER')


request = json.load(open(filename1,'r'))
str_din = get_strdin(request)

# Разбиваем "worker_id": [0, 1, 2, 3...] на отдельные workers
new_workers = []
for worker in request['environment']['workers']:
    if isinstance(worker['worker_id'], Iterable):
        for id in worker['worker_id']:
            worker_clone = copy(worker)
            worker_clone['worker_id'] = id
            new_workers.append(worker_clone)
request['environment']['workers'] = new_workers
#pprint(request)


# Создаем список id workers
workers_id_set = set()
for interval in str_din:
    for worker in interval['connected']:
        workers_id_set.add(worker[0])
        workers_id_set.add(worker[1])

xml = '''
<XMLDocument version="1.0">
    <comment />
</XMLDocument>'''

root = objectify.fromstring(xml)
root.append(objectify.Element("task"))
task = root.task




task.append(make_flows(request))
task.append(make_process(request))
task.append(make_transport(request))
task.append(make_storage(request))

bar = IncrementalBar('Интервалы постоянства', max = len(str_din))
for struct_info in str_din:
    struct = make_struct(request, struct_info)
    task.append(struct)
    bar.next()
bar.finish()

task.append(make_selectors(request))
task.append(make_criterion(request))
task.append(make_constraints(request))





# удаляем все lxml аннотации.
objectify.deannotate(root)
etree.cleanup_namespaces(root)

# конвертируем все в привычную нам xml структуру.
obj_xml = etree.tostring(root,
    pretty_print=True,
    xml_declaration=True,
    encoding="utf-8"
)

try:
    with open(filename_result, "wb") as xml_writer:
        xml_writer.write(obj_xml)
except IOError:
    pass