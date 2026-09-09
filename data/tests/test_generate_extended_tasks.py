import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "scripts" / "generate_extended_tasks.py"


def load_generator():
    spec = importlib.util.spec_from_file_location("generate_extended_tasks", GENERATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ExtendedTaskGenerationTest(unittest.TestCase):
    def test_generates_large_schema_compatible_dataset_with_provenance(self):
        gen = load_generator()
        tasks = gen.generate_tasks()

        self.assertGreaterEqual(len(tasks), 240)
        self.assertEqual(len(tasks), len({task["id"] for task in tasks}))

        required = {
            "id",
            "category",
            "platform",
            "framework",
            "difficulty",
            "prompt",
            "constraints",
            "expected",
            "evaluation",
            "failure_modes",
            "source_refs",
            "scenario",
        }
        for task in tasks:
            self.assertTrue(required.issubset(task), task.get("id"))
            self.assertIn(task["difficulty"], {"easy", "medium", "hard"})
            self.assertGreaterEqual(len(task["constraints"]), 2, task["id"])
            self.assertGreaterEqual(len(task["expected"]), 1, task["id"])
            self.assertGreaterEqual(len(task["evaluation"]), 2, task["id"])
            self.assertGreaterEqual(len(task["failure_modes"]), 2, task["id"])
            self.assertGreaterEqual(len(task["source_refs"]), 1, task["id"])

        scenarios = {task["scenario"] for task in tasks}
        self.assertTrue(set(gen.REQUIRED_SCENARIOS).issubset(scenarios))

    def test_source_catalog_is_reportable_and_all_references_resolve(self):
        gen = load_generator()
        catalog = gen.source_catalog_by_id()
        tasks = gen.generate_tasks()

        self.assertGreaterEqual(len(catalog), 10)
        for source_id, source in catalog.items():
            self.assertIn("url", source, source_id)
            self.assertIn("license", source, source_id)
            self.assertIn("coverage", source, source_id)

        missing = sorted(
            {
                source_ref
                for task in tasks
                for source_ref in task["source_refs"]
                if source_ref not in catalog
            }
        )
        self.assertEqual([], missing)

    def test_jsonl_writer_outputs_one_valid_object_per_line(self):
        gen = load_generator()
        out = ROOT / "tmp_extended_tasks_test.jsonl"
        try:
            tasks = gen.generate_tasks()[:3]
            gen.write_jsonl(tasks, out)
            rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(tasks, rows)
        finally:
            if out.exists():
                out.unlink()


if __name__ == "__main__":
    unittest.main()
