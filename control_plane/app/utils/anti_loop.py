import re


def detect_repetition(
    text: str,
    max_repeats: int = 2,
    *,
    prompt_template: str | None = None,
) -> bool:
    if _detect_block_repetition(text, max_repeats):
        return True
    if _detect_long_line_repetition(text, max_repeats):
        return True
    ngram_threshold = 3 if prompt_template == "gemma" else 4
    if _detect_ngram_repetition(text, threshold=ngram_threshold):
        return True
    if _detect_short_phrase_repetition(text, max_repeats):
        return True
    return False


def _detect_block_repetition(text: str, max_repeats: int) -> bool:
    blocks = [
        "Goal:",
        "Progress:",
        "Done:",
        "In Progress:",
        "Next Steps:",
        "Relevant Files:",
    ]
    for block in blocks:
        if text.count(block) > max_repeats:
            return True
    return False


def _detect_long_line_repetition(text: str, max_repeats: int) -> bool:
    lines = [line.strip() for line in text.splitlines() if len(line.strip()) > 40]
    line_counts: dict[str, int] = {}
    for line in lines:
        line_counts[line] = line_counts.get(line, 0) + 1
        if line_counts[line] > max_repeats:
            return True
    return False


def _detect_ngram_repetition(
    text: str,
    *,
    window_sizes: tuple[int, ...] = (5, 8, 12, 20),
    threshold: int = 4,
    single_word_threshold: int = 8,
) -> bool:
    stripped = text.strip()
    if len(stripped) < 40:
        return False
    words = stripped.split()
    if len(words) >= single_word_threshold:
        word_counts: dict[str, int] = {}
        for w in words:
            word_counts[w.lower()] = word_counts.get(w.lower(), 0) + 1
            if word_counts[w.lower()] >= single_word_threshold:
                ratio = word_counts[w.lower()] / len(words)
                if ratio >= 0.5:
                    return True
    for ws in window_sizes:
        if len(words) < ws * threshold:
            continue
        seen: dict[str, int] = {}
        for i in range(len(words) - ws + 1):
            ngram = " ".join(words[i : i + ws])
            seen[ngram] = seen.get(ngram, 0) + 1
            if seen[ngram] >= threshold:
                return True
    return False


def _detect_short_phrase_repetition(text: str, max_repeats: int) -> bool:
    lines = [
        line.strip()
        for line in text.splitlines()
        if 10 <= len(line.strip()) <= 40
    ]
    line_counts: dict[str, int] = {}
    for line in lines:
        line_counts[line] = line_counts.get(line, 0) + 1
        if line_counts[line] > max_repeats:
            return True

    sentences = re.split(r"[.!?]\s*", text)
    phrases = [s.strip() for s in sentences if 10 <= len(s.strip()) <= 60]
    phrase_counts: dict[str, int] = {}
    for phrase in phrases:
        phrase_counts[phrase] = phrase_counts.get(phrase, 0) + 1
        if phrase_counts[phrase] > max_repeats:
            return True
    return False


def truncate_at_repetition(
    text: str,
    max_repeats: int = 2,
    *,
    prompt_template: str | None = None,
) -> str:
    blocks = [
        "Goal:",
        "Progress:",
        "Done:",
        "In Progress:",
        "Next Steps:",
        "Relevant Files:",
    ]
    for block in blocks:
        indices = [m.start() for m in re.finditer(re.escape(block), text)]
        if len(indices) > max_repeats:
            return (
                text[: indices[max_repeats]].strip()
                + "\n\n[Truncated due to repetition loop]"
            )

    ngram_threshold = 3 if prompt_template == "gemma" else 4
    if _detect_ngram_repetition(text, threshold=ngram_threshold):
        words = text.split()
        for ws in (5, 8, 12, 20):
            seen: dict[str, int] = {}
            for i in range(len(words) - ws + 1):
                ngram = " ".join(words[i : i + ws])
                seen[ngram] = seen.get(ngram, 0) + 1
                if seen[ngram] >= ngram_threshold:
                    char_pos = len(" ".join(words[:i]))
                    return (
                        text[:char_pos].strip()
                        + "\n\n[Truncated due to repetition loop]"
                    )

    if _detect_short_phrase_repetition(text, max_repeats):
        lines = text.splitlines()
        line_counts: dict[str, int] = {}
        for idx, line in enumerate(lines):
            stripped = line.strip()
            if 10 <= len(stripped) <= 40:
                line_counts[stripped] = line_counts.get(stripped, 0) + 1
                if line_counts[stripped] > max_repeats:
                    return (
                        "\n".join(lines[:idx]).strip()
                        + "\n\n[Truncated due to repetition loop]"
                    )

        sentences = re.split(r"([.!?]\s*)", text)
        reconstructed = ""
        phrase_counts: dict[str, int] = {}
        i = 0
        while i < len(sentences):
            chunk = sentences[i]
            if (
                i + 1 < len(sentences)
                and re.match(r"[.!?]\s*$", sentences[i + 1])
            ):
                phrase = (chunk + sentences[i + 1]).strip()
                phrase_counts[phrase] = phrase_counts.get(phrase, 0) + 1
                if phrase_counts[phrase] > max_repeats:
                    return (
                        reconstructed.strip()
                        + "\n\n[Truncated due to repetition loop]"
                    )
                reconstructed += chunk + sentences[i + 1]
                i += 2
            else:
                reconstructed += chunk
                i += 1

    return text
