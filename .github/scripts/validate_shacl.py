import json
import sys
from pathlib import Path

from pyshacl import validate
from rdflib import Graph

OPENAPI_VER_DIR = Path("openapi/ver")
SHACL_DIR = Path("data-model/shacl")


def load_shapes(version):
    shapes_path = SHACL_DIR / version / "shacl.ttl"
    if not shapes_path.exists():
        return None
    g = Graph()
    g.parse(str(shapes_path), format="turtle")
    return g


def validate_file(json_path, shapes_graph):
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    data_graph = Graph()
    data_graph.parse(data=json.dumps(data), format="json-ld")
    if len(data_graph) == 0:
        return False, "Parsed RDF graph is empty (context resolution may have failed)"
    conforms, _, results_text = validate(
        data_graph=data_graph, shacl_graph=shapes_graph, debug=False
    )
    return conforms, results_text


def main():
    failures = []
    versions_found = 0

    for version_dir in sorted(OPENAPI_VER_DIR.iterdir()):
        sample_data_dir = version_dir / "sample_data"
        json_files = sorted(sample_data_dir.glob("**/*.json")) if sample_data_dir.is_dir() else []
        if not json_files:
            continue

        shapes_graph = load_shapes(version_dir.name)

        versions_found += 1
        for json_path in json_files:
            conforms, results_text = validate_file(json_path, shapes_graph)
            if conforms:
                print(f"PASS {json_path}")
            else:
                print(f"FAIL {json_path}\n{results_text}")
                failures.append(json_path)

    print(f"\n{versions_found} versions validated, {len(failures)} failures")
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
