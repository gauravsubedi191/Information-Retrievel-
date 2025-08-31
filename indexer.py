import argparse, json, math, hashlib
from collections import defaultdict, Counter
from typing import Dict, List
from preprocess import normalize

def doc_id(rec: dict) -> str:
    h = hashlib.sha1((rec.get('title','') + str(rec.get('year',''))).encode('utf-8')).hexdigest()
    return f"hash:{h[:16]}"

def build_index(in_jsonl: str, index_out: str, postings_out: str):
    docs = {}
    corpus_tokens = {}

    with open(in_jsonl, 'r', encoding='utf-8') as f:
        for line in f:
            rec = json.loads(line)
            did = doc_id(rec)
            if did in docs:
                continue  # dedupe
            docs[did] = rec
            # index title + abstract + authors' names
            author_names = ' '.join(a.get('name','') for a in rec.get('authors', []))
            text = f"{rec.get('title','')} {rec.get('abstract','')} {author_names}"
            tokens = normalize(text)
            corpus_tokens[did] = tokens

    df = Counter()
    for toks in corpus_tokens.values():
        df.update(set(toks))

    N = len(corpus_tokens)
    idf = {t: math.log((N + 1) / (df_t + 1)) + 1.0 for t, df_t in df.items()}

    postings = defaultdict(list)
    for did, toks in corpus_tokens.items():
        tf = Counter(toks)
        for t, c in tf.items():
            postings[t].append((did, c))

    meta = {
        'num_docs': N,
        'idf': idf,
        'docs': docs,
    }

    with open(index_out, 'w', encoding='utf-8') as f:
        json.dump(meta, f)
    with open(postings_out, 'w', encoding='utf-8') as f:
        json.dump({t: v for t, v in postings.items()}, f)

    print(f"Indexed {N} documents. Wrote {index_out} and {postings_out}")

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--in', dest='inp', required=True)
    ap.add_argument('--index', required=True)
    ap.add_argument('--postings', required=True)
    args = ap.parse_args()
    build_index(args.inp, args.index, args.postings)
