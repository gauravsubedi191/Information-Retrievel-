import re
from typing import List

_STOP = {
    'the','is','a','an','and','or','of','to','in','for','on','with','at','by','from','as','that','this','it','be','are','was','were',
    'we','you','they','he','she','i','not','but','if','into','about','over','after','before','under','between','through',
}

def simple_porter_stem(token: str) -> str:
    for suf in ('ing','edly','ed','ly','es','s'):
        if token.endswith(suf) and len(token) > len(suf) + 2:
            return token[: -len(suf)]
    return token

def tokenize(text: str) -> List[str]:
    text = text.lower()
    # Match words made of letters or digits
    tokens = re.findall(r"[a-z0-9]+", text, flags=re.UNICODE)
    return tokens

def normalize(text: str, do_stem: bool = True) -> List[str]:
    toks = tokenize(text)
    toks = [t for t in toks if t not in _STOP and len(t) > 1]
    if do_stem:
        toks = [simple_porter_stem(t) for t in toks]
    return toks
