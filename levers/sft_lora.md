# Lever: per-client supervised fine-tuning with LoRA

- **Status:** planned; no training or results
- **Potential `--lever=` value after implementation:** `sft_lora`

## Target architecture

Keep one versioned Qwen base model and train an independent LoRA adapter for
each client. The adapter learns to decompose the client's questions into SQL
building blocks, call a read-only SQL tool when intermediate data is needed,
interpret its results, and compose the final answer. An authenticated client
ID selects the adapter. The client's current schema, database values, and
reviewed semantic definitions still go in the request context; adapter weights
do not replace live schema information. If a client uses multiple databases,
train and route by client unless measured results justify finer adapters.

Version every adapter with its exact base-model revision, tokenizer, prompt
format, training data, schema version, and held-out evaluation result. Isolate
client data and adapters from one another. The serving stack must support
adapter selection and measure load/switch latency; the current Ollama baseline
runner does not implement this routing.

## Training targets

The data needs two kinds of supervised examples:

1. **Building blocks:** a schema and small subquestion paired with its correct
   SQL, such as finding an entity, computing a threshold, or aggregating a
   group. These teach individual operations.
2. **Complete trajectories:** a user question and schema followed by assistant
   decomposition, SQL tool calls, actual read-only tool responses, further
   reasoning or calls when needed, and a final answer. These teach *when* to
   call tools, how to use their results, and when to stop. Training only on
   isolated SQL pairs would not teach this orchestration.

The training loss should target assistant actions and final answers, with
prompt and tool-result tokens masked. LoRA updates adapter weights while the
base model remains frozen. QLoRA quantizes the base during training to reduce
GPU memory use. Validate each trajectory by executing its SQL against the
correct database and reviewing its final answer; execution success alone does
not prove that a query answers the question.

## Runtime loop

Give the adapter the question, current schema, semantic definitions, and a
read-only `execute_sql` tool. The agent may answer directly for simple cases;
otherwise it breaks the problem into subquestions, issues bounded SQL calls,
examines the returned rows, and either continues or answers. Log calls and
intermediate results for review. A final answer may be a value or table for a
client workflow; retain a final SQL statement when evaluating on Spider 1.0.

## Client data and evaluation

Use expert-approved examples that cover joins, filters, aggregation, negation,
and business-specific metric definitions. Record the expected intermediate
subquestions, tool calls, tool results, and final answer for complex cases.
Hold out questions by template, workflow, or time period instead of memorized
paraphrases. Compare the tuned agent against both an untuned agent with the
same tools and a direct-SQL baseline; include previously correct questions.
Where labels are scarce, test schema grounding and retrieved examples before
training an adapter.

## Spider as a method check

`data/spider_data/train_spider.json` has 7,000 question/SQL pairs across 140
database IDs. `train_others.json` adds 1,659 pairs across 6 other databases.
Neither training file shares a database ID with the 20 dev databases. Begin
with `train_spider.json`; treat `train_others.json` as a separate ablation.
Never train on `dev.json`, `data/eval_sample.json` gold SQL, model outputs
corrected using dev gold, `data/question_patterns/`, or the full semantic
layer mined from dev answers.

Spider does not contain labeled examples for this project's real clients, nor
does it ship agent trajectories. Its training databases can act as simulated
clients. Derive candidate decompositions from train-split questions and gold
SQL, execute the proposed building-block queries, and review the trajectories
before training. Use the same schema and tool contract at training and
inference. The Spider dev databases have no training examples in this project,
so a dev-database adapter cannot be trained without contaminating the
benchmark. Report simulated-client agent results separately from the existing
single-query Spider dev baseline.

## Proposed experiment

1. Define the `execute_sql` input/output contract and bounded agent loop, then
   build a small set of reviewed building blocks and trajectories from one
   Spider train database. Hold out complete question patterns.
2. Run the same agent loop with untuned Qwen, then profile a Qwen 2.5 Coder 7B
   QLoRA adapter to verify trajectory formatting, assistant-only loss masking,
   GPU memory, and adapter loading. Its partial Spider dev run is unrelated.
3. Repeat across several simulated clients with enough examples, keeping each
   adapter and holdout separate. Measure final-answer accuracy, wrong-tool-call
   rate, SQL errors, calls per question, latency, and regressions.
4. Once client-approved examples exist, train a pilot adapter for one real
   client on a suitable GPU, then validate on that client's held-out questions.
   The CPU-only laptop is not a practical training target, and 16 GB deployment
   RAM does not imply adequate GPU memory for training.
5. Add authenticated adapter routing only after the pilot shows a useful gain.
   Keep the current Spider dev result as a separate cross-database benchmark.

## Verdict gate

Keep a client's adapter only if it improves that client's held-out final-answer
accuracy with acceptable latency and no major regression on simple questions.
The 90% Spider dev target is separate and is not an expected outcome of
client-specific LoRA.
