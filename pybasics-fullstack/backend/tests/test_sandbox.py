import pytest

from app.sandbox import UnsafeCode, _validate, ast, run_user_code


@pytest.mark.parametrize(
    "code",
    [
        "import os",
        "x = open('secret.txt')",
        "x = (1).__class__",
        "x = (1).__class__.__mro__",
        "def escape():\n    return 1",
        "while True:\n    pass",
    ],
)
def test_rejects_unsafe_syntax_and_private_access(code):
    with pytest.raises(UnsafeCode):
        _validate(ast.parse(code, mode="exec"))


def test_malformed_code_returns_a_syntax_error():
    result = run_user_code("x = (")
    assert result["ok"] is False
    assert result["error"].startswith("SyntaxError:")


def test_simple_supported_code_runs():
    result = run_user_code("name = 'pybasics'.upper()\ncount = len([1, 2, 3])")
    assert result == {
        "ok": True,
        "vars": {"name": "PYBASICS", "count": 3},
        "error": None,
    }


def test_oversized_submission_is_rejected_before_spawning_child():
    result = run_user_code("x = 1\n" + (" " * 4001))
    assert result["ok"] is False
    assert "under 4000 characters" in result["error"]


def test_memory_pressure_fails_without_crashing_test_process():
    result = run_user_code("items = [0] * 100000000")
    assert result["ok"] is False
    assert result["vars"] == {}


def test_cpu_heavy_expression_is_stopped():
    result = run_user_code("value = 9 ** 999999999")
    assert result["ok"] is False
    assert result["vars"] == {}
