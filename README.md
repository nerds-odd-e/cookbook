
# Fireworks Cookbook

Fireworks cookbook is a collection of recipes designed to assist in the development, evaluation, and deployment of Generative AI (GenAI) models.

## Motivation
Generative AI has seen unprecedented growth in recent times, spurring the creation of novel models and techniques. However, the information required to recreate these models and implement the latest modeling techniques is dispersed across various repositories, online forums, and research papers. The Fireworks Cookbook provides a set of comprehensive, ready-to-use recipes, enabling users to run and adapt them for diverse needs and applications. These recipes encompass a wide range of popular use-cases, including fine-tuning, generation, and evaluation. The cookbook is routinely updated to include recipes based on the latest advancements in the field.

## Code organization
The code in the repository is organized according to use-case, with some code serving multiple purposes. Our present emphasis is on Large Language Models (LLMs), however, we will incorporate more model classes in the future.

### Docker
To enhance user convenience, we offer a Docker container inclusive of all the necessary dependencies to run the provided recipes. The Docker configuration is found under [`recipes/docker`](https://github.com/fw-ai/cookbook/tree/main/recipes/docker/text)

### Shared libraries
The codebase shared across recipes is situated in [`recipes/common`](https://github.com/fw-ai/cookbook/tree/main/recipes/common).

### Recipes
Recipes are categorized according to their respective use-cases. Here is the list of currently supported use-cases. Please note, most of the recipes come with dedicated README files providing more in-depth information.

**Environment:**
* [Docker container for LLM development](https://github.com/fw-ai/cookbook/tree/main/recipes/docker/text).

**Tuning:**
* [LoRA instruction tuning](https://github.com/fw-ai/cookbook/tree/main/recipes/tune/instruct_lora).

**Evaluation:**
* [Ranker leveraging perplexity for scoring](https://github.com/fw-ai/cookbook/tree/main/recipes/eval/perplexity_rank).

**Generation:**
* [Inference with a LoRA adapter](https://github.com/fw-ai/cookbook/tree/main/recipes/generate/instruct_lora),
* [Constrained output generation in json format](https://github.com/fw-ai/cookbook/tree/main/recipes/generate/jsonformer).

## Example Workflow
To illustrate how to leverage the recipes for an end-to-end usecase, lets walk through the process of fine tuning a model, inspecting the results visually, and deploying the model to the Fireworks platform for inference.
The instructions assume that the source code of the cookbook was checked out under `/workspace/cookbook`.
### Build and instantiate docker container
```bash
cd /workspace/cookbook/recipes/docker/text
docker build -t fireworks_cb_text .
docker run --privileged -it --gpus all -p 8888:8888 \
  --mount type=bind,source="/workspace",target="/workspace" \
  --mount type=bind,source="$HOME/.cache/huggingface",target="/root/.cache/huggingface" \
  --mount type=bind,source="$HOME/.ssh",target="/root/.ssh" \
  --mount type=bind,source="/mnt/text",target="/mnt/text" \
  --ipc=host --net=host --cap-add  SYS_NICE \
  fireworks_cb_text /bin/bash
```
The following commands will run inside the container.
For more details, go [here](https://github.com/fw-ai/cookbook/tree/main/recipes/docker/text).
### Fine tune a model
```bash
cd /workspace/cookbook/recipes/tune/instruct_lora
export PYTHONPATH=.:/workspace/cookbook
export N_GPUS=`nvidia-smi --query-gpu=gpu_name --format=csv,noheader | wc -l`
torchx run -s local_cwd dist.ddp -j 1x${N_GPUS} --script finetune.py -- \
  --config-name=summarize
```
### Test the model locally
```bash
cd /workspace/cookbook/recipes/generate/instruct_lora
python generate.py
```
### Upload the model to Fireworks
Follow the [quick start instructions](https://fireworksai.readme.io/docs/quickstart) to set up your account with Fireworks and generate the API key.
```
firectl signin
firectl create model my-model \
  /mnt/text/model/llama2-7b/dialogsum-samsum/0.1/final
firectl deploy my-model
```
For more details, see this [guide](https://fireworksai.readme.io/docs/model-upload).
### Test the model

```bash
export API_KEY=...
export ACCOUNT_ID=...
export PROMPT="[INST] <<SYS>>\nYou are an assistant and you are tasked with writing text summaries. For each input text, provide a summary. The summary should be concise, accurate and truthful. Do not make up facts or answers.\n<</SYS>>\n\n#Person1#: Welcome to my birthday party, I am so happy you can come. #Person2#: Thanks for inviting me. Here is the gift for you. Happy birthday, Francis! Many more happy and healthy years for you! #Person1#: Thank you, shall I open it now? #Person2#: Yes, please do. #Person1#: Wow, a remote car model and my favorite brand. I really like it. That is so nice of you. #Person2#: Yeah, I was really struggling whether I should give you this nice little car. It was the last one they had and I really like it so much myself. #Person1#: Typical you, always wanting to keep the best things for yourself. The more I appreciate the gift now.[/INST]\n"
curl \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model": "accounts/${ACCOUNT_ID}/models/my-model", "prompt": "${PROMPT}"}' \
  https://api.fireworks.ai/inference/v1/completions
```
### Clean up
```bash
firectl undeploy my-model
firectl delete my-model
```