from numbers import Number
import xml.etree.ElementTree as ET
import json

def auto_cast(value):
    """Преобразует строку в int, float или оставляет как str."""
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

def xml_element_to_dict(element):
    """Рекурсивно преобразует XML-элемент в словарь."""
    if len(element) == 0 and not element.attrib:
        return auto_cast(element.text)

    node = {}

    # Атрибуты
    if element.attrib:
        node.update({f"@{key}": auto_cast(value) for key, value in element.attrib.items()})

    # Дети
    children = {}
    for child in element:
        child_data = xml_element_to_dict(child)

        if child.tag in children:
            if not isinstance(children[child.tag], list):
                children[child.tag] = [children[child.tag]]
            children[child.tag].append(child_data)
        else:
            children[child.tag] = child_data

    # Если нет детей, но есть текст — добавляем его как '#text'
    if not children and element.text and element.text.strip():
        node["#text"] = auto_cast(element.text)

    node.update(children)
    return node

def validate_full_structure(data):
    required_sections = ["task", "report"]
    missing = [sec for sec in required_sections if sec not in data.get("XMLDocument", {})]
    if missing:
        raise ValueError(f"❌ В XML отсутствуют обязательные секции: {missing}")

def analyze_full_report(data):
    task = data["XMLDocument"]["task"]
    report = data["XMLDocument"]["report"]

    # --- Общее время выполнения из <time> ---
    total_time = 0
    time_entries = report.get("plan", {}).get("time", [])
    
    if isinstance(time_entries, list):
        for entry in time_entries:
            if isinstance(entry, dict) and "#text" in entry:
                total_time += entry["#text"]
            elif isinstance(entry, (int, float)):
                total_time += entry
    elif isinstance(time_entries, dict):
        if "#text" in time_entries:
            total_time += time_entries["#text"]
        elif isinstance(time_entries, Number):
            total_time += time_entries

    # --- Количество элементов <elem> ---
    elem_count = 0
    struct_list = task.get("struct", [])
    if isinstance(struct_list, list):
        for struct in struct_list:
            elem_list = struct.get("elem", [])
            if isinstance(elem_list, list):
                elem_count += len(elem_list)
            elif isinstance(elem_list, dict):
                elem_count += 1

    # --- Количество селекторов ---
    selector_count = 0
    selectors = report.get("summary", {}).get("selectors", {}).get("selector", [])
    if isinstance(selectors, list):
        selector_count = len(selectors)
    elif isinstance(selectors, dict):
        selector_count = 1

    # --- Количество цепочек ---
    chain_count = 0
    chains = report.get("techchains", {}).get("chain", [])
    if isinstance(chains, list):
        chain_count = len(chains)
    elif isinstance(chains, dict):
        chain_count = 1

    print("\n📊 Анализ XML:")
    print(f"- Общее время выполнения из <time>: {total_time}")
    print(f"- Количество <elem> в <struct>: {elem_count}")
    print(f"- Количество <selector> в <summary>: {selector_count}")
    print(f"- Всего цепочек в <techchains>: {chain_count}")

def xml_file_to_json(xml_path, json_path="output_full.json"):
    tree = ET.parse(xml_path)
    root = tree.getroot()

    data = {root.tag: xml_element_to_dict(root)}

    validate_full_structure(data)
    analyze_full_report(data)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    print(f"\n✅ JSON сохранён в {json_path}")

# Запуск
if __name__ == "__main__":
    xml_file_to_json("report.xml", "report.json")