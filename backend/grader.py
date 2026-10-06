"""
A restricted, sandboxed evaluator for the short Python snippets learners submit
in Level 4 and 5 code challenges.

Why not just exec()/eval() the student's code? Because that would let anyone
run arbitrary Python on the server (read files, open sockets, import os, etc).
Why not forbid code execution entirely and pattern-match the answer instead?
Because the whole point of these levels is "write real code that works" --
we want real Python semantics (real arithmetic, real string/list/dict
behaviour, real error types), just restricted to a safe subset.

Approach: parse the submission with Python's own `ast` module (so we get
real Python grammar for free), then walk the tree ourselves, evaluating node
by node against an explicit allow-list. Anything not on the allow-list
(imports, function/class defs, loops, lambdas, comprehensions, arbitrary
attribute access, double-underscore names, etc.) is rejected before a single
line of the submission actually runs.

This is a reasonable sandbox for a learning tool, not a security boundary
you should trust with hostile, incentivized attackers. If you deploy this
for real, also run the backend as a low-privilege, resource-limited process
(container, seccomp, a short wall-clock timeout, etc.) as defense in depth.
"""
import ast


class PyError(Exception):
    """Wraps a Python-style runtime error so the API can report it as
    `ErrorType: message`, mirroring what a real interpreter would say."""
    def __init__(self, kind, message):
        self.kind = kind
        super().__init__(f"{kind}: {message}")


class Unsupported(Exception):
    """Raised when the submission uses syntax outside the allowed subset."""
    pass


ALLOWED_BUILTINS = {
    'len': len, 'str': str, 'bool': bool, 'round': round,
    'abs': abs, 'min': min, 'max': max, 'sum': sum,
    'sorted': sorted, 'list': list,
}


def _py_int(x):
    if isinstance(x, str):
        s = x.strip()
        try:
            return int(s)
        except ValueError:
            raise PyError('ValueError', f"invalid literal for int(): {x!r}")
    return int(x)


def _py_float(x):
    if isinstance(x, str):
        s = x.strip()
        try:
            return float(s)
        except ValueError:
            raise PyError('ValueError', f"could not convert string to float: {x!r}")
    return float(x)


def _py_range(*args):
    return list(range(*[int(a) for a in args]))


ALLOWED_BUILTINS['int'] = _py_int
ALLOWED_BUILTINS['float'] = _py_float
ALLOWED_BUILTINS['range'] = _py_range

STR_METHODS = {'upper', 'lower', 'strip', 'title', 'capitalize', 'replace',
               'split', 'startswith', 'endswith', 'count', 'find', 'join', 'isdigit'}
LIST_METHODS = {'append', 'pop', 'count', 'index', 'sort', 'reverse', 'insert'}
DICT_METHODS = {'get', 'keys', 'values'}
ALL_METHODS = STR_METHODS | LIST_METHODS | DICT_METHODS

ALLOWED_EXPR = (
    ast.Expression, ast.Constant, ast.Name, ast.Load,
    ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare, ast.IfExp,
    ast.List, ast.Tuple, ast.Dict, ast.Set,
    ast.Subscript, ast.Slice, ast.Index,
    ast.Call, ast.Attribute,
    ast.JoinedStr, ast.FormattedValue,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow,
    ast.USub, ast.UAdd, ast.Not,
    ast.And, ast.Or,
    ast.Eq, ast.NotEq, ast.Lt, ast.Gt, ast.LtE, ast.GtE, ast.In, ast.NotIn,
)
ALLOWED_STMT = (ast.Module, ast.Assign, ast.AugAssign, ast.Expr, ast.Store)


def _check_node(node):
    if isinstance(node, ast.Attribute):
        if node.attr.startswith('_'):
            raise Unsupported(f"attribute access to '{node.attr}' is not allowed")
        if not isinstance(node.ctx, ast.Load):
            raise Unsupported("cannot assign to an attribute")
    elif isinstance(node, ast.Name):
        if node.id.startswith('_'):
            raise Unsupported(f"names starting with '_' are not allowed")
    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
                            ast.Import, ast.ImportFrom, ast.Lambda, ast.For,
                            ast.While, ast.If, ast.With, ast.Try, ast.ListComp,
                            ast.SetComp, ast.DictComp, ast.GeneratorExp,
                            ast.Global, ast.Nonlocal, ast.Delete, ast.Return,
                            ast.Yield, ast.YieldFrom, ast.Await)):
        name = type(node).__name__
        raise Unsupported(f"this challenge only accepts simple assignment/expression "
                           f"lines \u2014 '{name}' is not supported here")
    elif not isinstance(node, ALLOWED_EXPR + ALLOWED_STMT):
        raise Unsupported(f"unsupported syntax: {type(node).__name__}")
    for child in ast.iter_child_nodes(node):
        _check_node(child)


def _py_type(v):
    if v is None:
        return 'NoneType'
    if isinstance(v, bool):
        return 'bool'
    if isinstance(v, int):
        return 'int'
    if isinstance(v, float):
        return 'float'
    if isinstance(v, str):
        return 'str'
    if isinstance(v, list):
        return 'list'
    if isinstance(v, dict):
        return 'dict'
    return type(v).__name__


class Evaluator:
    def __init__(self):
        self.env = {}

    def run(self, src):
        try:
            tree = ast.parse(src, mode='exec')
        except SyntaxError as e:
            raise PyError('SyntaxError', str(e))
        _check_node(tree)
        for stmt in tree.body:
            self.exec_stmt(stmt)
        return self.env

    def exec_stmt(self, node):
        if isinstance(node, ast.Assign):
            value = self.eval_expr(node.value)
            for target in node.targets:
                self.assign(target, value)
        elif isinstance(node, ast.AugAssign):
            if not isinstance(node.target, ast.Name):
                raise Unsupported("augmented assignment only supported for simple names")
            name = node.target.id
            if name not in self.env:
                raise PyError('NameError', f"name '{name}' is not defined")
            op = type(node.op)
            rhs = self.eval_expr(node.value)
            self.env[name] = self.binop(op, self.env[name], rhs)
        elif isinstance(node, ast.Expr):
            self.eval_expr(node.value)
        else:
            raise Unsupported(f"unsupported statement: {type(node).__name__}")

    def assign(self, target, value):
        if isinstance(target, ast.Name):
            self.env[target.id] = value
        else:
            raise Unsupported("only simple variable assignment is supported")

    def eval_expr(self, node):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            if node.id not in self.env:
                raise PyError('NameError', f"name '{node.id}' is not defined")
            return self.env[node.id]
        if isinstance(node, ast.BinOp):
            return self.binop(type(node.op), self.eval_expr(node.left), self.eval_expr(node.right))
        if isinstance(node, ast.UnaryOp):
            v = self.eval_expr(node.operand)
            if isinstance(node.op, ast.USub):
                return -v
            if isinstance(node.op, ast.UAdd):
                return +v
            if isinstance(node.op, ast.Not):
                return not v
        if isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                result = True
                for v in node.values:
                    result = self.eval_expr(v)
                    if not result:
                        return result
                return result
            else:
                result = False
                for v in node.values:
                    result = self.eval_expr(v)
                    if result:
                        return result
                return result
        if isinstance(node, ast.Compare):
            left = self.eval_expr(node.left)
            for op, comp in zip(node.ops, node.comparators):
                right = self.eval_expr(comp)
                if not self.compare(type(op), left, right):
                    return False
                left = right
            return True
        if isinstance(node, ast.IfExp):
            return self.eval_expr(node.body) if self.eval_expr(node.test) else self.eval_expr(node.orelse)
        if isinstance(node, ast.List):
            return [self.eval_expr(e) for e in node.elts]
        if isinstance(node, ast.Tuple):
            return tuple(self.eval_expr(e) for e in node.elts)
        if isinstance(node, ast.Set):
            return {self.eval_expr(e) for e in node.elts}
        if isinstance(node, ast.Dict):
            return {self.eval_expr(k): self.eval_expr(v) for k, v in zip(node.keys, node.values)}
        if isinstance(node, ast.Subscript):
            obj = self.eval_expr(node.value)
            sl = node.slice
            if isinstance(sl, ast.Slice):
                lo = self.eval_expr(sl.lower) if sl.lower else None
                hi = self.eval_expr(sl.upper) if sl.upper else None
                step = self.eval_expr(sl.step) if sl.step else None
                return obj[lo:hi:step]
            idx = self.eval_expr(sl.value if isinstance(sl, ast.Index) else sl)
            try:
                return obj[idx]
            except KeyError:
                raise PyError('KeyError', repr(idx))
            except IndexError:
                raise PyError('IndexError', 'list index out of range')
            except TypeError as e:
                raise PyError('TypeError', str(e))
        if isinstance(node, ast.JoinedStr):
            parts = []
            for v in node.values:
                if isinstance(v, ast.Constant):
                    parts.append(str(v.value))
                elif isinstance(v, ast.FormattedValue):
                    val = self.eval_expr(v.value)
                    spec = ''
                    if v.format_spec:
                        spec = ''.join(
                            c.value if isinstance(c, ast.Constant) else str(self.eval_expr(c))
                            for c in v.format_spec.values
                        )
                    parts.append(format(val, spec) if spec else str(val))
            return ''.join(parts)
        if isinstance(node, ast.Call):
            return self.call(node)
        raise Unsupported(f"unsupported expression: {type(node).__name__}")

    def call(self, node):
        func = node.func
        args = [self.eval_expr(a) for a in node.args]
        if isinstance(func, ast.Name):
            if func.id not in ALLOWED_BUILTINS:
                raise PyError('NameError', f"name '{func.id}' is not defined")
            try:
                return ALLOWED_BUILTINS[func.id](*args)
            except ZeroDivisionError:
                raise PyError('ZeroDivisionError', 'division by zero')
            except (TypeError, ValueError) as e:
                raise PyError(type(e).__name__, str(e))
        if isinstance(func, ast.Attribute):
            obj = self.eval_expr(func.value)
            method = func.attr
            if method not in ALL_METHODS:
                raise PyError('AttributeError', f"'{_py_type(obj)}' object has no attribute '{method}'")
            if not hasattr(obj, method):
                raise PyError('AttributeError', f"'{_py_type(obj)}' object has no attribute '{method}'")
            try:
                result = getattr(obj, method)(*args)
            except (TypeError, ValueError, IndexError) as e:
                raise PyError(type(e).__name__, str(e))
            # .get() on a dict with one arg should default to None like real Python (already does)
            return result
        raise Unsupported("calls are only supported for a small set of built-ins and methods")

    def binop(self, op, a, b):
        try:
            if op is ast.Add:
                return a + b
            if op is ast.Sub:
                return a - b
            if op is ast.Mult:
                return a * b
            if op is ast.Div:
                return a / b
            if op is ast.FloorDiv:
                return a // b
            if op is ast.Mod:
                return a % b
            if op is ast.Pow:
                return a ** b
        except ZeroDivisionError:
            raise PyError('ZeroDivisionError', 'division by zero')
        except TypeError as e:
            raise PyError('TypeError', str(e))
        raise Unsupported(f"unsupported operator: {op}")

    def compare(self, op, a, b):
        try:
            if op is ast.Eq:
                return a == b
            if op is ast.NotEq:
                return a != b
            if op is ast.Lt:
                return a < b
            if op is ast.Gt:
                return a > b
            if op is ast.LtE:
                return a <= b
            if op is ast.GtE:
                return a >= b
            if op is ast.In:
                return a in b
            if op is ast.NotIn:
                return a not in b
        except TypeError as e:
            raise PyError('TypeError', str(e))
        raise Unsupported(f"unsupported comparison: {op}")


def run_submission(code, max_lines=40):
    """Run a learner's submission and return (env_dict, error_message_or_None)."""
    if len(code.splitlines()) > max_lines:
        return {}, f"SyntaxError: that's more lines than this challenge expects (max {max_lines})"
    try:
        ev = Evaluator()
        env = ev.run(code)
        return env, None
    except Unsupported as e:
        return {}, f"SyntaxError: {e}"
    except PyError as e:
        return {}, str(e)
    except RecursionError:
        return {}, "RecursionError: expression nested too deeply"


def values_equal(a, b):
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b or (isinstance(a, bool) and isinstance(b, bool) and a == b)
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) < 1e-9
    return a == b


def py_repr(v):
    if isinstance(v, str):
        return repr(v)
    return repr(v)
