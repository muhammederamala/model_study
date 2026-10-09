# Cloud Lambda text-to-SQL evaluation

After cloning, download the Spider databases separately as described in [data/README.md](../data/README.md); they are excluded from the planned Git contents. Cloud grading requires these local databases even though inference runs remotely. See [README.md](../README.md) for setup dependencies and pending path portability fixes. Keep authentication configuration outside the repository.

This path is separate from the local Ollama study. It reads the same fixed
1,032 Spider dev questions, sends one HTTP POST per question with `curl`, grades
returned SQL against the local SQLite database, and writes only to
`results/cloud/<run>/`. It never changes `results/runs/spider_baseline/` or
starts an Ollama model.

## Request contract to confirm with the teammate

The default JSON body is:

```json
{
  "id": 0,
  "db_id": "cre_Doc_Template_Mgt",
  "question": "...",
  "schema": "CREATE TABLE ...",
  "semantic_schema": "-- db_id: ...\nCREATE TABLE ...",
  "model": "optional-cloud-model-id"
}
```

`model` is omitted unless `--model` is supplied. `semantic_schema` comes from
`data/semantic_layer_dataonly/`, which uses database facts only. Gold SQL,
expected answers, and the local SQLite path are **never sent** to the endpoint.
If Lambda expects different field names or nesting, provide a JSON file with
`--request-template`, using exact string placeholders `$id`, `$db_id`,
`$question`, `$schema`, `$semantic_schema`, and `$model`. `$model` requires
`--model`. See [request_template.example.json](request_template.example.json).

The default response parser expects `{"sql": "SELECT ..."}`. Set
`--response-path body.sql` for nested JSON or `--response-path .` for plain SQL
text. An API Gateway stringified `body` is decoded automatically while walking
the dotted path. This is a configurable adapter until the teammate provides
the actual request and response examples.

## Usage

Inspect the first payload without any HTTP request:

```bash
python3 scripts/run_cloud_eval.py --run team_v1 --label cloud_qwen14 --model qwen14 --dry-run
```

Run one cloud model. Omit `--batch-size` to process all remaining questions in
one invocation; re-running the same command skips saved IDs:

```bash
python3 scripts/run_cloud_eval.py \
  --endpoint 'https://YOUR-ENDPOINT' \
  --run team_v1 --label cloud_qwen14 --model qwen14 \
  --response-path sql --batch-size 100
```

Use a different `--label` per cloud model and repeat for the teammate's
roster. The exact endpoint, model IDs, authentication, and response path must
be confirmed first. A new endpoint, model, request template, dataset, or
semantic schema requires a new run/label; the runner checks a configuration
fingerprint before resuming.

For authentication, put curl options such as `header = "Authorization: Bearer
..."` in a private file outside this project and pass `--curl-config
/path/to/private-curl-config`. Do not put tokens in the request template or
commit them. The endpoint may instead require a different authentication
mechanism; use the teammate's contract.

Results are written as `results/cloud/<run>/results_<label>.csv`, with a
separate `summary_<label>.json`. Request failures stop the run without saving a
wrong answer for that ID, so it can be retried. The summary includes overall
and complexity-bucket accuracy, SQL error count, latency, and a `complete`
flag. The local grader matches the existing Ollama grader for comparability;
it compares query results on one SQLite database, not Spider's official test
suite metric.
