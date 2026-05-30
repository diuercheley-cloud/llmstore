# LLM-as-a-Judge

LLM-as-a-judge provides a scalable way to evaluate agent outputs that are too complex for traditional string matching or regex assertions.

## How it Works

The system uses a high-capability model (e.g., GPT-4o) as a "judge" to review agent responses. The judge is provided with:
1. The original user input.
2. The agent's response.
3. The expected behavior or golden reference.
4. A versioned evaluation rubric.

## Rubrics

Rubrics define the criteria for scoring. A typical rubric includes:
- **Alignment**: Does the response answer the user's question?
- **Tone**: Is the persona consistent and professional?
- **Accuracy**: Are facts presented correctly?
- **Safety**: Is the response free of harmful content?

## Scores and Rationale

The judge produces:
- **Score (1-10)**: A numerical representation of quality.
- **Rationale**: A detailed explanation of why the score was given, highlighting specific strengths or weaknesses.

## Sanitization

Rationale text is sanitized to remove any sensitive information or potential prompt leakage from the judging process.
