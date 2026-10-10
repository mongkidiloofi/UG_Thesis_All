"""Small Datalog interpreter and domain-independent Popper fact builders."""

import clingo


def infer(program, predicate, arity=2):
    ctl = clingo.Control(["--warn=none"])
    ctl.add("base", [], program + f"\n#show {predicate}/{arity}.")
    ctl.ground([("base", [])])
    with ctl.solve(yield_=True) as handle:
        for m in handle:
            return [tuple(str(a) for a in s.arguments) for s in m.symbols(shown=True)]
    return []


def bias(head, types, bodies, variables=4, body=3):
    lines = [
        f"head_pred({head},{len(types)}).",
        f"type({head},({','.join(types)}{',' if len(types) == 1 else ''})).",
        f"max_vars({variables}).",
        f"max_body({body}).",
        ":- clause(C), #count{V : var_type(C,V,example)} != 1.",
    ]
    for name, ts in bodies.items():
        lines += [
            f"body_pred({name},{len(ts)}).",
            f"type({name},({','.join(ts)}{',' if len(ts) == 1 else ''})).",
        ]
    return lines


def context(colors, prefix, e):
    """Positive and explicit negative color-presence facts, no color roles."""
    return [f"{prefix}{'has' if c in colors else 'lacks'}{c}({e})." for c in range(16)]


def pixel_facts(symbol, e):
    n = int(len(symbol) ** 0.5)
    assert n * n == len(symbol)
    return [f"opposite({i},{n - 1 - i})." for i in range(n)] + [
        f"current({e},{i // n},{i % n})." for i, v in enumerate(symbol) if v
    ]
