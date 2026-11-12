"""Minimal S-expression reader/writer for KiCad files.

Copied from the PDB project's prepare_libraries.py (parse/dump/child helpers). Quoted
strings are kept as a `Quoted` str subclass so they are written back with quotes.
"""
import json
import re


class Quoted(str):
    pass


def q(value):
    """Mark a value as a quoted string."""
    return Quoted(str(value))


def parse(text):
    """Turn KiCad S-expression text into nested Python lists."""
    tokens = re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+', text)
    stack, root = [], None
    for token in tokens:
        if token == "(":
            node = []
            if stack:
                stack[-1].append(node)
            else:
                root = node
            stack.append(node)
        elif token == ")":
            stack.pop()
        else:
            stack[-1].append(q(json.loads(token)) if token.startswith('"') else token)
    return root


def dump(node, level=0):
    """Write nested lists back as indented S-expression text (tabs, like KiCad)."""
    if isinstance(node, Quoted):
        return json.dumps(str(node), ensure_ascii=False)
    if not isinstance(node, list):
        return str(node)
    if not any(isinstance(item, list) for item in node):
        return "(" + " ".join(dump(item) for item in node) + ")"
    head, i = [], 0
    while i < len(node) and not isinstance(node[i], list):
        head.append(dump(node[i]))
        i += 1
    inner = "".join("\n" + "\t" * (level + 1) + dump(item, level + 1) for item in node[i:])
    return "(" + " ".join(head) + inner + "\n" + "\t" * level + ")"


def children(node, name):
    return [c for c in node if isinstance(c, list) and c and c[0] == name]


def child(node, name):
    found = children(node, name)
    return found[0] if found else None


def walk(node, name):
    if isinstance(node, list):
        if node and node[0] == name:
            yield node
        for c in node:
            yield from walk(c, name)
