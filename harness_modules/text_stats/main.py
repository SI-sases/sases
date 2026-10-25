import re
from collections import Counter

def run(params):
    text = params.get("text", "")
    if not text:
        raise ValueError("缺少 text 参数")
    words = re.findall(r'\w+', text.lower())
    lines = text.split('\n')
    return {
        "char_count": len(text),
        "word_count": len(words),
        "line_count": len(lines),
        "top_words": dict(Counter(words).most_common(10))
    }
