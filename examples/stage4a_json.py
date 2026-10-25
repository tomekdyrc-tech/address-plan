"""Demonstrate JSON import, atomic export, recomputation and frozen project storage."""

from pathlib import Path

from adresplan.application.project_json import load_project, save_project
from adresplan.core.freeze import freeze

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    source = ROOT / "examples" / "stage4a_project.json"
    output = ROOT / ".tmp" / "stage4a"
    output.mkdir(parents=True, exist_ok=True)
    original = load_project(source)
    print(f"Projekt: {original.project.name}")
    print("Wynik:", "kompletny" if original.plan.is_complete else "z błędami")
    print("\nIPv4:")
    for allocation in original.plan.v4_allocations:
        print(f"  {allocation.node_id:<8} {allocation.network}")
    print("\nIPv6:")
    for allocation in original.plan.v6_allocations:
        print(f"  {allocation.node_id:<8} {allocation.network}")

    target = output / "project.json"
    save_project(target, original.project)
    restored = load_project(target)
    if restored != original:
        raise RuntimeError("JSON round-trip changed the project or plan")
    print("\nEksport i ponowny import: identyczny projekt i plan")
    frozen = freeze(original.project, original.plan)
    frozen_target = output / "project-frozen.json"
    save_project(frozen_target, frozen)
    restored_frozen = load_project(frozen_target)
    if restored_frozen.project != frozen or restored_frozen.plan != original.plan:
        raise RuntimeError("Frozen project round-trip changed the pins or plan")
    print("Zamrożone IPv4/IPv6 i infrastruktura: zachowane")
    print(f"Zapisano: {target}")
    print(f"Zapisano: {frozen_target}")


if __name__ == "__main__":
    main()
