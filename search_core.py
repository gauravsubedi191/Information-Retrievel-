import json, math
from typing import List, Dict
from preprocess import normalize

def load_index(index_path: str, postings_path: str):
    with open(index_path, 'r', encoding='utf-8') as f:
        meta = json.load(f)
    with open(postings_path, 'r', encoding='utf-8') as f:
        postings = json.load(f)
    return meta, postings

def rank(meta: dict, postings: dict, query: str, topk: int = 20, year_from=None, year_to=None):
    q_toks = normalize(query)
    if not q_toks:
        return []

    scores = {}
    for qt in q_toks:
        if qt not in postings:
            continue
        idf = meta['idf'].get(qt, 0.0)
        for did, tf in postings[qt]:
            rec = meta['docs'][did]
            y = rec.get('year')
            if year_from is not None and (y is None or y < year_from):
                continue
            if year_to is not None and (y is None or y > year_to):
                continue
            scores[did] = scores.get(did, 0.0) + (1 + math.log(tf)) * idf

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:topk]
    results = []
    for did, sc in ranked:
        rec = meta['docs'][did]
        results.append({
            'score': round(sc, 4),
            'title': rec.get('title'),
            'year': rec.get('year'),
            'pub_url': rec.get('pub_url'),
            'authors': rec.get('authors', []),
            'abstract': rec.get('abstract', ''),
        })
    return results
