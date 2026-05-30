# Model Lineage and Provenance

Model Lineage ensures auditability and end-to-end trace mapping from model ID back to the exact version of the training dataset.

## Lineage Model
The lineage graph connects the following elements:
* **Output Model ID**: The fine-tuned LLM identifier.
* **Dataset Version**: The dataset registry reference.
* **Training Job**: The fine-tuning job ID.
* **Experiment Run**: The logged run ID.

## Verification
Retrieve lineage information using the admin API:
`GET /admin/mlops/model-lineage/{model_id}`

This yields the complete metadata trail satisfying compliance requirements.
