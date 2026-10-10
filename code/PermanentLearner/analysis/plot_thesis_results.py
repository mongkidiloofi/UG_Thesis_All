from pathlib import Path
import json
import statistics

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "analysis" / "figures"
OUT.mkdir(parents=True, exist_ok=True)


def load_runs(pattern):
    return [json.loads(path.read_text()) for path in sorted(ROOT.glob(pattern))]


def mean_sd(values):
    values = [float(value) for value in values]
    return statistics.mean(values), statistics.pstdev(values)


def curve(runs, key):
    length = max(len(run[key]) for run in runs)
    values = []
    for index in range(length):
        values.append([float(run[key][index]["reward"]) for run in runs if index < len(run[key])])
    means = [statistics.mean(row) for row in values]
    sds = [statistics.pstdev(row) for row in values]
    return range(1, length + 1), means, sds


q_runs = load_runs("phase3_results/baseline/q_learning/seed_*/result.json")
p_runs = load_runs("phase3_results/baseline/popper/seed_*/result.json")

fig, ax = plt.subplots(figsize=(8, 4.5))
for runs, label, color in ((q_runs, "Q-learning", "tab:blue"), (p_runs, "PermanentLearner", "tab:orange")):
    x, y, sd = curve(runs, "training_by_episode")
    ax.plot(x, y, label=label, color=color)
    ax.fill_between(x, [a - b for a, b in zip(y, sd)], [a + b for a, b in zip(y, sd)], color=color, alpha=0.18)
ax.set_xlabel("Training episode")
ax.set_ylabel("Episode reward")
ax.set_title("Maze training reward across 30 seeds")
ax.legend()
fig.tight_layout()
fig.savefig(OUT / "maze_training_reward.png", dpi=300)
plt.close(fig)


p_conv = mean_sd([run["episodes_to_convergence"] for run in p_runs])
q_conv = mean_sd([run["episodes_to_optimal_policy"] for run in q_runs])
fig, ax = plt.subplots(figsize=(6, 4.5))
ax.bar(["PermanentLearner\nconvergence", "Q-learning\nfinal-policy match"], [p_conv[0], q_conv[0]], yerr=[p_conv[1], q_conv[1]], capsize=5, color=["tab:orange", "tab:blue"])
ax.set_ylabel("Episodes")
ax.set_title("Convergence indicators; definitions differ")
fig.tight_layout()
fig.savefig(OUT / "maze_convergence_indicators.png", dpi=300)
plt.close(fig)


games = ["unary", "relational", "compositional"]
goal_runs = {
    game: load_runs(f"results/hidden_goal/{game}/seed_*.json")
    for game in games
}

metrics = ["held_out_agreement", "held_out_precision", "held_out_recall", "planning_success"]
fig, ax = plt.subplots(figsize=(8, 4.5))
width = 0.18
positions = list(range(len(games)))
for offset, metric in enumerate(metrics):
    values = [statistics.mean(float(run[metric]) for run in goal_runs[game]) for game in games]
    ax.bar([pos + (offset - 1.5) * width for pos in positions], values, width=width, label=metric.replace("_", " "))
ax.set_xticks(positions)
ax.set_xticklabels([game.title() for game in games])
ax.set_ylim(0, 1.08)
ax.set_ylabel("Mean score")
ax.set_title("Hidden-goal held-out and planning performance")
ax.legend()
fig.tight_layout()
fig.savefig(OUT / "hidden_goal_performance.png", dpi=300)
plt.close(fig)


means = [mean_sd([run["examples_to_convergence"] for run in goal_runs[game]]) for game in games]
fig, ax = plt.subplots(figsize=(6, 4.5))
ax.bar([game.title() for game in games], [item[0] for item in means], yerr=[item[1] for item in means], capsize=5, color="tab:green")
ax.set_ylabel("Examples")
ax.set_title("Hidden-goal examples to convergence")
fig.tight_layout()
fig.savefig(OUT / "hidden_goal_convergence.png", dpi=300)
plt.close(fig)

print(f"Wrote figures to {OUT}")
