"""A small safe evaluator for question conditions (02 §9.1).

Supports ``and``, ``or``, ``not``, ``==``, ``in`` over earlier answers. Names
resolve to an answer's value; no attribute access, calls or arithmetic.
"""

from __future__ import annotations

import ast
from typing import Any


def evaluate(expr: str, answers: dict[str, Any]) -> bool:
    tree = ast.parse(expr, mode="eval")
    return bool(_eval(tree.body, answers))


def _eval(node: ast.AST, answers: dict[str, Any]) -> Any:
    if isinstance(node, ast.BoolOp):
        vals = [_eval(v, answers) for v in node.values]
        return all(vals) if isinstance(node.op, ast.And) else any(vals)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return not _eval(node.operand, answers)
    if isinstance(node, ast.Compare) and len(node.ops) == 1:
        left = _eval(node.left, answers)
        right = _eval(node.comparators[0], answers)
        op = node.ops[0]
        if isinstance(op, ast.Eq):
            return left == right
        if isinstance(op, ast.NotEq):
            return left != right
        if isinstance(op, ast.In):
            return left in right
        if isinstance(op, ast.NotIn):
            return left not in right
        raise ValueError("unsupported comparison")
    if isinstance(node, ast.Name):
        answer = answers.get(node.id)
        return answer.get("value") if isinstance(answer, dict) else answer
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, (ast.List, ast.Tuple)):
        return [_eval(e, answers) for e in node.elts]
    raise ValueError(f"unsupported expression node: {type(node).__name__}")
