\# SASES Self-Iteration Validation - Reproducibility Report



\## Summary



We attempted to reproduce the historical 474 LoRA (81% syntax pass rate) using the exact training script and data. Despite matching format, max\_length, and hyperparameters, the reproduction achieved only 23%.



\*\*Conclusion\*\*: The historical 474 LoRA was trained with an unknown recipe that cannot be reproduced from the provided script.



\## Full Experiment Matrix



| Model | Data | Format | max\_len | Syntax | Pass@1 | Notes |

|-------|------|--------|---------|--------|--------|-------|

| base | 0 | - | - | 12% | 0% | No fine-tuning |

| lora\_adapter\_474 | 474 | chat | - | 88% | 38.5% | Historical, unknown recipe |

| lora\_adapter\_474 | 474 | User: | - | 81% | 23.1% | Same model, User: eval |

| lora\_474\_chat | 474 | chat | 512 | 24% | 0% | Reproduced w/ chat format |

| lora\_730\_chat | 730 | chat | 512 | 29% | 15.4% | Reproduced w/ 730 data |

| lora\_474\_final | 474 | User: | 256 | 23% | 7.7% | Exact historical script |



\## Reproducible Findings



Only these results are reproducible with the documented script:



| Model | Data | Syntax |

|-------|------|--------|

| base | 0 | 12% |

| lora\_474\_chat | 474 | 24% |

| lora\_730\_chat | 730 | 29% |



\*\*The reproducible curve shows mild improvement (12% → 24% → 29%) as knowledge base grows.\*\*



\## Key Lesson for SASES



\*\*Self-iteration systems MUST record training metadata\*\*: collator type, loss mask strategy, random seed, transformers version, CUDA version. Without this, training is not reproducible.



\## Files



\- `results\_v6/` — final experiment data

\- `sases\_lora\_final.zip` — raw outputs

