from enum import Enum


class Quantization(str, Enum):
    FP16 = "fp16"
    BF16 = "bf16"
    INT8 = "int8"
    AWQ = "awq"
    GPTQ = "gptq"
    GGUF_Q4 = "gguf_q4"
    GGUF_Q5 = "gguf_q5"
    GGUF_Q8 = "gguf_q8"
