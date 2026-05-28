from enum import Enum


class StepClass(str, Enum):
    CLASSIFICATION = "classification"
    EXTRACTION = "extraction"
    SUMMARIZATION = "summarization"
    FORMATTING = "formatting"
    TOOL_SELECTION = "tool_selection"
    SIMPLE_REASONING = "simple_reasoning"
    COMPLEX_REASONING = "complex_reasoning"
    CODE_GENERATION = "code_generation"
    CRITIQUE = "critique"
    FINAL_SYNTHESIS = "final_synthesis"


class StepClassifier:
    """
    Classifies the current agent step into a specific category to inform routing decisions.
    """

    @staticmethod
    def classify(step_type: str, input_text: str | None = None, metadata: dict | None = None) -> StepClass:
        # Default heuristic classification
        if step_type == "tool_call":
            return StepClass.TOOL_SELECTION
        
        if step_type == "final":
            return StepClass.FINAL_SYNTHESIS

        if metadata and "step_class" in metadata:
            return StepClass(metadata["step_class"])

        # Simple heuristics based on input_text if available
        if input_text:
            text_lower = input_text.lower()
            if any(kw in text_lower for kw in ["summarize", "summary", "tl;dr"]):
                return StepClass.SUMMARIZATION
            if any(kw in text_lower for kw in ["extract", "entities", "json structure"]):
                return StepClass.EXTRACTION
            if any(kw in text_lower for kw in ["code", "python", "javascript", "function"]):
                return StepClass.CODE_GENERATION
            if any(kw in text_lower for kw in ["think", "reason", "analyze", "why"]):
                return StepClass.COMPLEX_REASONING
            if any(kw in text_lower for kw in ["format", "pretty", "style"]):
                return StepClass.FORMATTING

        return StepClass.SIMPLE_REASONING
