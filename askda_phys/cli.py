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
from .agents.memeticist import ALL_ROLES, EXPANDABLE_ROLES
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


def _role_set(value: str) -> frozenset[str]:
    """argparse type for --expandable: a comma-separated list of role names."""
    roles = frozenset(r.strip().upper() for r in value.split(",") if r.strip())
    invalid = roles - ALL_ROLES
    if invalid:
        raise argparse.ArgumentTypeError(
            f"unknown role(s): {', '.join(sorted(invalid))}; valid roles: "
            f"{', '.join(sorted(ALL_ROLES))}")
    return roles


def _common_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    group = common.add_mutually_exclusive_group()
    group.add_argument("--quiet", action="store_true",
                       help="suppress non-essential output")
    group.add_argument("--debug", action="store_true",
                       help="verbose per-step output")
    common.add_argument("--mock", action="store_true",
                        help="use the offline mock model instead of a real backend")
    return common


def _load_web() -> KnowledgeWeb:
    if WEB_PATH.exists():
        return KnowledgeWeb.load(WEB_PATH)
    raise SystemExit(f"No web at {WEB_PATH}. Run `build-web` first.")


def cmd_build_web(args) -> None:
    verbosity = _verbosity(args)
    if args.mock:
        models.use_mock()
    web = build_initial_web(verbosity=verbosity)
    web.save(WEB_PATH)
    if verbosity >= 1:
        print(f"Built web with {len(web)} nodes -> {WEB_PATH}")


def cmd_label_web(args) -> None:
    verbosity = _verbosity(args)
    if args.mock:
        models.use_mock()
    web = _load_web()
    n = trawl_web(web, verbosity=verbosity, checkpoint=lambda: web.save(WEB_PATH),
                 expandable_roles=args.expandable)
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

    lw = sub.add_parser("label-web", parents=[common])
    lw.add_argument(
        "--expandable", type=_role_set, default=None, metavar="ROLE[,ROLE...]",
        help="comma-separated roles eligible for the expand pass "
             f"(default: {','.join(sorted(EXPANDABLE_ROLES))}); pass an empty "
             "string to classify only")
    lw.set_defaults(func=cmd_label_web)

    pr = sub.add_parser("rank", parents=[common])
    pr.add_argument("--top", type=int, default=10)
    pr.set_defaults(func=cmd_rank)

    rn = sub.add_parser("run", parents=[common])
    rn.add_argument("--seed", default=None)
    rn.set_defaults(func=cmd_run)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
