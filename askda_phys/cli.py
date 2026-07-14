"""Command-line entry point.

    python -m askda_phys.cli build-web        # construct + save the initial web
    python -m askda_phys.cli label-web        # run the memeticist pass over the web
    python -m askda_phys.cli link-semantic    # add lexical SEMANTIC edges
    python -m askda_phys.cli rank             # rank seeds, persist full checkpoint
    python -m askda_phys.cli stage1 --n 10    # cafeteam -> advisor on the next 10 seeds
    python -m askda_phys.cli stage1 --n 10 --advisor-only  # re-run advisor only, on existing ACCEPTs
    python -m askda_phys.cli run [--seed ID]  # run one discovery pass (unstaged)
    python -m askda_phys.cli run --mock       # run offline with the mock model

Every subcommand accepts --quiet (verbosity=0, suppresses output) and --debug
(verbosity=2, extra per-step detail); the default is verbosity=1.
"""
from __future__ import annotations

import argparse

from . import models
from .agents.memeticist import ALL_ROLES, EXPANDABLE_ROLES
from .config import RANKING_CHECKPOINT_PATH, STAGE1_CHECKPOINT_PATH, WEB_PATH
from .knowledge import KnowledgeWeb, add_semantic_links, build_initial_web, trawl_web
from .knowledge.ranking import best_seed
from .orchestration import discover, run_stage0_ranking, run_stage1, run_stage1_advisor_only


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


def cmd_link_semantic(args) -> None:
    verbosity = _verbosity(args)
    web = _load_web()
    removed = web.remove_edges_by_strength({"SEMANTIC"}) if args.clear else 0
    n = add_semantic_links(web, max_doc_freq=args.max_doc_freq, debug=verbosity >= 2)
    web.save(WEB_PATH)
    if verbosity >= 1:
        if args.clear:
            print(f"removed {removed} SEMANTIC edge(s)")
        print(f"added {n} SEMANTIC edge(s) -> {WEB_PATH}")


def cmd_rank(args) -> None:
    verbosity = _verbosity(args)
    web = _load_web()
    ranked = run_stage0_ranking(web)
    if not ranked:
        if verbosity >= 1:
            print("No rankable seed nodes (need MEME+PHILOSOPHY_CONCEPT nodes "
                  "reachable to a PHENOMENON node). Run the memeticist pass first.")
        return
    if verbosity >= 1:
        for row in ranked[: args.top]:
            print(f"{row['score']:+.3f}  {row['node']}  "
                  f"(->{row['nearest_phenomenon']} d={row['distance']} "
                  f"c_phen={row['phenomenon_centrality']:.3f} "
                  f"~sci={row['nearest_science']} c_sci={row['science_centrality']:.3f})")
        print(f"full ranking ({len(ranked)} seed(s)) -> {RANKING_CHECKPOINT_PATH}")


def cmd_stage1(args) -> None:
    verbosity = _verbosity(args)
    if args.mock:
        models.use_mock()

    if args.advisor_only:
        results = run_stage1_advisor_only(args.n, verbosity=verbosity)
        if verbosity >= 1:
            print(f"stage1 (advisor-only): re-ran advisor for {len(results)} "
                  f"seed(s) -> {STAGE1_CHECKPOINT_PATH}")
        return

    web = _load_web()
    results = run_stage1(web, args.n, verbosity=verbosity)
    if verbosity >= 1:
        accepted = sum(1 for e in results if e["cafeteam"]["passed"])
        print(f"stage1: processed {len(results)} seed(s), {accepted} accepted by "
              f"cafeteam -> {STAGE1_CHECKPOINT_PATH}")


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

    ls = sub.add_parser("link-semantic", parents=[common])
    ls.add_argument("--max-doc-freq", type=int, default=3,
                    help="only link on a shared word if it appears in at most "
                         "this many node ids (default: 3) - keeps generic "
                         "vocabulary from swamping the graph")
    ls.add_argument("--clear", action="store_true",
                    help="remove all existing SEMANTIC edges before adding new "
                         "ones - useful when re-running with a different "
                         "--max-doc-freq, since edges are otherwise only ever "
                         "added, never pruned")
    ls.set_defaults(func=cmd_link_semantic)

    pr = sub.add_parser("rank", parents=[common])
    pr.add_argument("--top", type=int, default=10,
                    help="how many rows to print (the full ranking is always "
                         "persisted, regardless of this)")
    pr.set_defaults(func=cmd_rank)

    s1 = sub.add_parser("stage1", parents=[common])
    s1.add_argument("--n", type=int, default=10,
                    help="number of seeds to process this call - fresh "
                         "not-yet-processed seeds normally, or (with "
                         "--advisor-only) existing cafeteam.passed=true "
                         "entries to re-run advisor for")
    s1.add_argument("--advisor-only", action="store_true",
                    help="don't pull new seeds or re-run cafeteam; re-run "
                         "just advisor for up to --n existing checkpoint "
                         "entries with cafeteam.passed=true, using their "
                         "already-stored cafeteam output")
    s1.set_defaults(func=cmd_stage1)

    rn = sub.add_parser("run", parents=[common])
    rn.add_argument("--seed", default=None)
    rn.set_defaults(func=cmd_run)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
