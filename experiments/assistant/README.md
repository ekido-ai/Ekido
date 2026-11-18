# Assistant evaluation

`score.py` evaluates a configured assistant endpoint against the independently
labelled `prompts.jsonl` set. First run `validate_prompt_set.py` on that set.
Provide a JSON map from each recipe ID in the allowed cases to an authorized
dataset ID. Set `EKIDO_ASSISTANT_API_KEY` in the environment to a `jobs`-scoped
key; do not put it in the command, dataset map or output file.

```sh
python -I experiments/assistant/score.py --url https://example.invalid/sepolia \
  --prompts experiments/assistant/prompts.jsonl --dataset-map /private/dataset-map.json \
  --out experiments/results/assistant/run.json
```

Use an actual authorized API URL instead of the placeholder. HTTPS is required
except for numeric loopback HTTP. Redirects and environment proxies are disabled.
The scorer preflights all mappings, fails without overwriting existing results,
and stops on a transport failure without claiming a completed score. Results
include the prompt-set hash, per-case prompt and response hashes, structural
valid-spec rate, expected recipe/language/label match rate, and each refusal or
miss. They omit prompt and response bodies; use synthetic prompts only.

The 90% target applies to structurally valid previews. Report the separate
expected-match rate as well: a valid but wrong recipe is not a correct answer.
`review` is recorded separately and does not count as an explicit refusal.
Model screening and passing this test do not constitute human policy approval.
