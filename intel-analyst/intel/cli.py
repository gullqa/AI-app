import argparse
import sys

from .config import env, load_domains
from .pipeline import run_domain
from .store import Store
from . import chat


def main() -> None:
    p = argparse.ArgumentParser(prog="intel")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="采集并生成简报")
    r.add_argument("domain")
    r.add_argument("--send", action="store_true", help="同时推送到配置的渠道")
    a = sub.add_parser("ask", help="基于情报库提问")
    a.add_argument("domain")
    a.add_argument("question")
    sub.add_parser("domains")
    args = p.parse_args()

    domains = load_domains()
    store = Store(env("INTEL_DB", "data/intel.db"))
    if args.cmd == "domains":
        print("\n".join(f"{k}: {d.name}" for k, d in domains.items()))
    elif args.domain not in domains:
        sys.exit(f"unknown domain; choose from {list(domains)}")
    elif args.cmd == "run":
        print(run_domain(domains[args.domain], store, send=args.send))
    else:
        print(chat.handle(f"{args.domain} {args.question}", domains, store))


if __name__ == "__main__":
    main()
