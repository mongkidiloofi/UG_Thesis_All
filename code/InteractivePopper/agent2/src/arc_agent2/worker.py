"""Run one bounded Popper search in an isolated Prolog process."""

import argparse
import json
from pathlib import Path


def main():
    from popper.loop import popper
    from popper.util import Settings, format_rule

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("timeout", type=float)
    args = parser.parse_args()
    path = args.directory
    settings = Settings(
        bk_file=str(path / "bk.pl"),
        ex_file=str(path / "exs.pl"),
        bias_file=str(path / "bias.pl"),
        timeout=args.timeout,
        verbosity=0,
    )
    program, score = popper(settings)
    rules = "\n".join(sorted(format_rule(rule) for rule in program)) + "\n" if program else ""
    (path / "hypothesis.pl").write_text(rules)
    (path / "score.json").write_text(json.dumps(list(score)) if score else "null")


if __name__ == "__main__":
    main()
