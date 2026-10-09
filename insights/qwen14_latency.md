# Qwen 14B latency on the CPU-only laptop

The 1,032-request Spider baseline used `qwen2.5-coder:14b` through Ollama's
`/api/chat` endpoint, one request at a time, with temperature 0 and up to 300
generated tokens. This is the same input setup used for DeepSeek Coder V2.

| Metric | Qwen 14B |
|---|---:|
| Median | 14.2 s |
| Mean | 19.2 s |
| 90th percentile | 33.8 s |
| 95th percentile | 44.4 s |
| Execution accuracy | 808/1,032 (78.3%) |

Latency rises with answer length: median 5.9 s for outputs below 40 characters,
9.7 s for 40–79, 17.4 s for 80–159, and 29.6 s for 160–319. This suggests
token generation is a substantial cost, but the stored CSV has only total API
latency and output text. It does not record Ollama's load, prompt evaluation,
or generation durations, so it cannot prove which phase dominates.

Run `python3 scripts/profile_qwen_latency.py` on the laptop while no other
model evaluation is active. It sends 12 original benchmark prompts across
three databases, writes nothing to the results, and prints Ollama's load,
prompt, generation, and token-rate fields. The first request may include a
cold model load; warm-request medians exclude it.

## Speed options to test

1. **Cloud hardware:** the laptop benchmark is CPU-only. Benchmark the same
   Qwen model on the intended cloud instance, preferably with the full model
   resident in GPU memory. A 16 GB RAM budget by itself does not imply low
   latency. Record warm p50/p90/p95 and concurrent-request behavior.
2. **Keep it warm:** preload Qwen and use Ollama's `keep_alive` where memory
   permits. This removes repeated load time, but will not reduce generation
   time when the model is already resident.
3. **Shorter relevant prompts:** current requests include the complete
   data-only schema for one database. Question-specific schema selection could
   reduce prompt work, but must be tested for schema-omission errors. The
   current evaluator already groups questions by database to aid prefix cache.
4. **Smaller/faster route:** DeepSeek Coder V2's full run had 4.0 s median but
   68.9% accuracy, versus Qwen's 78.3%. It is a candidate for a speed/accuracy
   tradeoff, especially on simple questions, only after routing is validated.
5. **Quantization and output cap:** compare variants in a separate result
   folder before changing production. Lowering `num_predict=300` only helps
   responses that would otherwise reach the cap; most recorded SQL answers
   are short. Smaller quantization can affect accuracy.

Streaming can show partial text sooner, but SQL should only be executed after
the complete answer is available; streaming does not necessarily lower total
inference latency.
