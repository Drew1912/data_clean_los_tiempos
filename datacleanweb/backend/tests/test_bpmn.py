from collections import defaultdict, deque
from pathlib import Path

from lxml import etree

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "docs/fase_1/diagramas/to_be_v2.bpmn"
NS = {"b": "http://www.omg.org/spec/BPMN/20100524/MODEL", "d": "http://www.omg.org/spec/BPMN/20100524/DI"}


def test_bpmn_validates_against_official_omg_xsd():
    parser = etree.XMLParser(no_network=True, resolve_entities=False)
    schema = etree.XMLSchema(etree.parse(str(Path(__file__).parent / "schemas/bpmn/BPMN20.xsd"), parser))
    schema.assertValid(etree.parse(str(PATH), parser))


def test_bpmn_references_lanes_and_reachable_end_events():
    tree = etree.parse(str(PATH))
    ids = tree.xpath("//@id")
    assert len(ids) == len(set(ids))
    assert len(tree.xpath("//b:participant", namespaces=NS)) == 1
    assert len(tree.xpath("//b:lane", namespaces=NS)) == 4
    process = tree.find("b:process", NS)
    assert process.get("isExecutable") == "false"
    flow_nodes = {n.get("id") for n in process if n.tag.rsplit("}", 1)[-1] in {"startEvent", "endEvent", "userTask", "serviceTask", "exclusiveGateway", "parallelGateway"}}
    refs = tree.xpath("//b:lane/b:flowNodeRef/text()", namespaces=NS)
    assert set(refs) == flow_nodes and len(refs) == len(set(refs))
    graph = defaultdict(list)
    for flow in tree.xpath("//b:sequenceFlow", namespaces=NS):
        a, b = flow.get("sourceRef"), flow.get("targetRef")
        assert a in flow_nodes and b in flow_nodes
        graph[a].append(b)
    seen, queue = set(), deque(["Start"])
    while queue:
        item = queue.popleft()
        if item not in seen:
            seen.add(item)
            queue.extend(graph[item])
    assert seen == flow_nodes
    assert {"End", "End_Rechazo"} <= seen
    shapes = {n.get("bpmnElement") for n in tree.xpath("//d:BPMNShape", namespaces=NS)}
    assert flow_nodes <= shapes
    edges = {n.get("bpmnElement") for n in tree.xpath("//d:BPMNEdge", namespaces=NS)}
    assert edges == {n.get("id") for n in tree.xpath("//b:sequenceFlow", namespaces=NS)}
    documentation = " ".join(tree.xpath("//b:documentation/text()", namespaces=NS))
    for i in range(1, 13): assert f"RF-{i:02}" in documentation
