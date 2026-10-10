"""Command-line entry points. Only this boundary knows game identifiers."""

import argparse
import hashlib
import json
import logging
import os
import subprocess
import sys
import time
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import numpy as np

from .agent import Agent2


def positive_int(value):
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def versions():
    result = {"python": sys.version.split()[0]}
    for name in ["arc-agent2", "popper", "arc-agi", "arcengine", "numpy", "clingo", "janus_swi"]:
        try:
            result[name] = version(name)
        except PackageNotFoundError:
            result[name] = "not installed"
    return result


def theory(result):
    """Export independently queryable programs; observation facts are external."""
    programs = ["% Learned theory snapshot; provide observation facts when querying."]
    for model in result["rules"].values():
        if model["program"] is not None:
            programs.append(model["program"])
    for index, channel in enumerate(result["channels"]):
        if channel["rule"] is not None:
            programs.append(f"% Registered observed region {channel['key']}")
            programs.append(channel["rule"].replace("nextpixel(", f"nextpixel_region{index}("))
    return "\n".join(programs) + "\n"


def run(args):
    """Run once, continue through levels, and stop without automatic resets."""
    from arc_agi import Arcade, OperationMode
    from arcengine import GameAction, GameState

    os.environ.setdefault("PYTHONHASHSEED", "0")
    out = args.out
    out.mkdir(parents=True, exist_ok=False)
    package = Path(__file__).parent
    write_json(
        out / "manifest.json",
        {
            "game": args.game,
            "budget": args.budget,
            "seed": args.seed,
            "max_fits": args.max_fits,
            "fit_timeout": args.fit_timeout,
            "versions": versions(),
            "sources": {
                path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                for path in sorted(package.glob("*.py"))
            },
        },
    )
    arc = Arcade(
        operation_mode=OperationMode.OFFLINE,
        environments_dir=str(args.environments_dir),
        recordings_dir=str(out / "recordings"),
        logger=logging.getLogger("arc_agent2"),
    )
    env = arc.make(args.game, seed=args.seed, save_recording=True, include_frame_data=True)
    if env is None:
        raise ValueError(f"Game unavailable locally: {args.game}. Run 'arc-agent2 download' first.")
    frame = env.observation_space
    agent = Agent2(out / "learning", args.seed, args.fit_timeout, args.max_fits)
    frames = [np.array(frame.frame[-1])]
    start = time.monotonic()
    error = None
    actions = 0
    try:
        agent.observe(frame.frame[-1], frame.levels_completed, frame.available_actions)
        for _ in range(args.budget):
            action, data = agent.choose()
            frame = env.step(getattr(GameAction, f"ACTION{action}"), data=data)
            actions += 1
            frames.append(np.array(frame.frame[-1]))
            agent.observe(frame.frame[-1], frame.levels_completed, frame.available_actions)
            write_json(out / "trace.json", agent.trace)
            if actions % 20 == 0:
                print(f"{actions} actions, {frame.levels_completed} levels completed", flush=True)
            if frame.state in [GameState.WIN, GameState.GAME_OVER]:
                break
    except Exception as exc:
        error = repr(exc)
        raise
    finally:
        result = agent.summary()
        result.update(
            game_id=env.environment_info.game_id,
            environment_actions=actions,
            levels_completed=frame.levels_completed,
            state=str(frame.state),
            seconds=time.monotonic() - start,
            error=error,
            resets=0,
        )
        write_json(out / "result.json", result)
        write_json(out / "trace.json", agent.trace)
        (out / "knowledge.pl").write_text(theory(result))
        np.savez_compressed(out / "frames.npz", frames=np.array(frames))
        print(
            json.dumps(
                {
                    key: result[key]
                    for key in [
                        "environment_actions",
                        "levels_completed",
                        "state",
                        "seconds",
                        "error",
                    ]
                },
                indent=2,
            )
        )


def download(args):
    """Let the official toolkit obtain assets; no credentials are stored here."""
    from arc_agi import Arcade, OperationMode

    arc = Arcade(operation_mode=OperationMode.NORMAL, environments_dir=str(args.environments_dir))
    if arc.make(args.game, save_recording=False) is None:
        raise ValueError(f"Game unavailable: {args.game}")
    print(f"Ready: {args.game} in {args.environments_dir}")


def doctor(_args):
    """Check Python dependencies and the native SWI-Prolog/Janus connection."""
    print(json.dumps(versions(), indent=2), flush=True)
    code = (
        "from janus_swi import query_once; "
        "print(query_once('current_prolog_flag(version_data, swi(Major, Minor, Patch, _))'))"
    )
    subprocess.run([sys.executable, "-c", code], check=True)


def main():
    parser = argparse.ArgumentParser(description="Agent 2: online symbolic dynamics learning")
    commands = parser.add_subparsers(dest="command", required=True)
    runner = commands.add_parser("run", help="play a downloaded game locally")
    runner.add_argument("game")
    runner.add_argument("--out", type=Path, required=True)
    runner.add_argument("--environments-dir", type=Path, default=Path("environment_files"))
    runner.add_argument("--budget", type=positive_int, default=200)
    runner.add_argument("--seed", type=int, default=0)
    runner.add_argument("--max-fits", type=positive_int, default=40)
    runner.add_argument("--fit-timeout", type=positive_int, default=8)
    runner.set_defaults(function=run)
    downloader = commands.add_parser("download", help="download assets using the official toolkit")
    downloader.add_argument("game")
    downloader.add_argument("--environments-dir", type=Path, default=Path("environment_files"))
    downloader.set_defaults(function=download)
    check = commands.add_parser("doctor", help="check the runtime and Prolog bridge")
    check.set_defaults(function=doctor)
    args = parser.parse_args()
    args.function(args)
