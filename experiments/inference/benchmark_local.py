"""Measure a local OpenAI-compatible inference engine, without saving prompt content.

This measures the engine alone, not the customer gateway, billing, or production latency.
Only loopback HTTP endpoints are accepted; use synthetic input data.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import ipaddress
import json
import math
import platform
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def endpoint(value: str) -> str:
    url = urllib.parse.urlsplit(value)
    try:
        is_loopback = url.hostname == 'localhost' or ipaddress.ip_address(url.hostname or '').is_loopback
    except ValueError:
        is_loopback = False
    if (url.scheme != 'http' or not is_loopback or url.username is not None or url.password is not None
            or url.path not in ('', '/') or url.query or url.fragment):
        raise ValueError('endpoint must be a loopback HTTP origin')
    return value.rstrip('/') + '/v1/chat/completions'


def run(base_url: str, model: str, dataset: Path, count: int, max_tokens: int, timeout: float) -> dict:
    url = endpoint(base_url)
    data = dataset.read_bytes()
    rows = list(csv.DictReader(data.decode('utf-8-sig').splitlines()))
    if not rows or any(not row.get('text') for row in rows):
        raise ValueError('dataset must have non-empty text rows')
    if count < 1 or count > len(rows) or not 1 <= max_tokens <= 1024 or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError('invalid request count, token limit or timeout')
    records = []
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    for row in rows[:count]:
        payload = json.dumps({'model': model, 'messages': [{'role': 'user', 'content': row['text']}],
                              'temperature': 0, 'max_tokens': max_tokens}).encode('utf-8')
        request = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
        start = time.perf_counter()
        try:
            with opener.open(request, timeout=timeout) as response:
                body = response.read(1_000_001)
                if len(body) > 1_000_000:
                    raise ValueError('response too large')
                result = json.loads(body)
                message = result['choices'][0]['message']['content']
                if not isinstance(message, str) or not message.strip():
                    raise ValueError('empty response')
                usage = result.get('usage', {})
                records.append({'ok': True, 'status': response.status,
                                'latency_ms': round((time.perf_counter() - start) * 1000, 3),
                                'prompt_tokens': usage.get('prompt_tokens'),
                                'completion_tokens': usage.get('completion_tokens')})
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError, IndexError, TypeError):
            records.append({'ok': False, 'latency_ms': round((time.perf_counter() - start) * 1000, 3)})
            break  # Stop promptly when the engine is unhealthy or too slow.
    successes = sorted(item['latency_ms'] for item in records if item['ok'])
    return {'kind': 'local_engine_only', 'run_at': datetime.now(timezone.utc).isoformat(),
            'model': model, 'input_sha256': hashlib.sha256(data).hexdigest(), 'requests': count,
            'max_tokens': max_tokens, 'concurrency': 1, 'platform': platform.platform(),
            'records': records, 'attempted': len(records), 'successful': len(successes),
            'p95_ms': successes[math.ceil(.95 * len(successes)) - 1] if successes else None}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', required=True)
    parser.add_argument('--model', required=True)
    parser.add_argument('--dataset', required=True, type=Path)
    parser.add_argument('--count', type=int, default=20)
    parser.add_argument('--max-tokens', type=int, default=8)
    parser.add_argument('--timeout', type=float, default=120)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    result = run(args.url, args.model, args.dataset, args.count, args.max_tokens, args.timeout)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x', encoding='utf-8', newline='\n') as handle:
        json.dump(result, handle, indent=2)
        handle.write('\n')
    print(f"{result['successful']}/{result['requests']} responses; p95={result['p95_ms']} ms")
    return 0 if result['successful'] == result['requests'] else 1


if __name__ == '__main__':
    sys.exit(main())
