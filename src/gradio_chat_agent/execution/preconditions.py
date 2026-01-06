import ast
from typing import Any, Mapping, Sequence

from pydantic import BaseModel, Field

from ..models.state_snapshot import StateSnapshot


class PreconditionFailure(BaseModel):
    """
    Structured description of a failed precondition.
    """

    precondition_id: str = Field(
        ...,
        description="Identifier of the failed precondition.",
    )
    description: str = Field(
        ...,
        description="Human-readable explanation of the precondition.",
    )
    expr: str = Field(
        ...,
        description="Expression that was evaluated.",
    )
    detail: str = Field(
        ...,
        description="Reason the precondition failed.",
    )


class UnsafeExpressionError(ValueError):
    pass


_ALLOWED_NODES = (
    ast.Expression,
    ast.BoolOp,
    ast.UnaryOp,
    ast.BinOp,
    ast.Compare,
    ast.Name,
    ast.Load,
    ast.Constant,
    ast.And,
    ast.Or,
    ast.Not,
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.In,
    ast.NotIn,
    ast.Is,
    ast.IsNot,
    ast.Subscript,
    ast.Index,  # py<3.9
    ast.Slice,
    ast.Attribute,
    ast.List,
    ast.Tuple,
    ast.Dict,
)


def _ensure_safe(tree: ast.AST) -> None:
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise UnsafeExpressionError(
                f"Disallowed expression node: {type(node).__name__}"
            )

        # Block any function calls outright
        if isinstance(node, ast.Call):
            raise UnsafeExpressionError(
                "Function calls are not allowed in preconditions"
            )

        # Block comprehensions / lambdas implicitly by node allowlist
        # Block dunder attribute access defensively
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            raise UnsafeExpressionError(
                "Dunder attribute access is not allowed"
            )


def _root_env(snapshot: StateSnapshot) -> dict[str, Any]:
    """
    Exposes a minimal evaluation environment:

    - components: mapping of component_id -> component_state
    - get(path, default=None): helper to fetch dotted paths under components
    """

    def get(path: str, default: Any = None) -> Any:
        # path is dotted: components.<component_id>.<field>...
        parts = path.split(".")
        cur: Any = {"components": snapshot.components}
        for part in parts:
            if isinstance(cur, Mapping) and part in cur:
                cur = cur[part]
            else:
                return default
        return cur

    return {"components": snapshot.components, "get": get}


def eval_precondition_expr(expr: str, snapshot: StateSnapshot) -> bool:
    """
    Evaluate a deterministic boolean expression against the state snapshot.

    Supported:
      - boolean ops: and/or/not
      - comparisons: == != < <= > >=
      - membership: in, not in
      - constants, lists/tuples/dicts
      - attribute/subscript access on dict-like values
      - `components` root mapping
      - `get("components.<id>.<path>", default)` helper
    """
    tree = ast.parse(expr, mode="eval")
    _ensure_safe(tree)

    env = _root_env(snapshot)

    # IMPORTANT: no builtins, only env
    value = eval(
        compile(tree, "<precondition>", "eval"), {"__builtins__": {}}, env
    )
    if not isinstance(value, bool):
        raise ValueError("Precondition expression must evaluate to a boolean")
    return value


def check_preconditions(
    preconditions: Sequence[Any], snapshot: StateSnapshot
) -> list[PreconditionFailure]:
    """
    preconditions: sequence of ActionPrecondition-like objects with fields:
      - id, description, expr
    """
    failures: list[PreconditionFailure] = []
    for p in preconditions:
        try:
            ok = eval_precondition_expr(p.expr, snapshot)
            if not ok:
                failures.append(
                    PreconditionFailure(
                        precondition_id=p.id,
                        description=p.description,
                        expr=p.expr,
                        detail="Expression evaluated to false",
                    )
                )
        except Exception as e:
            failures.append(
                PreconditionFailure(
                    precondition_id=p.id,
                    description=p.description,
                    expr=p.expr,
                    detail=f"Evaluation error: {e}",
                )
            )
    return failures
