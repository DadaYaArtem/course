"""Measure real HTTP /query responses; run only against a test environment."""
import argparse
import asyncio
from collections import Counter
import math
import time
import httpx


def positive(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError('must be positive')
    return number


async def run(args):
    semaphore = asyncio.Semaphore(args.concurrency)
    durations = []
    outcomes = Counter()
    async with httpx.AsyncClient(timeout=args.timeout) as client:
        async def request():
            async with semaphore:
                start = time.perf_counter()
                try:
                    response = await client.post(args.url.rstrip('/') + '/query', json={'text': args.question, 'language': args.language})
                    outcome = str(response.status_code)
                    success = response.is_success
                except httpx.RequestError as exc:
                    outcome = type(exc).__name__
                    success = False
                elapsed = time.perf_counter() - start
                outcomes[outcome] += 1
                if success:
                    durations.append(elapsed)
        start = time.perf_counter()
        await asyncio.gather(*(request() for _ in range(args.requests)))
        total = time.perf_counter() - start
    print(f'Attempts: {args.requests}; concurrency: {args.concurrency}; elapsed: {total:.3f} s')
    print(f'Outcomes: {dict(outcomes)}')
    print(f'Successful responses/s: {len(durations) / total:.3f}')
    if durations:
        durations.sort()
        percentile = lambda p: durations[math.ceil(len(durations) * p) - 1] * 1000
        print(f'Successful latency ms: mean={sum(durations)/len(durations)*1000:.1f}; p50={percentile(.5):.1f}; p95={percentile(.95):.1f}; p99={percentile(.99):.1f}')
    return 0 if len(durations) == args.requests else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://localhost:8000')
    parser.add_argument('--requests', type=positive, default=20)
    parser.add_argument('--concurrency', type=positive, default=2)
    parser.add_argument('--timeout', type=float, default=120)
    parser.add_argument('--question', default='What is BERT?')
    parser.add_argument('--language', choices=['en', 'ru'], default='en')
    raise SystemExit(asyncio.run(run(parser.parse_args())))
