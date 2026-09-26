def stable_batches(graph, targets=None):
    deps={}
    for node, values in graph.items():
        if not isinstance(node,str) or not node: raise ValueError('invalid node')
        try: values=list(values)
        except TypeError: raise ValueError('invalid dependencies')
        if any(not isinstance(v,str) or not v for v in values): raise ValueError('invalid dependency')
        deps[node]=set(values)
    for values in list(deps.values()):
        for value in values: deps.setdefault(value,set())
    if targets is None:
        selected=set(deps)
    else:
        try: pending=list(targets)
        except TypeError: raise ValueError('invalid targets')
        if any(t not in deps for t in pending): raise ValueError('unknown target')
        selected=set()
        while pending:
            node=pending.pop()
            if node not in selected: selected.add(node); pending.extend(deps[node])
    remaining={n:deps[n]&selected for n in selected}; batches=[]
    while remaining:
        ready=sorted(n for n,d in remaining.items() if not d)
        if not ready: raise ValueError('cycle')
        batches.append(ready); done=set(ready)
        remaining={n:(d-done) for n,d in remaining.items() if n not in done}
    return batches
