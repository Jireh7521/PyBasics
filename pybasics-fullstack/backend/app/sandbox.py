"""A restricted Python executor for grading the Level 4/5 code challenges.

Unlike the old browser-only version (which had to hand-write a tiny Python-like
interpreter in JavaScript because there's no real Python in a browser), the
backend has real Python available -- so submitted code is graded by actually
running it, but only after an AST whitelist check, inside a separate process
with hard CPU-time and memory limits. No imports, no function/class
definitions, no loops, no file or network access, and only a small whitelist
of builtins and string/list/dict methods are reachable.
"""
import ast
import json
import multiprocessing as mp
import resource
import signal

TIMEOUT_SECONDS = 2
MEMORY_LIMIT_BYTES = 256 * 1024 * 1024  # 256MB

ALLOWED_BUILTINS = {
    "len": len, "str": str, "int": int, "float": float, "bool": bool,
    "round": round, "abs": abs, "min": min, "max": max, "sum": sum,
    "sorted": sorted, "list": list, "range": range,
}
ALLOWED_METHODS = {
    "upper", "lower", "strip", "title", "capitalize", "replace", "split",
    "startswith", "endswith", "count", "find", "join", "isdigit",
    "append", "pop", "index", "sort", "reverse", "insert",
    "get", "keys", "values",
}
ALLOWED_NODE_TYPES = (
    ast.Module, ast.Expr, ast.Assign, ast.AugAssign,
    ast.Name, ast.Load, ast.Store, ast.Constant,
    ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare, ast.Call,
    ast.Attribute, ast.Subscript, ast.Slice, ast.List, ast.Dict, ast.Set,
    ast.Tuple, ast.IfExp, ast.keyword, ast.comprehension, ast.ListComp,
    ast.JoinedStr, ast.FormattedValue,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow,
    ast.USub, ast.UAdd, ast.Not, ast.And, ast.Or,
    ast.Eq, ast.NotEq, ast.Lt, ast.Gt, ast.LtE, ast.GtE, ast.In, ast.NotIn,
)


class UnsafeCode(Exception):
    pass


def _validate(tree: ast.AST) -> None:
    for node in ast.walk(tree):
        if not isinstance(node, ALLOWED_NODE_TYPES):
            kind = type(node).__name__
            raise UnsafeCode(f"'{kind}' isn't allowed here \u2014 this challenge accepts simple assignment and expression lines only (no def/if/for/while/import/class).")
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Name):
                if f.id not in ALLOWED_BUILTINS:
                    raise UnsafeCode(f"'{f.id}' is not an available function here.")
            elif isinstance(f, ast.Attribute):
                if f.attr.startswith("_") or f.attr not in ALLOWED_METHODS:
                    raise UnsafeCode(f"'.{f.attr}()' is not an available method here.")
            else:
                raise UnsafeCode("That kind of call is not allowed here.")
        if isinstance(node, ast.Attribute) and node.attr.startswith("_"):
            raise UnsafeCode("Attribute names starting with '_' are not allowed.")
        if isinstance(node, ast.Name) and node.id.startswith("__"):
            raise UnsafeCode("Names starting with '__' are not allowed.")


def _jsonable(value):
    """Reduce a Python value to something JSON can carry; anything else becomes its repr."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, set):
        return sorted(_jsonable(v) for v in value)
    return repr(value)


def _child_main(code: str, conn):
    try:
        resource.setrlimit(resource.RLIMIT_CPU, (TIMEOUT_SECONDS, TIMEOUT_SECONDS))
        try:
            resource.setrlimit(resource.RLIMIT_AS, (MEMORY_LIMIT_BYTES, MEMORY_LIMIT_BYTES))
        except (ValueError, resource.error):
            pass  # not available on every platform (e.g. macOS); CPU limit + wall clock still apply

        def _on_alarm(signum, frame):
            raise TimeoutError("Timed out")
        signal.signal(signal.SIGALRM, _on_alarm)
        signal.alarm(TIMEOUT_SECONDS)

        tree = ast.parse(code, mode="exec")
        _validate(tree)
        compiled = compile(tree, "<challenge>", "exec")
        env = {"__builtins__": ALLOWED_BUILTINS}
        exec(compiled, env)
        signal.alarm(0)

        result_vars = {k: _jsonable(v) for k, v in env.items() if k != "__builtins__"}
        conn.send({"ok": True, "vars": result_vars, "error": None})
    except UnsafeCode as e:
        conn.send({"ok": False, "vars": {}, "error": str(e)})
    except SyntaxError as e:
        conn.send({"ok": False, "vars": {}, "error": f"SyntaxError: {e.msg} (line {e.lineno})"})
    except TimeoutError:
        conn.send({"ok": False, "vars": {}, "error": "Your code took too long to run (possible infinite loop or huge computation)."})
    except MemoryError:
        conn.send({"ok": False, "vars": {}, "error": "Your code used too much memory."})
    except Exception as e:  # noqa: BLE001 - deliberately broad: any runtime error becomes feedback text
        conn.send({"ok": False, "vars": {}, "error": f"{type(e).__name__}: {e}"})
    finally:
        conn.close()


def run_user_code(code: str) -> dict:
    """Runs `code` in a locked-down subprocess and returns
    {"ok": bool, "vars": {name: value, ...}, "error": str | None}.
    Always returns (never raises) -- a crash or hang in the child becomes an error dict."""
    if len(code) > 4000:
        return {"ok": False, "vars": {}, "error": "That's a lot of code for this challenge \u2014 please keep it under 4000 characters."}

    parent_conn, child_conn = mp.Pipe()
    ctx = mp.get_context("fork") if hasattr(mp, "get_context") else mp
    proc = ctx.Process(target=_child_main, args=(code, child_conn))
    proc.start()
    child_conn.close()
    proc.join(TIMEOUT_SECONDS + 1)
    if proc.is_alive():
        proc.terminate()
        proc.join()
        return {"ok": False, "vars": {}, "error": "Your code took too long to run (possible infinite loop or huge computation)."}
    try:
        if parent_conn.poll():
            result = parent_conn.recv()
        else:
            result = {"ok": False, "vars": {}, "error": "Your code crashed the sandbox process."}
    except EOFError:
        result = {"ok": False, "vars": {}, "error": "Your code crashed the sandbox process."}
    finally:
        parent_conn.close()
    return result


def values_equal(a, b) -> bool:
    """Loose equality matching the grading semantics used throughout: numeric
    values compare by value regardless of int/float, everything else exactly."""
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) < 1e-9
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(values_equal(x, y) for x, y in zip(a, b))
    return a == b
