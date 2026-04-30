FROM nvidia/cuda:12.6.3-devel-ubuntu24.04 AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    cmake \
    curl \
    git \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*
RUN ln -sf /usr/local/cuda/lib64/stubs/libcuda.so /usr/lib/x86_64-linux-gnu/libcuda.so.1

WORKDIR /build
COPY .cache/llama.cpp /build/llama.cpp
WORKDIR /build/llama.cpp
RUN rm -rf build && \
    cmake -S . -B build \
    -DGGML_CUDA=ON \
    -DLLAMA_BUILD_SERVER=ON \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_CUDA_ARCHITECTURES=89 && \
    cmake --build build --config Release -j"$(nproc)" --target llama-server

FROM nvidia/cuda:12.6.3-runtime-ubuntu24.04

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /build/llama.cpp/build/bin/ /opt/llama/bin/
COPY docker/data-plane/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8081

ENTRYPOINT ["/entrypoint.sh"]
