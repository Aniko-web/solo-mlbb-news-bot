import re
from typing import List


def safe_trim_html(text: str, max_len: int = 1020) -> str:
    """
    Safely trims an HTML string to max_len without leaving unclosed tags
    like <i>, <b>, <code>, <a>, <u>, <s> or broken entities.
    Prevents Telegram's:
    'Bad Request: can't parse entities: Can't find end tag corresponding to start tag...'
    """
    if not text or len(text) <= max_len:
        return text or ""

    # Attempt to cut at a paragraph, newline, sentence, or word boundary
    cut_idx = max_len - 15
    for sep in ["\n\n", "\n", ". ", " "]:
        idx = text.rfind(sep, 0, max_len - 10)
        if idx > max_len // 2:
            cut_idx = idx
            break

    chunk = text[:cut_idx].rstrip()

    # Remove broken tag at the very end e.g. '<i' or '<a href='
    chunk = re.sub(r"<[^>]*$", "", chunk)

    # Track open tags in the chunk
    tag_regex = re.compile(r"<\s*(/)?\s*([a-zA-Z0-9]+)(?:\s+[^>]*)?>")
    open_stack: List[str] = []

    for match in tag_regex.finditer(chunk):
        is_closing = bool(match.group(1))
        tag_name = match.group(2).lower()
        if tag_name in ["b", "i", "code", "pre", "a", "u", "s"]:
            if not is_closing:
                open_stack.append(tag_name)
            else:
                if open_stack and open_stack[-1] == tag_name:
                    open_stack.pop()
                elif tag_name in open_stack:
                    for i in range(len(open_stack) - 1, -1, -1):
                        if open_stack[i] == tag_name:
                            open_stack.pop(i)
                            break

    # Add ellipsis
    chunk += "..."

    # Close any remaining unclosed tags in reverse order
    for tag in reversed(open_stack):
        chunk += f"</{tag}>"

    return chunk
