"""One-shot gate-checked lifetime; tests and CI must never invoke this CLI."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import cast

from .organism_lifetime import run_once, run_reference_once
from .run_diagnostics import _canonical, _check_clean_frozen_tree, sha256


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-organism-once", action="store_true")
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.run_organism_once:
        parser.error("explicit --run-organism-once is required")
    head = _check_clean_frozen_tree()
    result_path = args.results / "results.json"
    if not result_path.is_file():
        raise SystemExit("frozen fixed-command result is missing; STOP")
    results = cast(
        dict[str, object], json.loads(result_path.read_text(encoding="utf-8"))
    )
    if (
        results.get("executable_sha") != head
        or results.get("essential_B_pass") is not True
    ):
        raise SystemExit(
            "exact frozen executable/B gate mismatch; STOP before organism lifetime"
        )
    if args.output.exists():
        raise SystemExit("one-shot lifetime output/marker already exists; never rerun")
    args.output.mkdir(parents=True)
    marker = args.output / "LIFETIME_STARTED"
    marker.write_text(
        f"head={head}\nresults_sha256={sha256(result_path)}\n", encoding="ascii"
    )
    # Exactly one Pymunk lifetime and its separately matched D-058 reference.
    pymunk_lifetime = run_once()
    reference = run_reference_once()
    output = {
        "schema_version": 1,
        "executable_sha": head,
        "diagnostics_sha256": sha256(result_path),
        "protocol_sha256": results["protocol_sha256"],
        "pymunk_lifetime": pymunk_lifetime,
        "matched_reference_lifetime": reference,
        "trajectory_match_claim": False,
        "comparison_disclosure": (
            "Same seed/start/horizon/proposal stream; substrate trajectories and "
            "later actions may diverge; descriptive only."
        ),
    }
    artifact = args.output / "lifetime.json"
    artifact.write_bytes(_canonical(output) + b"\n")
    sums = f"{sha256(artifact)}  lifetime.json\n"
    (args.output / "SHA256SUMS").write_text(sums, encoding="ascii")
    marker.write_text(
        f"head={head}\nresults_sha256={sha256(result_path)}\ncompleted=1\n",
        encoding="ascii",
    )
    print(
        json.dumps(
            {
                "transitions": pymunk_lifetime["transitions"],
                "reference_transitions": reference["transitions"],
                "output": str(artifact),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
