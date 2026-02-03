#!/usr/bin/env python3
import argparse
import csv
import os
import re
import subprocess
from datetime import datetime

# Regex for nginx "combined" access log:
# $remote_addr - $remote_user [$time_local] "$request" $status $body_bytes_sent "$http_referer" "$http_user_agent"
LOG_RE = re.compile(
    r'^(?P<remote_addr>\S+)\s+\S+\s+(?P<remote_user>\S+)\s+'
    r'\[(?P<time_local>[^\]]+)\]\s+'
    r'"(?P<request>[^"]*)"\s+'
    r'(?P<status>\d{3})\s+'
    r'(?P<body_bytes_sent>\S+)\s+'
    r'"(?P<http_referer>[^"]*)"\s+'
    r'"(?P<http_user_agent>[^"]*)"\s+'
    r'(?P<request_length>\S+)\s+'
    r'(?P<request_time>\S+)\s+'
    r'(?P<upstream_name>\[[^\]]*\])\s+'
    r'(?P<upstream_other>\[[^\]]*\])\s+'
    r'(?P<upstream_addr>\S+)\s+'
    r'(?P<upstream_response_length>\S+)\s+'
    r'(?P<upstream_response_time>\S+)\s+'
    r'(?P<upstream_status>\S+)\s+'
    r'(?P<request_id>\S+)\s*$'
)


def parse_args():
    p = argparse.ArgumentParser(description="Parse nginx access log to CSV and commit to Git.")
    p.add_argument("--log", required=True, help="Path to nginx access.log")
    p.add_argument("--out", required=True, help="Output CSV file path")
    p.add_argument("--repo", default=".", help="Path to git repo (default: current dir)")
    p.add_argument("--commit", action="store_true", help="Commit CSV to git")
    p.add_argument("--message", default="", help="Commit message (optional)")
    return p.parse_args()

def ensure_parent_dir(path: str):
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)

def git(cmd, repo):
    return subprocess.run(["git", "-C", repo] + cmd, check=True, text=True, capture_output=True)

def main():
    args = parse_args()

    if not os.path.isfile(args.log):
        raise SystemExit(f"Log file not found: {args.log}")

    ensure_parent_dir(args.out)

    rows_written = 0
    with open(args.log, "r", encoding="utf-8", errors="replace") as f_in, \
         open(args.out, "w", newline="", encoding="utf-8") as f_out:

        writer = csv.writer(f_out)
writer.writerow([
    "remote_addr",
    "remote_user",
    "time_local",
    "method",
    "path",
    "protocol",
    "status",
    "body_bytes_sent",
    "http_referer",
    "http_user_agent",
    "request_length",
    "request_time",
    "upstream_name",
    "upstream_other",
    "upstream_addr",
    "upstream_response_length",
    "upstream_response_time",
    "upstream_status",
    "request_id",
])

        for line in f_in:
            line = line.rstrip("\n")
            m = LOG_RE.match(line)
            if not m:
                # skip lines that don't match; could also log them to a file
                continue

            request = m.group("request")
            # request looks like: "GET /some/path HTTP/1.1"
            parts = request.split(" ", 2)
            method, path, protocol = (parts + ["", "", ""])[:3]

writer.writerow([
    m.group("remote_addr"),
    m.group("remote_user"),
    m.group("time_local"),
    method,
    path,
    protocol,
    m.group("status"),
    m.group("body_bytes_sent"),
    m.group("http_referer"),
    m.group("http_user_agent"),
    m.group("request_length"),
    m.group("request_time"),
    m.group("upstream_name"),
    m.group("upstream_other"),
    m.group("upstream_addr"),
    m.group("upstream_response_length"),
    m.group("upstream_response_time"),
    m.group("upstream_status"),
    m.group("request_id"),
])

            rows_written += 1

    print(f"✅ CSV saved: {args.out} (rows: {rows_written})")

    if args.commit:
        # Basic git checks
        git(["rev-parse", "--is-inside-work-tree"], args.repo)

        # Add and commit
        git(["add", os.path.relpath(args.out, start=args.repo)], args.repo)

        msg = args.message.strip()
        if not msg:
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            msg = f"Update nginx CSV export ({now})"

        # Only commit if there are changes
        diff = subprocess.run(
            ["git", "-C", args.repo, "diff", "--cached", "--quiet"]
        )
        if diff.returncode == 0:
            print("ℹ️ No changes to commit.")
        else:
            git(["commit", "-m", msg], args.repo)
            print("✅ Committed to Git.")

if __name__ == "__main__":
    main()

