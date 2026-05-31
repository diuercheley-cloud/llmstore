import asyncio
import json
import os
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import get_settings
from app.services.mlops.training_job_registry import TrainingJobRegistry
from app.services.mlops.model_lineage import ModelLineage


GPU_TRAINING_SCRIPT = """
import json, os, sys
import torch
import torch.nn.functional as F
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer, DataCollatorForSeq2Seq
from peft import LoraConfig, get_peft_model, TaskType
from datasets import Dataset

def train():
    params = json.loads(sys.argv[1])
    model_name = params["base_model"]
    output_dir = params["output_dir"]
    learning_rate = float(params.get("learning_rate", 2e-4))
    num_epochs = int(params.get("num_epochs", 3))
    batch_size = int(params.get("batch_size", 4))
    max_length = int(params.get("max_length", 512))
    lora_r = int(params.get("lora_r", 8))
    lora_alpha = float(params.get("lora_alpha", 16))
    lora_dropout = float(params.get("lora_dropout", 0.1))

    print(f"=== GPU Fine-Tuning Started ===")
    print(f"Model: {model_name}")
    print(f"Device count: {torch.cuda.device_count()}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"Memory: {torch.cuda.get_device_properties(0).total_mem / 1e9:.1f} GB")

    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True,
    )

    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=lora_r,
        lora_alpha=lora_alpha,
        lora_dropout=lora_dropout,
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    data_path = params.get("dataset_path")
    if data_path and os.path.exists(data_path):
        with open(data_path) as f:
            raw = [json.loads(line) for line in f if line.strip()]
    else:
        raw = [{"text": f"Example training sample {i}"} for i in range(32)]
        print(f"Using {len(raw)} synthetic samples (no dataset found at {data_path})")

    def tokenize_fn(examples):
        return tokenizer(examples["text"], truncation=True, max_length=max_length, padding="max_length")

    dataset = Dataset.from_list(raw).map(tokenize_fn, batched=True)
    split = dataset.train_test_split(test_size=0.1)
    train_ds, eval_ds = split["train"], split["test"]

    args = TrainingArguments(
        output_dir=output_dir,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        num_train_epochs=num_epochs,
        learning_rate=learning_rate,
        bf16=torch.cuda.is_available(),
        logging_steps=1,
        eval_strategy="steps",
        eval_steps=10,
        save_strategy="epoch",
        report_to="none",
        remove_unused_columns=False,
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        tokenizer=tokenizer,
        data_collator=DataCollatorForSeq2Seq(tokenizer, pad_to_multiple_of=8),
    )

    trainer.train()
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)

    final_loss = trainer.state.log_history[-1].get("eval_loss", trainer.state.log_history[-2].get("eval_loss", 0))
    print(f"\\n=== Training Complete ===")
    print(f"Final eval loss: {final_loss:.4f}")
    print(f"Output saved to: {output_dir}")
    print(json.dumps({"final_loss": final_loss, "epochs": num_epochs, "output_dir": output_dir}))

if __name__ == "__main__":
    train()
"""


class FineTuningService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.settings = get_settings()
        self.job_registry = TrainingJobRegistry(session)
        self.lineage_service = ModelLineage(session)

    async def start_fine_tuning(
        self,
        model_name: str,
        dataset_version_id: uuid.UUID,
        provider: str = "mock",
        hyperparameters: Optional[Dict[str, Any]] = None,
        admin_user_id: Optional[uuid.UUID] = None,
    ) -> uuid.UUID:
        job = await self.job_registry.create_job(
            model_name=model_name,
            dataset_version_id=dataset_version_id,
            provider=provider,
            hyperparameters=hyperparameters,
            admin_user_id=admin_user_id,
        )

        hparams = hyperparameters or {}

        if provider == "gpu":
            await self._execute_gpu(job.id, model_name, dataset_version_id, hparams, admin_user_id)
        elif provider == "mock":
            await self._execute_mock(job.id, model_name, dataset_version_id, hparams, admin_user_id)
        elif provider == "local":
            await self.job_registry.update_job_status(
                job_id=job.id, status="failed",
                logs="Local training not configured. Use 'gpu' provider.",
                admin_user_id=admin_user_id,
            )
        else:
            await self.job_registry.update_job_status(
                job_id=job.id, status="failed",
                logs=f"Provider '{provider}' not recognised. Use 'gpu' or 'mock'.",
                admin_user_id=admin_user_id,
            )

        return job.id

    async def _execute_mock(self, job_id: uuid.UUID, model_name: str,
                            dataset_version_id: uuid.UUID, hparams: Dict[str, Any],
                            admin_user_id: Optional[uuid.UUID] = None):
        await self.job_registry.update_job_status(
            job_id=job_id, status="running",
            logs="Starting mock training execution... Setting up environments.",
            admin_user_id=admin_user_id,
        )
        output_model_id = f"{model_name}-ft-{str(job_id)[:8]}"
        raw_logs = (
            "Training finished successfully.\n"
            "Saved weights. Epoch 3/3 loss=0.045\nDone."
        )
        await self.job_registry.update_job_status(
            job_id=job_id, status="completed", logs=raw_logs,
            output_model_id=output_model_id, admin_user_id=admin_user_id,
        )
        await self.lineage_service.record_lineage(
            model_id=output_model_id, dataset_version_id=dataset_version_id,
            training_job_id=job_id, admin_user_id=admin_user_id,
        )

    async def _execute_gpu(self, job_id: uuid.UUID, model_name: str,
                           dataset_version_id: uuid.UUID, hparams: Dict[str, Any],
                           admin_user_id: Optional[uuid.UUID] = None):
        await self.job_registry.update_job_status(
            job_id=job_id, status="running",
            logs="GPU executor: provisioning environment...",
            admin_user_id=admin_user_id,
        )

        output_dir = tempfile.mkdtemp(prefix=f"ft-{str(job_id)[:8]}-")
        dataset_path = None
        if self.settings.mlops_dataset_storage_path:
            dataset_path = str(
                Path(self.settings.mlops_dataset_storage_path) / str(dataset_version_id) / "data.jsonl"
            )

        params = {
            "base_model": model_name,
            "output_dir": output_dir,
            "dataset_path": dataset_path,
            "learning_rate": hparams.get("learning_rate", "2e-4"),
            "num_epochs": str(hparams.get("num_epochs", 3)),
            "batch_size": str(hparams.get("batch_size", 4)),
            "max_length": str(hparams.get("max_length", 512)),
            "lora_r": str(hparams.get("lora_r", 8)),
            "lora_alpha": str(hparams.get("lora_alpha", 16)),
            "lora_dropout": str(hparams.get("lora_dropout", 0.1)),
        }

        script = GPU_TRAINING_SCRIPT
        params_json = json.dumps(params)

        async def _run():
            try:
                proc = await asyncio.create_subprocess_exec(
                    sys.executable, "-c", script, params_json,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    env={**os.environ, "TOKENIZERS_PARALLELISM": "false"},
                )
                all_logs = ""
                while True:
                    line = await proc.stdout.readline()
                    if not line:
                        break
                    decoded = line.decode("utf-8", errors="replace")
                    all_logs += decoded
                    if len(all_logs) % 4096 < len(decoded):
                        await self.job_registry.update_job_status(
                            job_id=job_id, status="running",
                            logs=all_logs[-16000:], admin_user_id=admin_user_id,
                        )
                await proc.wait()
                if proc.returncode == 0:
                    output_model_id = f"{model_name}-ft-{str(job_id)[:8]}"
                    await self.job_registry.update_job_status(
                        job_id=job_id, status="completed", logs=all_logs,
                        output_model_id=output_model_id, admin_user_id=admin_user_id,
                    )
                    await self.lineage_service.record_lineage(
                        model_id=output_model_id, dataset_version_id=dataset_version_id,
                        training_job_id=job_id, admin_user_id=admin_user_id,
                    )
                else:
                    await self.job_registry.update_job_status(
                        job_id=job_id, status="failed", logs=all_logs,
                        admin_user_id=admin_user_id,
                    )
            except Exception as e:
                await self.job_registry.update_job_status(
                    job_id=job_id, status="failed",
                    logs=f"GPU executor error: {e}", admin_user_id=admin_user_id,
                )

        asyncio.create_task(_run())
