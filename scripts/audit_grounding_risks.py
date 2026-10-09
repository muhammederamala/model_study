"""Inventory unattempted grounded-eval questions using question and prompt context only.

Run from the repository root: python3 scripts/audit_grounding_risks.py
This is a triage aid, not a prediction of SQL correctness. It uses only question
text and prompt context, not gold or generated SQL, and never changes the run.
"""

import csv
import json
import re
from collections import Counter
from pathlib import Path

from ground_question import ground, load_catalog


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/eval_sample.json"
GROUNDED = ROOT / "results/runs/question_grounding/results_qwen25coder_14b.csv"
OUTPUT = ROOT / "insights/grounding_risk_inventory.csv"
CRITICAL = {"quantified_comparison", "language_negation", "language_intersection",
            "language_uniqueness", "language_disjunction", "year_disjunction",
            "winner_loser_roles", "tournament_intersection", "ranking_source_ambiguity",
            "population_grain_collision"}
FIELDS = ["id", "db_id", "question", "priority", "risk_tags", "prompt_evidence",
          "review_after_run"]


def flags(example):
    question = example["question"]
    q = question.lower()
    db = example["db_id"]
    context = ground(question, load_catalog(db))
    tags = []
    evidence = []
    actions = []

    def add(tag, evidence_text, action):
        tags.append(tag)
        evidence.append(evidence_text)
        actions.append(action)

    if db == "wta_1":
        has_winner = bool(re.search(r"\bwinn(?:er|ers|ing)|\bwon\b", q))
        has_loser = bool(re.search(r"\blos(?:er|ers|ing)", q))
        if has_winner or has_loser:
            add("winner_loser_roles", "matches has separate winner_id and loser_id roles",
                "Check the selected role, its player join, and whether match names or player names were requested.")
        if re.search(r"\brank(?:ing|s)?\b|rank points|ranking points|\btours\b", q):
            add("ranking_source_ambiguity", "matches has event rank/points; rankings has dated player rank/points/tours",
                "Check whether the question asks for match-time values or dated rankings and the intended player grain.")
        tourneys = {hit["value"] for hit in context["value_matches"]
                    if hit["table"] == "matches" and hit["column"] == "tourney_name"}
        if len(tourneys) > 1 or ("both" in q and "2013" in q and "2016" in q):
            add("tournament_intersection", "question names two tournaments or years",
                "Check that the same player satisfies both conditions; a single row cannot equal two values.")
        if "2013" in q and "2016" in q and re.search(r"\bor\b", q):
            add("year_disjunction", "question asks for matches in either of two years",
                "Check OR or IN rather than requiring one match to have both years.")
        if re.search(r"\b(?:most|highest|lowest|youngest|oldest|average|each|per|longest|three|greatest)\b|more than|greater than", q):
            add("aggregation_grain", "question needs a grouping, ordering, or extreme",
                "Check grouping key, deduplication, sort direction, and requested output columns.")
    elif db == "world_1":
        if re.search(r"\b(?:larger|greater|smaller|less|bigger)\b.*\bany\b", q):
            add("quantified_comparison", "question compares with 'any' country in another set",
                "Check ANY/ALL meaning and whether the threshold is MIN or MAX over the comparison set.")
        if re.search(r"\b(?:do not|does not|not)\b", q) and re.search(r"\b(?:language|english|speak|spoken|used)\b", q):
            add("language_negation", "countrylanguage has multiple rows per country",
                "Check NOT EXISTS or grouped negation; filtering out an English row is insufficient.")
        language_values = {hit["value"].lower() for hit in context["value_matches"]
                           if hit["table"] == "countrylanguage" and hit["column"] == "Language"}
        if len(language_values) > 1 and re.search(r"\b(?:both|and)\b", q):
            add("language_intersection", "two matched countrylanguage.Language values",
                "Check that both languages belong to the same country, not one language row.")
        if len(language_values) > 1 and re.search(r"\bor\b", q):
            add("language_disjunction", "two matched languages joined by OR",
                "Check OR semantics and deduplicate regions or countries as requested.")
        if re.search(r"\b(?:only used by a single country|spoken by only one country)\b", q):
            add("language_uniqueness", "language use must be counted per country",
                "Check whether the one-country count is global or restricted to republic governments.")
        if re.search(r"\b(?:official|predominantly|greatest percentage|most popular)\b", q):
            add("language_qualifier", "countrylanguage has IsOfficial and Percentage",
                "Check IsOfficial and/or Percentage against the exact wording.")
        population_tables = {hit["table"] for hit in context["column_matches"]
                             if hit["column"] == "Population"}
        if {"city", "country"} <= population_tables:
            add("population_grain_collision", "prompt suggests both city.Population and country.Population",
                "Check whether the answer concerns city, district, country, or continent population.")
        if re.search(r"\bdistrict\b", q):
            add("district_scope", "city.District identifies districts; city rows carry district population",
                "Check city.Population and whether district names require a country filter.")
        if re.search(r"\b(?:each|per|total|average|number of|most|top|largest|lowest|shortest|single)\b", q):
            add("aggregation_grain", "question needs aggregation, ranking, or a scoped count",
                "Check grouping key and one-to-many joins to city or countrylanguage.")
    if not any(context[key] for key in ("value_matches", "table_matches", "column_matches")):
        add("weak_lexical_grounding", "prompt reports no strong lexical or value match",
            "Review schema columns manually; no question-specific candidate was selected.")
    priority = "high" if CRITICAL.intersection(tags) or len(tags) >= 2 else "medium" if tags else "lower"
    return {"priority": priority, "risk_tags": "; ".join(tags),
            "prompt_evidence": "; ".join(evidence),
            "review_after_run": " ".join(dict.fromkeys(actions))}


def main():
    with GROUNDED.open(newline="") as handle:
        attempted = {row["id"] for row in csv.DictReader(handle)}
    examples = json.loads(DATASET.read_text())
    pending = [example for example in examples if str(example["id"]) not in attempted]
    rows = [{"id": example["id"], "db_id": example["db_id"],
             "question": example["question"], **flags(example)} for example in pending]
    rows.sort(key=lambda row: (row["db_id"], int(row["id"])))
    with OUTPUT.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved {len(rows)} unattempted questions to {OUTPUT.relative_to(ROOT)}; "
          f"priority counts: {dict(Counter(row['priority'] for row in rows))}")


if __name__ == "__main__":
    main()
