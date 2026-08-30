"""CLI for the A-share Board Radar."""
import argparse
from pathlib import Path
import pandas as pd
from radar import scan


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', help='CSV containing historical daily data')
    p.add_argument('--output', default='output/top20.csv')
    p.add_argument('--min-score', type=int, default=70)
    p.add_argument('--top', type=int, default=20)
    args = p.parse_args()

    if not args.input:
        raise SystemExit('V1.1: use --input data.csv; live download will be added after environment testing.')
    df = pd.read_csv(args.input)
    result = scan(df, args.min_score).head(args.top)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False, encoding='utf-8-sig')
    print(result.to_string(index=False))
    print(f'\nSaved: {args.output}')


if __name__ == '__main__':
    main()
