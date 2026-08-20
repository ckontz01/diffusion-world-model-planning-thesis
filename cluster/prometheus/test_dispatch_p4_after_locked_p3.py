#!/usr/bin/env python3

import hashlib
import json
import sys
import tempfile
from pathlib import Path

import dispatch_p4_after_locked_p3 as dispatch


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    with tempfile.TemporaryDirectory(prefix="p4-dispatch-test-") as raw_root:
        root = Path(raw_root)
        scripts = root / "scripts"
        promotion_dir = root / "promotion"
        scripts.mkdir()
        promotion_dir.mkdir()

        learned_launcher = scripts / "learned.slurm"
        aggregate_launcher = scripts / "aggregate.slurm"
        baseline_launcher = scripts / "baseline.slurm"
        for path in (learned_launcher, aggregate_launcher, baseline_launcher):
            path.write_text("#!/usr/bin/env bash\n", encoding="utf-8")

        audit = promotion_dir / "audit.h5"
        audit.write_bytes(b"synthetic locked audit")
        manifest = {
            "status": "ok",
            "classification": "p3_locked_scorer_audit_and_promotion",
            "partition": "P3-locked",
            "output_h5_sha256": sha256(audit),
            "promoted_arms": ["M2"],
            "promotion": {
                "M1": {"promoted": False},
                "M2": {"promoted": True},
                "M3": {"promoted": False},
            },
        }
        manifest_path = promotion_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        provenance = promotion_dir / "provenance.txt"
        provenance.write_text("synthetic_test=true\n", encoding="utf-8")
        inventory = promotion_dir / "checksums.sha256"
        inventory.write_text(
            "".join(
                "{}  {}\n".format(sha256(path), path.name)
                for path in (audit, manifest_path, provenance)
            ),
            encoding="utf-8",
        )

        dispatch.ROOT = root
        dispatch.PROMOTION_DIR = promotion_dir
        dispatch.LEARNED_LAUNCHER = learned_launcher
        dispatch.AGGREGATE_LAUNCHER = aggregate_launcher
        dispatch.BASELINE_LAUNCHER = baseline_launcher
        dispatch.EXPECTED_LAUNCHER_HASHES = {
            path: sha256(path)
            for path in (learned_launcher, aggregate_launcher, baseline_launcher)
        }

        observed = []
        next_job = iter((400001, 400002))

        def fake_checked_output(arguments):
            observed.append(arguments)
            if arguments[:4] == ["/usr/bin/scontrol", "show", "job", "-o"]:
                return "JobId={} Command={}".format(
                    dispatch.BASELINE_ARRAY_JOB_ID, baseline_launcher
                )
            if arguments[:2] == ["/usr/bin/sbatch", "--parsable"]:
                return str(next(next_job))
            raise AssertionError("unexpected command: {!r}".format(arguments))

        dispatch.checked_output = fake_checked_output
        output = root / "dispatch.json"
        sys.argv = ["dispatch_p4_after_locked_p3.py", "--output-json", str(output)]
        dispatch.main()

        receipt = json.loads(output.read_text(encoding="utf-8"))
        assert receipt["promoted_arms"] == ["M2"]
        assert receipt["learned_array_jobs"] == {"M2": 400001}
        assert receipt["aggregate_job_id"] == 400002
        assert receipt["submissions"][0]["afterok"] == dispatch.BASELINE_ARRAY_JOB_ID
        assert receipt["submissions"][1]["afterok"] == 400001
        assert any("METHOD=M2" in value for value in observed[1])
        assert all("METHOD=M1" not in value for command in observed for value in command)
        assert all("METHOD=M3" not in value for command in observed for value in command)

    print("synthetic_p4_dispatch_gate_test=ok")


if __name__ == "__main__":
    main()
