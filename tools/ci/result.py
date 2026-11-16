#!/usr/bin/env python3
"""result.py <job> <success|failure|cancelled> [summary file] -> result JSON for a request draft."""
import json, os, sys, time
job, status = sys.argv[1], sys.argv[2]
note = ''
if len(sys.argv) > 3 and os.path.isfile(sys.argv[3]):
    note = open(sys.argv[3], encoding='utf-8', errors='replace').read()[-4000:]
print(json.dumps({'job': job, 'result': 'pass' if status == 'success' else 'fail', 'status': status,
                  'run': f"{os.environ.get('GITHUB_SERVER_URL', '')}/{os.environ.get('GITHUB_REPOSITORY', '')}/actions/runs/{os.environ.get('GITHUB_RUN_ID', '')}",
                  'finished': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'note': note}, indent=1))
