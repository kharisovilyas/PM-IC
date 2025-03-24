import xml.etree.ElementTree as ET
import json
import argparse

def parse_xml_to_json(xml_file_path, json_file_path):
    """Парсит XML файл и сохраняет данные в JSON формате"""
    try:
        # Парсинг XML файла
        tree = ET.parse(xml_file_path)
        root = tree.getroot()

        # Собираем информацию о временных интервалах из struct
        time_intervals = {}
        for struct in root.findall('.//struct'):
            interval = struct.get('id')
            time_intervals[interval] = {
                'start_time': int(struct.get('start_time')),
                'end_time': int(struct.get('end_time'))
            }

        # Собираем данные о передаче информации (to_transport)
        transport_data = {}
        for transport in root.findall('.//plan/to_transport'):
            interval = transport.get('interval')
            sc_id = transport.get('object')
            gs_id = transport.get('to_object')
            flow = float(transport.text) if transport.text else 0.0

            key = (interval, sc_id, gs_id)
            transport_data[key] = transport_data.get(key, 0.0) + flow

        # Собираем данные об объеме обработанной информации (to_process)
        process_data = {}
        for process in root.findall('.//plan/to_process'):
            interval = process.get('interval')
            object_id = process.get('object')
            volume = float(process.text) if process.text else 0.0

            key = (interval, object_id)
            process_data[key] = volume

        # Собираем данные о хранении информации (storage)
        storage_data = {}
        for storage in root.findall('.//plan/storage'):
            interval = storage.get('interval')
            object_id = storage.get('object')
            size = float(storage.text) if storage.text else 0.0

            key = (interval, object_id)
            storage_data[key] = size

        # Формируем итоговый JSON
        result = []
        for (interval, sc_id, gs_id), transmit_data in transport_data.items():
            if interval in time_intervals:
                entry = {
                    'scId': int(sc_id),
                    'gsId': int(gs_id),
                    'timeStart': time_intervals[interval]['start_time'],
                    'timeEnd': time_intervals[interval]['end_time'],
                    'transmitData': transmit_data,
                    'processVolume': process_data.get((interval, gs_id), 0.0),
                    'storageSize': storage_data.get((interval, sc_id), 0.0)
                }
                result.append(entry)

        # Сохраняем в JSON файл
        with open(json_file_path, 'w') as json_file:
            json.dump({'plan': result}, json_file, indent=2)
        
        print(f"Данные успешно сохранены в {json_file_path}")
        return True

    except Exception as e:
        print(f"Ошибка при обработке файлов: {str(e)}")
        return False

def main():
    # Настройка парсера аргументов командной строки
    parser = argparse.ArgumentParser(
        description='Конвертер XML отчета в JSON формат',
        epilog='Пример использования: python converter.py input.xml output.json')
    
    parser.add_argument('input', help='Путь к входному XML файлу')
    parser.add_argument('output', help='Путь к выходному JSON файлу')
    
    args = parser.parse_args()

    # Запуск конвертации
    if not parse_xml_to_json(args.input, args.output):
        exit(1)

if __name__ == "__main__":
    main()