import json
import subprocess
import sys
import textwrap
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "prepare_review_context.py"


def write_file(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).strip() + "\n", encoding="utf-8")


def load_json_yaml(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class PrepareReviewContextTests(unittest.TestCase):
    def create_minimal_extraction(self, root: Path) -> Path:
        extraction = root / ".xperf_atdsl_extraction"

        write_file(
            extraction / "reports" / "function_index.yaml",
            """
            function_index:
              functions:
                - canonical_name: FiaBlockCubeNonQuantGqa<FIAT,Config>::ComputeMm2
                  owner: FiaBlockCubeNonQuantGqa
                  owner_qualified: FiaBlockCubeNonQuantGqa<FIAT,Config>
                  owner_template_args: [FIAT, Config]
                  template_params: [template<typename FIAT,typename Config>]
                  variant: gqa
                  stage: mm2
                  file: op_kernel/fia_block_cube_nonquant_gqa_sink.h
                  line_range: {start: 1113, end: 1240}
                  extraction_level: deep
                - canonical_name: FiaBlockCubeNonQuantMla<FIAT>::ComputeMm2
                  owner: FiaBlockCubeNonQuantMla
                  owner_qualified: FiaBlockCubeNonQuantMla<FIAT>
                  owner_template_args: [FIAT]
                  template_params: [template<typename FIAT>]
                  variant: mla
                  stage: mm2
                  file: op_kernel/fia_block_cube_nonquant_mla_sink.h
                  line_range: {start: 502, end: 521}
                  extraction_level: deep
                - canonical_name: FiaBlockCubeNonQuantMla<FIAT>::ProcessMm2
                  owner: FiaBlockCubeNonQuantMla
                  owner_qualified: FiaBlockCubeNonQuantMla<FIAT>
                  owner_template_args: [FIAT]
                  template_params: [template<typename FIAT>]
                  variant: mla
                  stage: mm2
                  file: op_kernel/fia_block_cube_nonquant_mla_sink.h
                  line_range: {start: 851, end: 1077}
                  extraction_level: deep
            """,
        )

        write_file(
            extraction / "reports" / "critical_path_annotations.yaml",
            """
            critical_path_annotations:
              stages:
                - stage: gqa.mm2
                  canonical_name: FiaBlockCubeNonQuantGqa<FIAT,Config>::ComputeMm2
                  variant: gqa
                  deep_annotation: annotations/functions/deep/gqa_compute_mm2.yaml
                - stage: mla.mm2
                  canonical_name: FiaBlockCubeNonQuantMla<FIAT>::ComputeMm2
                  variant: mla
                  deep_annotation: annotations/functions/deep/mla_compute_mm2.yaml
                - stage: mla.mm2.process
                  canonical_name: FiaBlockCubeNonQuantMla<FIAT>::ProcessMm2
                  variant: mla
                  deep_annotation: annotations/functions/deep/mla_process_mm2.yaml
            """,
        )

        for name in ["gqa_compute_mm2", "mla_compute_mm2", "mla_process_mm2"]:
            write_file(
                extraction / "annotations" / "functions" / "deep" / f"{name}.yaml",
                f"""
                function_annotation:
                  canonical_name: {name}
                  stage: mm2
                  evidence: op_kernel/example.h:1-9
                  suggested_dsl_fields:
                    - path: pipeline.stage_graph
                      evidence: op_kernel/example.h:1-9
                """,
            )

        write_file(
            extraction / "cards" / "optimization_cards.yaml",
            """
            optimization_cards:
              - id: OC-GQA-MM2
                title: GQA MM2 reuse
                evidence:
                  - op_kernel/fia_block_cube_nonquant_gqa_sink.h:1138-1222
                confidence: high
            """,
        )

        write_file(
            extraction / "dsl" / "suggested_dsl_sections.yaml",
            """
            suggested_dsl_sections:
              - name: pipeline.stage_graph
                fields:
                  - path: pipeline.stages[].canonical_name
                    evidence: reports/function_index.yaml
                    confidence: high
            """,
        )

        return extraction

    def test_generates_inventory_cross_reference_and_critical_coverage(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            extraction = self.create_minimal_extraction(root)
            output = root / "stage1_review"

            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--input", str(extraction), "--output", str(output)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            evidence_pack = load_json_yaml(output / "evidence_pack.yaml")
            inventory = load_json_yaml(output / "inventory.yaml")
            cross_reference = load_json_yaml(output / "cross_reference.yaml")

            self.assertEqual(inventory["counts"]["indexed_functions"], 3)
            self.assertEqual(inventory["counts"]["deep_annotations"], 3)
            self.assertTrue(evidence_pack["critical_coverage"]["required_items"]["gqa.mm2"]["present"])
            self.assertTrue(evidence_pack["critical_coverage"]["required_items"]["mla.mm2"]["present"])
            self.assertTrue(evidence_pack["critical_coverage"]["required_items"]["mla.mm2.process"]["present"])
            self.assertEqual(cross_reference["function_to_annotation"]["FiaBlockCubeNonQuantGqa<FIAT,Config>::ComputeMm2"]["level"], "deep")
            self.assertTrue(evidence_pack["template_identity_coverage"]["critical_functions"]["FiaBlockCubeNonQuantMla<FIAT>::ProcessMm2"]["complete"])

    def test_missing_function_index_is_blocking_but_not_fatal(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            extraction = root / ".xperf_atdsl_extraction"
            write_file(
                extraction / "cards" / "optimization_cards.yaml",
                """
                optimization_cards:
                  - id: OC-ONLY
                    evidence:
                      - op_kernel/example.h:1-2
                """,
            )
            output = root / "stage1_review"

            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--input", str(extraction), "--output", str(output)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            evidence_pack = load_json_yaml(output / "evidence_pack.yaml")
            self.assertIn("missing_function_index", evidence_pack["blocking_findings"])
            self.assertEqual(evidence_pack["inventory"]["counts"]["optimization_cards"], 1)


if __name__ == "__main__":
    unittest.main()
