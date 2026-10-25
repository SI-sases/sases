\# Training Manifest



Records complete metadata for every training run to guarantee reproducibility.



\## Why this exists



SASES promises that "self-iteration leads to capability improvement." But if the training recipe is not recorded, no run can be reproduced, and it becomes impossible to answer "why is this run better than the last one?"



\## Usage



\### At the start of training



```python

from training\_manifest import start\_run



run = start\_run()

run.record\_data("finetune\_474.jsonl")

run.record\_benchmark("eval\_benchmark.jsonl")

run.record\_config(

&#x20;   base\_model="TinyLlama/TinyLlama-1.1B-Chat-v1.0",

&#x20;   training\_format="User: ...",

&#x20;   collator="DataCollatorForLanguageModeling",

&#x20;   max\_length=256,

&#x20;   lora\_r=8,

&#x20;   lora\_alpha=32,

&#x20;   learning\_rate=2e-4,

&#x20;   num\_epochs=3,

&#x20;   random\_seed=42,

)

At the end of training

python

from training\_manifest import finalize



finalize("lora\_474\_final")   # path to the LoRA output directory

This writes lora\_474\_final/training\_manifest.json with the full record.



Manifest fields

Field	Description

run\_id	UUID, unique identifier

started\_at / finished\_at	UTC timestamps

environment	Python / torch / transformers / peft / datasets versions + GPU info

data	Data file path, SHA256, sample count

benchmark	Evaluation set SHA256

training\_config	Model, format, collator, hyperparameters, random seed

result	Optional evaluation metrics filled in after training

Archiving convention

Every LoRA directory should contain training\_manifest.json. When archiving to GitHub:



LoRA weights (optional; large files go to HuggingFace)



training\_manifest.json (required)



Training data used (optional)



Historical lesson

September 2026: SASES could not reproduce the historical 474 LoRA (88% → only 23% when retrained). The cause: the training recipe was never recorded, so it was impossible to determine what collator, loss mask, random seed, or transformers version the original run used.



This module exists to prevent that class of problem.

