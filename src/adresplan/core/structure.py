"""Validate tree structure independently from network planning."""

from collections import Counter

from adresplan.core.models import Finding, NodeKind, Project, Segment, node_sort_key


def validate_structure(project: Project) -> tuple[Finding, ...]:
    """Collect malformed IDs, names, parent relationships and cycles without I/O."""
    findings: list[Finding] = []
    if not project.id.strip():
        findings.append(Finding(code="empty_project_id"))
    if not project.name.strip():
        findings.append(Finding(code="empty_project_name"))

    counts = Counter(node.id for node in project.nodes)
    by_id = {node.id: node for node in project.nodes if counts[node.id] == 1}
    for node_id in sorted(counts):
        if counts[node_id] > 1:
            findings.append(
                Finding(
                    code="duplicate_node_id",
                    node_id=node_id,
                    details=(("count", counts[node_id]),),
                )
            )

    expected_parent = {NodeKind.BUILDING: NodeKind.SITE, NodeKind.SEGMENT: NodeKind.BUILDING}
    for node in sorted(project.nodes, key=node_sort_key):
        if not node.id.strip():
            findings.append(Finding(code="empty_node_id", node_id=node.id))
        if not node.name.strip():
            findings.append(Finding(code="empty_node_name", node_id=node.id))
        if node.sort_order < 0:
            findings.append(Finding(code="negative_sort_order", node_id=node.id))
        if node.kind is NodeKind.SEGMENT and not isinstance(node, Segment):
            findings.append(Finding(code="segment_data_missing", node_id=node.id))
        if node.kind is NodeKind.SITE:
            if node.parent_id is not None:
                findings.append(Finding(code="site_has_parent", node_id=node.id))
        elif node.parent_id not in by_id:
            findings.append(Finding(code="missing_parent", node_id=node.id))
        elif by_id[node.parent_id].kind is not expected_parent[node.kind]:
            findings.append(Finding(code="invalid_parent_kind", node_id=node.id))

    # A visited path is bounded by the number of unique nodes, even for malformed input.
    for node in sorted(by_id.values(), key=node_sort_key):
        visited: set[str] = set()
        current_id: str | None = node.id
        while current_id is not None and current_id in by_id:
            if current_id in visited:
                findings.append(Finding(code="parent_cycle", node_id=node.id))
                break
            visited.add(current_id)
            current_id = by_id[current_id].parent_id
    return tuple(findings)
