# Training data

`dataset_generator.py` creates a reproducible synthetic dataset with six balanced classes: `benign`, `prompt_injection`, `jailbreak`, `system_prompt_extraction`, `data_exfiltration`, and `tool_abuse`.

Run `python dataset_generator.py` from this directory to regenerate `train.csv` (5,400 rows) and `test.csv` (600 rows).

Synthetic data is appropriate for a hackathon demonstration; production systems should use curated, reviewed, and continuously evaluated real-world samples.
