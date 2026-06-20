"""Run a discovery interview from the terminal.

Offline (default): a deterministic mock brain replays the module's demo so you
can watch the graph fill and the deliverables generate with no model or network.
    python -m agentic_discovery --module process

Live: a real Claude interviewer asks adaptive questions; you answer by typing.
    python -m agentic_discovery --module process --claude
"""

from __future__ import annotations

import argparse
import os

from .brain import ClaudeBrain, MockBrain
from .channels import ScriptedChannel, TextChannel
from .engine import DiscoveryEngine
from .modules import REGISTRY, get


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="agentic-discovery")
    p.add_argument("--module", default="process",
                   help=f"discovery module: {', '.join(REGISTRY)}")
    p.add_argument("--claude", action="store_true",
                   help="live interview with Claude (needs anthropic SDK + auth)")
    p.add_argument("--interviewee", default="demo-user")
    p.add_argument("--out", default=None, help="directory to write artifacts")
    p.add_argument("--list", action="store_true", help="list modules and exit")
    args = p.parse_args(argv)

    if args.list:
        for name, m in REGISTRY.items():
            print(f"  {name:14} {m.title}")
        return 0

    module = get(args.module)
    print(f"\n=== {module.title} ===")
    print(f"goal: {module.ontology.description}\n")

    if args.claude:
        brain, channel = ClaudeBrain(), TextChannel()
    elif module.demo is not None:
        brain = MockBrain(scripted=module.demo.deltas)
        channel = ScriptedChannel(answers=module.demo.answers)
        print("(offline demo — deterministic mock brain replaying a canned interview)\n")
    else:
        p.error(f"module '{args.module}' has no offline demo yet — run with --claude")

    engine = DiscoveryEngine(
        ontology=module.ontology, brain=brain, channel=channel,
        interviewee=args.interviewee)
    result = engine.run()

    print("\n" + "─" * 60)
    print(f"stopped: {result.stop_reason}")
    print(f"coverage: {' → '.join(f'{c:.0%}' for c in result.coverage_trace)}")
    print(f"graph: {len(result.graph.nodes)} nodes, {len(result.graph.edges)} edges")
    if result.contradictions:
        print(f"⚠ {len(result.contradictions)} contradiction(s) flagged for follow-up")

    artifacts = module.synthesize(result.graph)
    if args.out:
        os.makedirs(args.out, exist_ok=True)
        result.graph.save(os.path.join(args.out, "graph.json"))
        for name, content in artifacts.items():
            with open(os.path.join(args.out, name), "w") as f:
                f.write(content)
        print(f"\nwrote graph.json + {len(artifacts)} artifact(s) to {args.out}/")
    else:
        for name, content in artifacts.items():
            print(f"\n┌─ {name} " + "─" * (54 - len(name)))
            print(content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
