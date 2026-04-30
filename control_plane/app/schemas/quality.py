from pydantic import BaseModel, Field

class SystemPromptUpdate(BaseModel):
    system_prompt: str | None = Field(default=None, max_length=5000)

class PromptTemplateUpdate(BaseModel):
    prompt_template: str | None = Field(default=None, max_length=10000)
