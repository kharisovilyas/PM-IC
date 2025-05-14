from numbers import Number
import xml.etree.ElementTree as ET
import json


def auto_cast(value):
    """Преобразует строку в число или оставляет как строку"""
    if value is None or value.strip() == "":
        return None
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def force_list(data):
    """Преобразует данные в список, даже если None или одиночный элемент"""
    if data is None:
        return []
    if isinstance(data, list):
        return data
    return [data]


def xml_element_to_dict(element, path=None, always_list_tags_in_plan=None):
    """Рекурсивно преобразует XML-элемент в словарь"""

    if always_list_tags_in_plan is None:
        always_list_tags_in_plan = ["inputflow", "resultflow", "process", "transport", "transport_all", "process_all", "lost", "to_process", "from_process", "to_transport", "time", "from_transport"]

    if path is None:
        path = []

    current_tag = element.tag
    current_path = path + [current_tag]

    # Проверка: сейчас ли мы внутри <plan>
    is_inside_plan = "plan" in current_path

    # Если у элемента нет дочерних и атрибутов — просто текстовое значение
    if len(element) == 0 and not element.attrib:
        return auto_cast(element.text)

    node = {}

    # Обрабатываем атрибуты
    if element.attrib:
        node.update({f"@{key}": auto_cast(value) for key, value in element.attrib.items()})

    # Обрабатываем детей
    children = {}
    for child in element:
        child_data = xml_element_to_dict(child, path=current_path)
        if child.tag in children:
            if not isinstance(children[child.tag], list):
                children[child.tag] = [children[child.tag]]
            children[child.tag].append(child_data)
        else:
            children[child.tag] = child_data

    # Принудительно делаем списки только внутри plan
    if is_inside_plan:
        for tag in list(children.keys()):
            if tag in always_list_tags_in_plan:
                children[tag] = force_list(children[tag])

    # Добавляем текст, если нет детей
    if not children and element.text and element.text.strip():
        node["#text"] = auto_cast(element.text)

    node.update(children)
    return node


def xml_file_to_json(xml_path, json_path="report.json"):
    tree = ET.parse(xml_path)
    root = tree.getroot()

    data = {
        root.tag: xml_element_to_dict(root)
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    print(f"✅ JSON сохранён в {json_path}")

# Запуск
if __name__ == "__main__":
    xml_file_to_json("report.xml", "report.json")