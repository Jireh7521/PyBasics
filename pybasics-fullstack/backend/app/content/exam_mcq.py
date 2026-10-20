"""Level 1-3 multiple-choice question generators -- ported from the original
browser-only version's JS generators (T_arithmetic, T_type, T_boolean,
T_string, T_conversion, T_list, T_conditional). Each returns a dict with the
correct answer's INDEX included -- callers must strip that before sending
anything to the frontend before grading."""
import random


def randint(a, b):
    return random.randint(a, b)


def pick(seq):
    return random.choice(seq)


def py_float(n):
    if float(n).is_integer():
        return f"{int(n)}.0"
    s = f"{n:.4f}".rstrip("0")
    if s.endswith("."):
        s += "0"
    return s


def shuffle_options(options, correct_idx):
    paired = list(enumerate(options))
    random.shuffle(paired)
    new_options = [o for _, o in paired]
    new_correct = next(i for i, (orig_i, _) in enumerate(paired) if orig_i == correct_idx)
    return new_options, new_correct


def finalize(correct_str, wrong_list):
    seen = {correct_str}
    uniq = []
    for w in wrong_list:
        w = str(w)
        if w not in seen:
            seen.add(w)
            uniq.append(w)
        if len(uniq) >= 3:
            break
    pool = ["N/A", "None of these", "\u2014", "Error"]
    pi = 0
    while len(uniq) < 3 and pi < len(pool):
        if pool[pi] not in seen:
            seen.add(pool[pi])
            uniq.append(pool[pi])
        pi += 1
    return shuffle_options([correct_str] + uniq, 0)


def T_arithmetic():
    op = pick(["+", "-", "*", "//", "%", "/"])
    if op == "/":
        b = pick([2, 3, 4, 5, 8]); a = randint(b, b * 9)
        correct = a / b; correct_str = py_float(correct)
    elif op == "//":
        b = randint(2, 9); a = randint(10, 80); correct = a // b; correct_str = str(correct)
    elif op == "%":
        b = randint(2, 9); a = randint(10, 80); correct = a % b; correct_str = str(correct)
    elif op == "+":
        a = randint(1, 50); b = randint(1, 50); correct = a + b; correct_str = str(correct)
    elif op == "-":
        a = randint(20, 80); b = randint(1, 19); correct = a - b; correct_str = str(correct)
    else:
        a = randint(2, 12); b = randint(2, 12); correct = a * b; correct_str = str(correct)
    code = f"result = {a} {op} {b}\nprint(result)"
    deltas = [1, -1, 0.5, -0.5, 2] if op == "/" else [1, -1, 2, -2, 5, -5]
    wrong = []
    for d in deltas:
        v = correct + d
        s = py_float(v) if op == "/" else str(int(v))
        if s not in wrong and s != correct_str:
            wrong.append(s)
    options, ci = finalize(correct_str, wrong)
    return {"topic": "Arithmetic", "q": "What does this print?", "code": code, "options": options, "correct": ci,
            "explain": f"Working through <code>{a} {op} {b}</code> step by step gives <code>{correct_str}</code>."}


def T_type():
    items = [
        {"lit": "42", "type": "int"}, {"lit": "3.14", "type": "float"}, {"lit": '"hello"', "type": "str"},
        {"lit": "True", "type": "bool"}, {"lit": "[1, 2, 3]", "type": "list"}, {"lit": '{"a": 1}', "type": "dict"},
        {"lit": "None", "type": "NoneType"}, {"lit": "(1, 2)", "type": "tuple"},
    ]
    it = pick(items)
    all_types = ["int", "float", "str", "bool", "list", "dict", "NoneType", "tuple"]
    wrong = [t for t in all_types if t != it["type"]]
    random.shuffle(wrong); wrong = wrong[:3]
    options, ci = finalize(it["type"], wrong)
    return {"topic": "Data types", "q": f"What does type({it['lit']}) return?", "code": None, "options": options, "correct": ci,
            "explain": f"<code>{it['lit']}</code> is a Python <code>{it['type']}</code>, so <code>type()</code> reports <code>&lt;class '{it['type']}'&gt;</code>."}


def T_boolean():
    a = pick([True, False]); b = pick([True, False])
    op = pick(["and", "or", "not"])
    if op == "and":
        code = f"a = {a}\nb = {b}\nprint(a and b)"; correct = "True" if (a and b) else "False"
    elif op == "or":
        code = f"a = {a}\nb = {b}\nprint(a or b)"; correct = "True" if (a or b) else "False"
    else:
        code = f"a = {a}\nprint(not a)"; correct = "True" if (not a) else "False"
    wrong = [v for v in ["True", "False", "None", "Error"] if v != correct][:3]
    options, ci = finalize(correct, wrong)
    return {"topic": "Booleans & logic", "q": "What does this print?", "code": code, "options": options, "correct": ci,
            "explain": f"Evaluating the boolean expression gives <code>{correct}</code>."}


def T_string():
    w = pick(["Python", "Coding", "Variable", "Function", "Keyboard", "Sunshine"])
    kind = pick(["slice", "upper", "lower", "len", "index"])
    if kind == "slice":
        start = randint(0, 2); end = randint(start + 2, min(len(w), start + 5))
        code = f'text = "{w}"\nprint(text[{start}:{end}])'
        correct = w[start:end]
        wrong = [w[start:end + 1], w[max(0, start - 1):end], w[start + 1:end]]
    elif kind == "upper":
        code = f'text = "{w}"\nprint(text.upper())'; correct = w.upper()
        wrong = [w, w.lower(), w.upper() + "!"]
    elif kind == "lower":
        code = f'text = "{w}"\nprint(text.lower())'; correct = w.lower()
        wrong = [w, w.upper(), w.lower()[1:]]
    elif kind == "len":
        code = f'text = "{w}"\nprint(len(text))'; correct = str(len(w))
        wrong = [str(len(w) - 1), str(len(w) + 1), str(len(w) + 2)]
    else:
        idx = randint(0, len(w) - 1)
        code = f'text = "{w}"\nprint(text[{idx}])'; correct = w[idx]
        others = {correct}; wrong = []
        while len(wrong) < 3:
            c = w[randint(0, len(w) - 1)]
            if c not in others:
                others.add(c); wrong.append(c)
    options, ci = finalize(correct, wrong)
    second_line = code.split("\n")[1]
    return {"topic": "Strings", "q": "What does this print?", "code": code, "options": options, "correct": ci,
            "explain": f"Tracing the code: <code>{second_line}</code> outputs <code>{correct}</code>."}


def T_list():
    arr = pick([[3, 7, 1, 9, 5], [10, 20, 30, 40], [2, 4, 6, 8, 10], [15, 3, 42, 8]])
    kind = pick(["index", "len", "append", "sum", "slice"])
    arr_lit = ", ".join(str(v) for v in arr)
    if kind == "index":
        idx = randint(0, len(arr) - 1)
        code = f"nums = [{arr_lit}]\nprint(nums[{idx}])"; correct = str(arr[idx])
        others = [v for i, v in enumerate(arr) if i != idx]
        random.shuffle(others)
        wrong = [str(v) for v in others[:3]]
    elif kind == "len":
        code = f"nums = [{arr_lit}]\nprint(len(nums))"; correct = str(len(arr))
        wrong = [str(len(arr) - 1), str(len(arr) + 1), str(len(arr) + 2)]
    elif kind == "append":
        code = f"nums = [{arr_lit}]\nnums.append(100)\nprint(len(nums))"; correct = str(len(arr) + 1)
        wrong = [str(len(arr)), str(len(arr) + 2), str(len(arr) - 1)]
    elif kind == "sum":
        code = f"nums = [{arr_lit}]\nprint(sum(nums))"
        s = sum(arr); correct = str(s)
        wrong = [str(s + arr[0]), str(max(0, s - arr[0])), str(s + 10)]
    else:
        start = randint(0, 1); end = randint(start + 1, len(arr))
        code = f"nums = [{arr_lit}]\nprint(nums[{start}:{end}])"
        correct = "[" + ", ".join(str(v) for v in arr[start:end]) + "]"
        wrong = [
            "[" + ", ".join(str(v) for v in arr[start:min(len(arr), end + 1)]) + "]",
            "[" + ", ".join(str(v) for v in arr[0:end]) + "]",
            "[" + ", ".join(str(v) for v in arr[start:]) + "]",
        ]
    options, ci = finalize(correct, wrong)
    return {"topic": "Lists", "q": "What does this print?", "code": code, "options": options, "correct": ci,
            "explain": f"Tracing the code line by line gives <code>{correct}</code>."}


def T_conditional():
    x = randint(-5, 25); t1 = randint(15, 20); t2 = randint(5, 10)
    code = f"x = {x}\nif x > {t1}:\n    print(\"high\")\nelif x > {t2}:\n    print(\"medium\")\nelse:\n    print(\"low\")"
    correct = "high" if x > t1 else "medium" if x > t2 else "low"
    opts = ["high", "medium", "low", "Nothing \u2014 this is a syntax error"]
    options, ci = shuffle_options(opts, opts.index(correct))
    why = (f"Since {x} &gt; {t1}, the first branch runs." if x > t1 else
           f"{x} isn't &gt; {t1}, but it is &gt; {t2}, so the elif branch runs." if x > t2 else
           f"{x} isn't greater than {t1} or {t2}, so the else branch runs.")
    return {"topic": "Conditionals", "q": "What does this print?", "code": code, "options": options, "correct": ci,
            "explain": f"x is {x}. {why}"}


def T_conversion():
    kind = pick(["int-from-str", "str-from-int", "float-from-int", "bool-zero", "bool-str"])
    if kind == "int-from-str":
        n = randint(1, 99)
        code = f'x = int("{n}")\nprint(x + 1)'; correct = str(n + 1)
        wrong = [f'"{n}1"', "TypeError", str(n)]
    elif kind == "str-from-int":
        n = randint(1, 99)
        code = f'x = str({n})\nprint(x + "0")'; correct = f'"{n}0"'
        wrong = [str(n * 10), "TypeError", f'"{n}"']
    elif kind == "float-from-int":
        n = randint(1, 20)
        code = f"x = float({n})\nprint(x)"; correct = py_float(n)
        wrong = [str(n), py_float(n + 1), py_float(max(0, n - 1))]
    elif kind == "bool-zero":
        code = "print(bool(0))"; correct = "False"; wrong = ["True", "None", "Error"]
    else:
        code = 'print(bool(""))'; correct = "False"; wrong = ["True", "None", "Error"]
    options, ci = finalize(correct, wrong)
    return {"topic": "Type conversion", "q": "What does this print?", "code": code, "options": options, "correct": ci,
            "explain": f"Converting and evaluating step by step gives <code>{correct}</code>."}


MCQ_POOLS = {
    "T_arithmetic": T_arithmetic, "T_type": T_type, "T_boolean": T_boolean,
    "T_string": T_string, "T_conversion": T_conversion, "T_list": T_list,
    "T_conditional": T_conditional,
}
