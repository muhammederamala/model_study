"""Check grounding behavior on real Spider schemas and observed values."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from ground_question import ground, load_catalog, load_reviewed_notes
from run_grounded_eval import prompt_for


class GroundingTests(unittest.TestCase):
    def test_two_named_ships_preserve_both_values_and_bridge(self):
        question = "List the battle name and date that lost Lettice and HMS Atalanta"
        result = ground(question, load_catalog("battle_death"))
        values = {(hit["table"], hit["column"], hit["value"])
                  for hit in result["value_matches"]}
        self.assertIn(("ship", "name", "Lettice"), values)
        self.assertIn(("ship", "name", "HMS Atalanta"), values)
        self.assertTrue(any(edge["from_table"] == "ship" and edge["to_table"] == "battle"
                            for edge in result["join_paths"]))

    def test_country_value_points_to_country_not_city(self):
        result = ground("Which continent is Anguilla in?", load_catalog("world_1"))
        values = {(hit["table"], hit["column"]) for hit in result["value_matches"]
                  if hit["value"] == "Anguilla"}
        self.assertIn(("country", "Name"), values)
        self.assertNotIn(("city", "Name"), values)

    def test_ambiguous_value_keeps_multiple_candidates(self):
        result = ground("For a volvo model, how many cylinders?", load_catalog("car_1"))
        columns = {(hit["table"], hit["column"]) for hit in result["value_matches"]}
        self.assertIn(("car_makers", "Maker"), columns)
        self.assertIn(("car_names", "Model"), columns)

    def test_quoted_numeric_text_is_grounded_as_a_value(self):
        result = ground("Which ships have tonnage '225'?", load_catalog("battle_death"))
        values = {(hit["table"], hit["column"], hit["value"])
                  for hit in result["value_matches"]}
        self.assertIn(("ship", "tonnage", "225"), values)

    def test_question_word_does_not_match_person_surname(self):
        question = "List the first name and birth date of players from USA."
        result = ground(question, load_catalog("wta_1"))
        self.assertFalse(any(hit["value"] == "Date" for hit in result["value_matches"]))
        self.assertTrue(any(hit["value"] == "USA" for hit in result["value_matches"]))

    def test_parallel_airport_joins_are_both_visible(self):
        question = "Which airlines have departures from CVO but not APG airports?"
        result = ground(question, load_catalog("flight_2"))
        join_columns = {edge["from_column"] for edge in result["join_paths"]}
        self.assertIn("SourceAirport", join_columns)
        self.assertIn("DestAirport", join_columns)

    def test_catalog_is_marked_source_grounded(self):
        catalog = load_catalog("battle_death")
        self.assertFalse(catalog["source"]["questions_or_gold_sql_used"])
        self.assertEqual(catalog["status"], "machine_derived_needs_domain_review")

    def test_raw_catalog_does_not_assert_unverified_grain_or_internal_table(self):
        catalog = load_catalog("world_1")
        self.assertNotIn("sqlite_sequence", catalog["entities"])
        self.assertNotIn("grain", catalog["entities"]["countrylanguage"])

    def test_reviewed_notes_are_scoped_to_database(self):
        flight = load_reviewed_notes("flight_2")
        self.assertIn("leading space", flight)
        self.assertNotIn("country.Capital", flight)
        self.assertIn("country.Capital", load_reviewed_notes("world_1"))

    def test_runner_prompt_uses_grounding_and_excludes_reference_sql(self):
        import json

        examples = json.loads((ROOT / "data/eval_sample.json").read_text())
        example = next(ex for ex in examples if ex["db_id"] == "flight_2")
        prompt, context = prompt_for(example)
        self.assertIn("leading space", context)
        self.assertIn("### SQL Query:", prompt)
        self.assertIn("### Database Schema:", prompt)
        self.assertNotIn(example["gold_sql"], prompt)

    def test_all_spider_dev_prompts_build_from_scoped_context(self):
        import json

        examples = json.loads((ROOT / "data/eval_sample.json").read_text())
        self.assertEqual(len(examples), 1032)
        self.assertEqual(len({ex["db_id"] for ex in examples}), 20)
        for example in examples:
            with self.subTest(id=example["id"]):
                prompt, context = prompt_for(example)
                self.assertIn(load_reviewed_notes(example["db_id"]), context)
                self.assertIn(example["question"], prompt)
                self.assertNotIn(example["gold_sql"], prompt)


if __name__ == "__main__":
    unittest.main()
