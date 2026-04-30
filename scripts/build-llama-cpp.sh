#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${ROOT_DIR}/.cache/llama.cpp"
REPO_URL="${LLAMA_CPP_REPO:-https://github.com/ggml-org/llama.cpp.git}"
REPO_REF="${LLAMA_CPP_REF:-master}"
BIN_DIR="${ROOT_DIR}/bin"
CUDA_ARCH="${CMAKE_CUDA_ARCHITECTURES:-89}"

mkdir -p "${ROOT_DIR}/.cache"

if [[ ! -d "${BUILD_DIR}" ]]; then
  git clone --depth 1 --branch "${REPO_REF}" "${REPO_URL}" "${BUILD_DIR}"
else
# git -C "${BUILD_DIR}" fetch --depth 1 origin "${REPO_REF}"
  git -C "${BUILD_DIR}" reset --hard "origin/${REPO_REF}"
  git -C "${BUILD_DIR}" checkout "${REPO_REF}"
  git -C "${BUILD_DIR}" pull --ff-only origin "${REPO_REF}"
fi

cmake -S "${BUILD_DIR}" -B "${BUILD_DIR}/build" \
  -DGGML_CUDA=ON \
  -DLLAMA_BUILD_SERVER=ON \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CUDA_ARCHITECTURES="${CUDA_ARCH}"
cmake --build "${BUILD_DIR}/build" --config Release -j"$(nproc)"

mkdir -p "${BIN_DIR}"
cp -a \
  "${BUILD_DIR}/build/bin/llama-server" \
  "${BUILD_DIR}/build/bin/libggml-base.so"* \
  "${BUILD_DIR}/build/bin/libggml-cpu.so"* \
  "${BUILD_DIR}/build/bin/libggml-cuda.so"* \
  "${BUILD_DIR}/build/bin/libggml.so"* \
  "${BUILD_DIR}/build/bin/libllama.so"* \
  "${BUILD_DIR}/build/bin/libmtmd.so"* \
  "${BIN_DIR}/"

echo "llama-server runtime bundle copied to ${BIN_DIR}"
