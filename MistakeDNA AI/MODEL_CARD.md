# MistakeDNA TinyLM 0.1 — model card

## Identity and origin

A custom decoder-only causal transformer written for this application and trained from random initialization. No pretrained language model, downloaded tokenizer, model-hub asset, hosted AI API, distillation teacher or existing foundation-model weights were used in training or inference. PyTorch is the training framework; NumPy is the inference framework. Those are existing software libraries, not pretrained language models.

This is a tiny neural language-model demonstration. It is **not an LLM in the usual large-model sense** and is not presented as one.

## Architecture

- 137,984 learned parameters.
- Two pre-normalized transformer blocks, four attention heads, hidden width 64.
- Feed-forward width 256, tanh-approximate GELU, layer normalization.
- Learned positional embeddings, causal attention, tied token embedding/output weights.
- 400-token vocabulary built from the original corpus; 192-token context.
- No pretrained embeddings or tokenizer.
- Random seed 29; 2,200 AdamW steps; batch size 16; CPU training.
- Full training code: `training/train.py`; original corpus authoring: `training/build_corpus.py`.

## Data

40 original English lesson completions: four modes for each of ten skills across Chemical Equilibrium and Quadratic Equations. No student records were used for training. User chat/quiz activity does not automatically retrain the model. The supplied text corpus and all weights are included.

A keyword router chooses the structured topic/mode prompt. This is a disclosed deterministic preprocessing step, not language understanding learned by the transformer.

## Recorded results

The machine-readable `backend/app/offline_model/manifest.json` contains the exact model/corpus hashes and training measurements. For the included checkpoint:

- Initial training cross-entropy: 44.4875679016.
- Final training cross-entropy: 0.0001854880.
- Training perplexity: 1.0001855052.
- Greedy completions exactly matching authored text on **training prompts**: 40/40.

These measure memorization on the training material. There is no held-out evaluation, no demonstrated generalization and no evidence from a student learning trial. They must not be advertised as 100% tutoring accuracy.

## Generation and safeguards

Inference autoregressively computes next-token logits from the custom weights. It does not simply select a stored reply instead of running the network. Its output tokens are then compared with the corresponding authored response. If they do not match exactly, the app shows a labeled authored-reference fallback. Unsupported requests show a separately labeled authored scope message. This is an intentionally restrictive correctness gate, not an AI verifier.

Scores and mastery never depend on generated text. Student evidence is rendered separately from generated text. The server never sends inputs to an external model.

## Limits

The model mainly memorizes its 40 completions. It cannot reliably solve arbitrary problems, infer psychological causes, reason generally, interpret images or answer other chapters. Its tokenizer and generation limits are deliberately small. Input paraphrases are handled by lexical routing, not a trained semantic encoder. The wording can be repetitive or rigid. Further capability requires a larger licensed/original corpus, independent evaluations and more training resources—not relabeling this checkpoint as a large model.

## Operational footprint

The compressed weights file is approximately 507 KiB. NumPy inference uses CPU with one generation at a time. PyTorch is not installed in the runtime Docker image. The corpus and weight checksums are verified when loading. Missing/corrupted weights produce an explicit unavailable response, with quizzes still usable. The exact per-request timings measured in this environment are in `VALIDATION.md`; they are not a Render latency guarantee.

## Reproducibility

Retrain using the documented seed, architecture, corpus and command. Different BLAS/PyTorch/platform versions may produce slightly different numerical weights or hashes. Re-run the checked-completion and optional PyTorch/NumPy parity tests before using any new checkpoint.
