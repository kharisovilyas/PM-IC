import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import networkx as nx
import plotly.graph_objects as go
import os

# --- Загрузка данных ---
def load_json(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

# --- Группировка по interval ---
def group_by_interval(data):
    structs = data["XMLDocument"]["task"].get("struct", [])
    if not isinstance(structs, list):
        structs = [structs]

    intervals = {}

    for struct in structs:
        interval_id = struct["@id"]
        time_start = struct.get("@start_time")
        time_end = struct.get("@end_time")

        # Объекты в этом интервале
        elem_list = struct.get("elem", [])
        if not isinstance(elem_list, list):
            elem_list = [elem_list]
        objects = [elem.get("@id") for elem in elem_list if elem.get("@id")]

        # Подсчёт процессов и транспортировок
        links = struct.get("link", [])
        if not isinstance(links, list):
            links = [links] if links else []

        processes = []
        transports = []

        for link in links:
            id1 = link.get("@id1")
            id2 = link.get("@id2")
            transport_1 = link.get("@transport_1")
            transport_3 = link.get("@transport_3")

            if transport_1 or transport_3:
                transports.append((id1, id2, transport_1 or transport_3))
            else:
                processes.append((id1, id2))

        intervals[interval_id] = {
            "time_start": time_start,
            "time_end": time_end,
            "objects": objects,
            "processes": processes,
            "transports": transports,
        }

    return intervals

# --- Группировка по типам ---
def group_by_type(data):
    task = data["XMLDocument"]["task"]

    result = {
        "process": {"total_time": 0, "count": 0, "objects": set(), "min_time": float("inf"), "max_time": -float("inf")},
        "transport": {"total_time": 0, "count": 0, "objects": set(), "min_time": float("inf"), "max_time": -float("inf")},
        "storage": {"count": 0, "objects": set()}
    }

    # Process
    process_list = task.get("process", {}).get("type", [])
    if not isinstance(process_list, list):
        process_list = [process_list]
    for p in process_list:
        time = p.get("@time")
        obj_id = p.get("@id")
        if isinstance(time, (int, float)):
            result["process"]["total_time"] += time
            result["process"]["min_time"] = min(result["process"]["min_time"], time)
            result["process"]["max_time"] = max(result["process"]["max_time"], time)
            result["process"]["count"] += 1
        if obj_id:
            result["process"]["objects"].add(obj_id)

    # Transport
    transport_list = task.get("transport", {}).get("type", [])
    if not isinstance(transport_list, list):
        transport_list = [transport_list]
    for t in transport_list:
        time = t.get("@time")
        obj_id = t.get("@id")
        if isinstance(time, (int, float)):
            result["transport"]["total_time"] += time
            result["transport"]["min_time"] = min(result["transport"]["min_time"], time)
            result["transport"]["max_time"] = max(result["transport"]["max_time"], time)
            result["transport"]["count"] += 1
        if obj_id:
            result["transport"]["objects"].add(obj_id)

    # Storage
    storage_list = task.get("storage", {}).get("type", [])
    if not isinstance(storage_list, list):
        storage_list = [storage_list]
    for s in storage_list:
        input_types = s.get("input", [])
        if not isinstance(input_types, list):
            input_types = [input_types]
        for inp in input_types:
            obj_id = inp.get("@id")
            if obj_id:
                result["storage"]["objects"].add(obj_id)
        result["storage"]["count"] += len(input_types)

    # Преобразуем множества в списки
    for key in result:
        result[key]["objects"] = list(result[key]["objects"])
        if key in ("process", "transport") and result[key]["count"] == 0:
            result[key]["min_time"] = None
            result[key]["max_time"] = None

    return result

# --- Извлечение flow данных ---
def extract_flows(data):
    plan = data["XMLDocument"]["report"].get("plan", {})
    flows = {}

    for key in plan:
        val = plan[key]
        if not isinstance(val, list):
            val = [val]
        for entry in val:
            if "#text" in entry and "@object" in entry and "@interval" in entry:
                obj = entry["@object"]
                interval = entry["@interval"]
                tag = key
                time = entry["#text"]

                if interval not in flows:
                    flows[interval] = {}
                if obj not in flows[interval]:
                    flows[interval][obj] = {}
                flows[interval][obj][tag] = time

    return flows

# --- Сохранение в Excel ---
def save_to_excel(grouped_by_type, interval_summary, flows, filename="analysis_report.xlsx"):
    with pd.ExcelWriter(filename, engine="openpyxl") as writer:
        # Типы (process, transport, storage)
        if grouped_by_type:
            pd.DataFrame([{
                "type": k,
                "total_time": v.get("total_time"),
                "count": v.get("count"),
                "min_time": v.get("min_time"),
                "max_time": v.get("max_time"),
                "objects": ", ".join(map(str, v.get("objects", [])))
            } for k, v in grouped_by_type.items()]).to_excel(writer, sheet_name="types", index=False)

        # Интервалы
        if interval_summary:
            pd.DataFrame([{
                "interval": k,
                "start": v.get("time_start"),
                "end": v.get("time_end"),
                "duration": v.get("time_end", 0) - v.get("time_start", 0),
                "objects": ", ".join(map(str, v.get("objects", [])))
            } for k, v in interval_summary.items() if v.get("time_start") and v.get("time_end")]).to_excel(
                writer, sheet_name="intervals", index=False
            )

        # Flows
        if flows:
            flow_rows = []
            for interval, objs in flows.items():
                for obj, tags in objs.items():
                    row = {"interval": interval, "object": obj}
                    row.update(tags)
                    flow_rows.append(row)
            if flow_rows:
                pd.DataFrame(flow_rows).to_excel(writer, sheet_name="flows", index=False)

    print(f"✅ Данные сохранены в {filename}")

# --- Построение графиков techchains (статичные) ---
def plot_techchains(data):
    chains = data["XMLDocument"]["report"]["techchains"].get("chain", [])
    if not isinstance(chains, list):
        chains = [chains]

    for i, chain in enumerate(chains):
        nodes = []
        edges = []

        prev_node = None
        for step in chain.values():
            if isinstance(step, dict) or (isinstance(step, list) and len(step) > 0 and isinstance(step[0], dict)):
                steps = step if isinstance(step, list) else [step]
                for s in steps:
                    name = f"{s.get('@type', '')}({s.get('@id', '')})"
                    nodes.append(name)
                    if prev_node:
                        edges.append((prev_node, name))
                    prev_node = name

        G = nx.DiGraph()
        G.add_nodes_from(nodes)
        G.add_edges_from(edges)

        plt.figure(figsize=(10, 4))
        pos = nx.spring_layout(G)
        nx.draw(G, pos, with_labels=True, node_size=600, font_size=10, node_color="lightgreen", arrows=True)
        plt.title(f"Технологическая цепочка {i+1}")
        plt.savefig(f"plots/techchain_{i+1}.png")
        plt.close()

    print("🖼️ Графики techchains сохранены")

# --- Построение интерактивного графа techchains ---
def plot_techchains_interactive(data):
    chains = data["XMLDocument"]["report"]["techchains"].get("chain", [])
    if not isinstance(chains, list):
        chains = [chains]

    G = nx.DiGraph()
    edge_labels = {}

    for chain in chains:
        steps = []
        for step in chain.values():
            if isinstance(step, dict):
                steps.append(step)
            elif isinstance(step, list):
                steps.extend(step)

        prev_node = None
        for step in steps:
            step_type = step.get("@type")
            obj_id = step.get("@object")
            to_obj = step.get("@to_object")
            time = step.get("#text")

            if step_type == "transport" and to_obj:
                from_node = str(obj_id)
                to_node = str(to_obj)
                label = f"transport<br>({time})"
                G.add_edge(from_node, to_node, label=label)
                edge_labels[(from_node, to_node)] = label
                prev_node = to_node
            elif step_type == "process":
                current_node = str(obj_id)
                label = f"process<br>({time})"
                if prev_node:
                    G.add_edge(prev_node, current_node, label=label)
                    edge_labels[(prev_node, current_node)] = label
                else:
                    G.add_node(current_node)
                prev_node = current_node

    pos = nx.spring_layout(G, k=0.5)

    edge_x = []
    edge_y = []
    edge_text = []

    for edge in G.edges(data=True):
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
        edge_text.append(edge_labels.get((edge[0], edge[1]), ""))

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        line=dict(width=2, color='gray'),
        hoverinfo='text',
        text=edge_text,
        mode='lines'
    )

    node_x = []
    node_y = []
    node_text = []

    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        node_text.append(node)

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode='markers+text',
        text=node_text,
        textposition='top center',
        hoverinfo='text',
        marker=dict(
            showscale=False,
            color='lightblue',
            size=30,
            line_width=2
        )
    )

    fig = go.Figure(
        data=[edge_trace, node_trace],
        layout=go.Layout(
            title='<br>⛓️ Интерактивная цепочка технологий',
            titlefont_size=16,
            showlegend=False,
            hovermode='closest',
            margin=dict(b=20, l=5, r=5, t=40),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
        )
    )

    fig.show()
    fig.write_html("techchains_interactive.html")
    print("✅ Интерактивный граф techchains сохранён как techchains_interactive.html")

# --- Основной запуск ---
if __name__ == "__main__":
    #os.makedirs("plots", exist_ok=True)

    data = load_json("report.json")
    grouped_by_type = group_by_type(data)
    interval_summary = group_by_interval(data)
    flows = extract_flows(data)

    save_to_excel(grouped_by_type, interval_summary, flows)

    #plot_techchains(data)
    #plot_techchains_interactive(data)