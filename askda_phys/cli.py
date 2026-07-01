"""Command-line entry point.

    python -m askda_phys.cli build-web        # construct + save the initial web
    python -m askda_phys.cli rank             # list ranked unused seed nodes
    python -m askda_phys.cli run [--seed ID]  # run one discovery pass
    python -m askda_phys.cli run --mock       # run offline with the mock model
"""
from __future__ import annotations

import argparse

from . import models
from .config import WEB_PATH
from .knowledge import KnowledgeWeb, build_initial_web, rank_seeds
from .knowledge.ranking import best_seed
from .orchestration import discover


def _load_web() -> KnowledgeWeb:
    if WEB_PATH.exists():
        return KnowledgeWeb.load(WEB_PATH)
    raise SystemExit(f"No web at {WEB_PATH}. Run `build-web` first.")


def cmd_build_web(args) -> None:
    web = build_initial_web()
    web.save(WEB_PATH)
    print(f"Built web with {len(web)} nodes -> {WEB_PATH}")


def cmd_rank(args) -> None:
    web = _load_web()
    ranked = rank_seeds(web)
    if not ranked:
        print("No rankable seed nodes (need MEME+PHILOSOPHY nodes reachable to "
              "an APPLICATION node). Run the memeticist pass first.")
        return
    for s in ranked[: args.top]:
        print(f"{s.score:+.3f}  {s.node}  "
              f"(->{s.nearest_application} d={s.distance} c={s.nearest_centrality:.3f})")


def cmd_run(args) -> None:
    if args.mock:
        models.use_mock()
    web = _load_web()
    seed = args.seed or best_seed(web)
    if seed is None:
        raise SystemExit("No seed available; provide --seed or run memeticist + rank.")
    print(f"Seed: {seed}")
    res = discover(web, seed)
    web.save(WEB_PATH)
    print(f"strength={res.strength}  novelty={res.novelty}  "
          f"credibility={res.credibility}  app={res.application_node}")


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="askda_phys")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("build-web").set_defaults(func=cmd_build_web)

    pr = sub.add_parser("rank")
    pr.add_argument("--top", type=int, default=10)
    pr.set_defaults(func=cmd_rank)

    rn = sub.add_parser("run")
    rn.add_argument("--seed", default=None)
    rn.add_argument("--mock", action="store_true", help="use offline mock model")
    rn.set_defaults(func=cmd_run)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
