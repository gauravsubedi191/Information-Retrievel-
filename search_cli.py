import argparse, webbrowser
from search_core import load_index, rank

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('query')
    ap.add_argument('--index', default='data/index.json')
    ap.add_argument('--postings', default='data/postings.json')
    ap.add_argument('--topk', type=int, default=20)
    ap.add_argument('--from-year', type=int)
    ap.add_argument('--to-year', type=int)
    ap.add_argument('--open', action='store_true', help='Open top result in browser')
    args = ap.parse_args()

    meta, postings = load_index(args.index, args.postings)
    results = rank(meta, postings, args.query, topk=args.topk, year_from=args.from_year, year_to=args.to_year)

    if not results:
        print('No results.')
        return

    for i, r in enumerate(results, 1):
        authors = ', '.join(a['name'] for a in r['authors'])
        year = r['year'] if r['year'] is not None else 'n.d.'
        print(f"[{i}] {r['title']} ({year})  score={r['score']}")
        if authors:
            print(f"    Authors: {authors}")
        if r.get('abstract'):
            print(f"    Abstract: {r['abstract'][:220]}{'…' if len(r['abstract'])>220 else ''}")
        print(r['pub_url'])
        print()

    if args.open:
        webbrowser.open(results[0]['pub_url'])

if __name__ == '__main__':
    main()
