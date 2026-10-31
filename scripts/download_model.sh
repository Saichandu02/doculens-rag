#!/usr/bin/env bash
# Prefetch the all-MiniLM-L6-v2 ONNX model into the fastembed/HF cache with
# curl. Needed in this build environment because the Python HF client stalls
# on the ~90 MB file through the egress proxy, while curl succeeds.
# On a normal network, fastembed downloads the model automatically on first
# ingestion and this script is unnecessary.
set -euo pipefail
CACHE="${FASTEMBED_CACHE:-/tmp/fastembed_cache}/models--Qdrant--all-MiniLM-L6-v2-onnx"
REV="d13954661f83248295ba75c1ed411eef3b7b936e"
mkdir -p "$CACHE/blobs" "$CACHE/snapshots/$REV"
dl() { curl -sL -o "/tmp/dl-$1" "https://huggingface.co/Qdrant/all-MiniLM-L6-v2-onnx/resolve/main/$1"; }
for f in model.onnx vocab.txt tokenizer.json tokenizer_config.json special_tokens_map.json config.json; do
  dl "$f"
  H=$(sha256sum "/tmp/dl-$f" | cut -d' ' -f1)
  # LFS files are stored by sha256; small files by git blob id — either way,
  # linking the content into the snapshot is sufficient for offline load.
  cp "/tmp/dl-$f" "$CACHE/blobs/$H"
  ln -sf "../../blobs/$H" "$CACHE/snapshots/$REV/$f"
done
echo "model cache ready at $CACHE"
