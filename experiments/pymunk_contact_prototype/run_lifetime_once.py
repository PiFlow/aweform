"""One-shot gate-checked v2 lifetime; never called by tests or CI."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import cast

from .organism_lifetime import run_once, run_reference_once
from .run_corrected_contact_check import check_frozen_tree
from .run_diagnostics import EXPECTED_OUTPUT, _canonical, sha256

EXPECTED_RESULTS = EXPECTED_OUTPUT
EXPECTED_LIFETIME = Path("experiments/pymunk_contact_prototype/results-v2/lifetime")


def validate_lifetime_gate(results: dict[str, object], head: str) -> None:
    if (
        results.get("executable_sha") != head
        or results.get("essential_B_pass") is not True
    ):
        raise RuntimeError(
            "exact frozen executable/B gate mismatch; STOP before lifetime"
        )


def _preflight_paths(results: Path, output: Path) -> None:
    if results.resolve() != EXPECTED_RESULTS.resolve():
        raise RuntimeError(
            f"lifetime must consume the v2 result path {EXPECTED_RESULTS}"
        )
    if output.resolve() != EXPECTED_LIFETIME.resolve():
        raise RuntimeError(f"lifetime output must be the new path {EXPECTED_LIFETIME}")
    if output.exists():
        raise FileExistsError("one-shot lifetime output exists; never rerun")


def run_lifetime(results_path: Path, output: Path) -> dict[str, object]:
    # All path/B/SHA gates run before an organism or reference can be constructed.
    _preflight_paths(results_path, output)
    head = check_frozen_tree(allow_output=True)
    result_path = results_path / "results.json"
    if not result_path.is_file():
        raise RuntimeError("frozen corrected contact result is missing; STOP")
    results = cast(
        dict[str, object], json.loads(result_path.read_text(encoding="utf-8"))
    )
    validate_lifetime_gate(results, head)
    output.mkdir(parents=True, exist_ok=False)
    marker = output / "LIFETIME_STARTED"
    marker.write_text(
        f"head={head}\nresults_sha256={sha256(result_path)}\n", encoding="ascii"
    )
    # Exactly one Pymunk lifetime and its separately matched D-058 reference.
    pymunk_lifetime = run_once()
    reference = run_reference_once()
    artifact_data: dict[str, object] = {
        "schema_version": 2,
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
    artifact = output / "lifetime.json"
    artifact.write_bytes(_canonical(artifact_data) + b"\n")
    (output / "SHA256SUMS").write_text(
        f"{sha256(artifact)}  lifetime.json\n", encoding="ascii"
    )
    marker.write_text(
        f"head={head}\nresults_sha256={sha256(result_path)}\ncompleted=1\n",
        encoding="ascii",
    )
    return artifact_data


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-organism-once", action="store_true")
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.run_organism_once:
        parser.error("explicit --run-organism-once is required")
    result = run_lifetime(args.results, args.output)
    pymunk = cast(dict[str, object], result["pymunk_lifetime"])
    reference = cast(dict[str, object], result["matched_reference_lifetime"])
    print(
        json.dumps(
            {
                "transitions": pymunk["transitions"],
                "reference_transitions": reference["transitions"],
                "output": str(args.output / "lifetime.json"),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
