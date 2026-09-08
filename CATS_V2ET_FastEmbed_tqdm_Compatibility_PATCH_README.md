# CATS V2ET — FastEmbed tqdm Compatibility Patch

Purpose: make the validated local CPU embedding installation reproducible.

Validated runtime behavior:
- FastEmbed / ONNX Runtime on CPU
- sentence-transformers/all-MiniLM-L6-v2
- 384-dimensional vectors
- no PyTorch/CUDA dependency
- local embedding smoke test PASS

The initial unpinned dependency resolution installed tqdm 4.70.0, which caused the installed Hugging Face Hub path to fail importing `tqdm` from `tqdm.auto` in this environment. The working environment was restored with tqdm 4.69.1.

This patch only pins the local embedding dependency set. It does not change CATS architecture or runtime code.
