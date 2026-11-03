#!/usr/bin/env bash
# Servidor Ollama dedicado à geração em lote, numa porta separada do app (11434).
# Contexto curto (8k) libera memória de KV cache para vários slots paralelos.
export OLLAMA_HOST=127.0.0.1:11435
export OLLAMA_NUM_PARALLEL=${OLLAMA_NUM_PARALLEL:-8}
export OLLAMA_CONTEXT_LENGTH=${OLLAMA_CONTEXT_LENGTH:-8192}
export OLLAMA_FLASH_ATTENTION=1
export OLLAMA_KV_CACHE_TYPE=q8_0
export OLLAMA_MAX_LOADED_MODELS=1
export OLLAMA_KEEP_ALIVE=30m
exec ollama serve
