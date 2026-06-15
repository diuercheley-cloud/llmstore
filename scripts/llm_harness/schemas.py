from typing import Literal, Union

from pydantic import BaseModel, Field, RootModel


class BaseAction(BaseModel):
    reason: str | None = Field(None, description="Short explanation of the action")


class PlanPayload(BaseModel):
    message: str | None = None
    reason: str | None = None


class ReadFilePayload(BaseModel):
    path: str


class ListFilesPayload(BaseModel):
    path: str = "."


class ReplaceContentPayload(BaseModel):
    path: str
    old_content: str
    new_content: str


class WriteFilePayload(BaseModel):
    path: str
    content: str


class ApplyPatchPayload(BaseModel):
    diff: str
    dry_run: bool = False


class RunShellPayload(BaseModel):
    command: str
    timeout: int = 30


class RunTestsPayload(BaseModel):
    test_path: str = "tests/"
    command: str | None = None


class GrepPayload(BaseModel):
    pattern: str
    path: str = "."
    regex: bool = False
    recursive: bool = True


class AstSearchPayload(BaseModel):
    symbol_name: str
    path: str = "."


class FinalPayload(BaseModel):
    message: str | None = None
    summary: str | None = None
    status: str | None = "completed"


class ParallelAction(BaseModel):
    type: Literal["read_file", "plan", "run_shell", "run_tests", "grep", "ast_search", "list_files"]
    reason: str | None = None
    payload: dict


class ParallelPayload(BaseModel):
    actions: list[ParallelAction]


# Specific action models for easier validation
class PlanAction(BaseAction):
    type: Literal["plan"]
    payload: PlanPayload = Field(default_factory=PlanPayload)


class ReadFileAction(BaseAction):
    type: Literal["read_file"]
    payload: ReadFilePayload


class ListFilesAction(BaseAction):
    type: Literal["list_files"]
    payload: ListFilesPayload = Field(default_factory=ListFilesPayload)


class ReplaceContentAction(BaseAction):
    type: Literal["replace_content"]
    payload: ReplaceContentPayload


class WriteFileAction(BaseAction):
    type: Literal["write_file"]
    payload: WriteFilePayload


class ApplyPatchAction(BaseAction):
    type: Literal["apply_patch"]
    payload: ApplyPatchPayload


class RunShellAction(BaseAction):
    type: Literal["run_shell"]
    payload: RunShellPayload


class RunTestsAction(BaseAction):
    type: Literal["run_tests"]
    payload: RunTestsPayload = Field(default_factory=RunTestsPayload)


class GrepAction(BaseAction):
    type: Literal["grep"]
    payload: GrepPayload


class AstSearchAction(BaseAction):
    type: Literal["ast_search"]
    payload: AstSearchPayload


class FinalAction(BaseAction):
    type: Literal["final"]
    payload: FinalPayload = Field(default_factory=FinalPayload)


class ParallelActionTyped(BaseAction):
    type: Literal["parallel"]
    payload: ParallelPayload


AgentAction = Union[
    PlanAction,
    ReadFileAction,
    ListFilesAction,
    ReplaceContentAction,
    WriteFileAction,
    ApplyPatchAction,
    RunShellAction,
    RunTestsAction,
    GrepAction,
    AstSearchAction,
    ParallelActionTyped,
    FinalAction,
]


class AgentActionResponse(RootModel):
    root: AgentAction
