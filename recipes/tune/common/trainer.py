# Copyright (c) Fireworks AI, Inc. and affiliates.
#
# All Rights Reserved.

import os
import torch
import torch.distributed as dist
from datasets import DatasetDict
import transformers
from transformers import AutoTokenizer
from omegaconf import DictConfig
import wandb


def train(
    config: DictConfig,
    tokenizer: AutoTokenizer,
    dataset: DatasetDict,
    model: torch.nn.Module,
) -> torch.nn.Module:
    """
    Fine tunes a summarization model.

    Args:
        config: the configuration describing the training program,
        tokenizer: the tokenizer to use,
        dataset: the training dataset,
        model: the model to train.

    Returns:
        trained model.
    """
    kwargs = {"report_to": []}

    # weights and biases config
    wandb_key = config.get("wandb_key")
    if wandb_key:
        wandb.login(key=wandb_key)
        kwargs["report_to"] = "wandb"
    wandb_project = config.get("wandb_project")
    os.environ["WANDB_PROJECT"] = config.get("wandb_project")
    wandb_last_run_id = config.get("wandb_last_run_id")
    wandb_checkpoint_dir = None
    if wandb_project:
        if wandb_last_run_id is None:
            wandb.init(project=wandb_project, dir=config.working_dir)
        else:
            # resume the wandb run from the run_id
            with wandb.init(
                    project=wandb_project,
                    id=wandb_last_run_id,
                    resume="must",
                    dir=config.working_dir
            ) as run:
                # Connect an Artifact to the run
                wandb_checkpoint_name = config.get("wandb_checkpoint_name") if config.get("wandb_checkpoint_name") is not None else f"checkpoint-{wandb_last_run_id}:latest"
                my_checkpoint_artifact = run.use_artifact(wandb_checkpoint_name)

                # Download checkpoint to a folder and return the path
                wandb_checkpoint_dir = my_checkpoint_artifact.download()
                print(f"wandb_checkpoint_dir: {wandb_checkpoint_dir}")
        kwargs["report_to"] = "wandb"
        os.environ["WANDB_LOG_MODEL"] = "checkpoint"
        kwargs["save_steps"] = 1
        kwargs["save_total_limit"] = 20
    if kwargs["report_to"] != "wandb":
        # HF tries to init wandb as long as the pip package is installed
        os.environ["WANDB_DISABLED"] = "true"

    per_device_macro_batch_size = config.model.batch_size // dist.get_world_size()
    gradient_accumulation_steps = (
        per_device_macro_batch_size // config.model.micro_batch_size
    )
    print(
        f"per_device_train_batch_size: {config.model.micro_batch_size} "
        f"gradient_accumulation_steps: {gradient_accumulation_steps}"
    )
    deepspeed_config = config.model.get("deepspeed_config", None)
    if deepspeed_config:
        print(f"Deepspeed config: {deepspeed_config}")
    ddp_find_unused_parameters = (
        not config.model.gradient_checkpointing
        and not config.model.get("load_in_8bit", False)
        and not config.model.get("load_in_4bit", False)
    )
    lr_scheduler_type = config.model.get("lr_scheduler_type")
    if lr_scheduler_type:
        kwargs["lr_scheduler_type"] = lr_scheduler_type
    optim = config.model.get("optim")
    if optim:
        kwargs["optim"] = optim
    warmup_steps = config.model.get("warmup_steps", 10)
    trainer = transformers.Trainer(
        model=model,
        train_dataset=dataset,
        args=transformers.TrainingArguments(
            per_device_train_batch_size=config.model.micro_batch_size,
            gradient_accumulation_steps=gradient_accumulation_steps,
            warmup_steps=warmup_steps,
            num_train_epochs=config.model.epochs,
            learning_rate=config.model.learning_rate,
            bf16=config.model.get("bf16", False),
            logging_steps=1,
            output_dir=config.working_dir,
            # save_strategy="no",
            deepspeed=deepspeed_config,
            gradient_checkpointing=config.model.gradient_checkpointing,
            ddp_find_unused_parameters=ddp_find_unused_parameters,
            group_by_length=False,
            # max_steps=50,
            **kwargs,
        ),
        data_collator=transformers.DataCollatorForSeq2Seq(
            tokenizer, pad_to_multiple_of=8, return_tensors="pt", padding=True
        ),
    )
    model.config.use_cache = False
    trainer.train(resume_from_checkpoint=False if wandb_checkpoint_dir is None else wandb_checkpoint_dir)

    return model
