"""Command-line entry point.

    python -m askda_phys.cli build-web        # construct + save the initial web
    python -m askda_phys.cli label-web        # run the memeticist pass over the web
    python -m askda_phys.cli rank             # list ranked unused seed nodes
    python -m askda_phys.cli run [--seed ID]  # run one discovery pass
    python -m askda_phys.cli run --mock       # run offline with the mock model

Every subcommand accepts --quiet (verbosity=0, suppresses output) and --debug
(verbosity=2, extra per-step detail); the default is verbosity=1.
"""
from __future__ import annotations

import argparse

from . import models
from .config import WEB_PATH
from .knowledge import KnowledgeWeb, build_initial_web, rank_seeds, trawl_web
from .knowledge.ranking import best_seed
from .orchestration import discover


def _verbosity(args) -> int:
    if args.quiet:
        return 0
    if args.debug:
        return 2
    return 1


def _common_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    group = common.add_mutually_exclusive_group()
    group.add_argument("--quiet", action="store_true",
                       help="suppress non-essential output")
    group.add_argument("--debug", action="store_true",
                       help="verbose per-step output")
    return common


def _load_web() -> KnowledgeWeb:
    if WEB_PATH.exists():
        return KnowledgeWeb.load(WEB_PATH)
    raise SystemExit(f"No web at {WEB_PATH}. Run `build-web` first.")


def cmd_build_web(args) -> None:
    verbosity = _verbosity(args)
    web = build_initial_web(verbosity=verbosity)
    web.save(WEB_PATH)
    if verbosity >= 1:
        print(f"Built web with {len(web)} nodes -> {WEB_PATH}")


def cmd_label_web(args) -> None:
    verbosity = _verbosity(args)
    web = _load_web()
    n = trawl_web(web, verbosity=verbosity, checkpoint=lambda: web.save(WEB_PATH))
    if verbosity >= 1:
        print(f"memeticist visited {n} node(s) -> {WEB_PATH}")


def cmd_rank(args) -> None:
    verbosity = _verbosity(args)
    web = _load_web()
    ranked = rank_seeds(web)
    if not ranked:
        if verbosity >= 1:
            print("No rankable seed nodes (need MEME+PHILOSOPHY_CONCEPT nodes "
                  "reachable to a PHENOMENON node). Run the memeticist pass first.")
        return
    if verbosity >= 1:
        for s in ranked[: args.top]:
            print(f"{s.score:+.3f}  {s.node}  "
                  f"(->{s.nearest_application} d={s.distance} c={s.nearest_centrality:.3f})")


def cmd_run(args) -> None:
    verbosity = _verbosity(args)
    if args.mock:
        models.use_mock()
    web = _load_web()
    seed = args.seed or best_seed(web)
    if seed is None:
        raise SystemExit("No seed available; provide --seed or run memeticist + rank.")
    if verbosity >= 1:
        print(f"Seed: {seed}")
    res = discover(web, seed, verbosity=verbosity)
    web.save(WEB_PATH)
    if verbosity >= 1:
        print(f"strength={res.strength}  novelty={res.novelty}  "
              f"credibility={res.credibility}  app={res.application_node}")


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="askda_phys")
    sub = p.add_subparsers(dest="cmd", required=True)
    common = _common_parser()

    sub.add_parser("build-web", parents=[common]).set_defaults(func=cmd_build_web)

    sub.add_parser("label-web", parents=[common]).set_defaults(func=cmd_label_web)

    pr = sub.add_parser("rank", parents=[common])
    pr.add_argument("--top", type=int, default=10)
    pr.set_defaults(func=cmd_rank)

    rn = sub.add_parser("run", parents=[common])
    rn.add_argument("--seed", default=None)
    rn.add_argument("--mock", action="store_true", help="use offline mock model")
    rn.set_defaults(func=cmd_run)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
