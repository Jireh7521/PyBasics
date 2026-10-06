"""
Question generators for the exam, ported from the original client-side JS.

MCQ generators (T_*) return a dict:
  {topic, q, code, options, correct, explain}
Code-challenge generators (C_*, H_*) return a dict:
  {topic, kind: 'code', q, starter, expected, explain}

Expected values and the correct option index are NEVER sent to the client --
app.py strips them before responding and keeps the full dict server-side
(in-memory, keyed by the attempt) to grade against later.
"""
import random


def rnd(a, b):
    return random.randint(a, b)


def pick(seq):
    return random.choice(seq)


def py_float_str(n):
    if float(n).is_integer():
        return f"{n:.1f}"
    s = f"{n:.4f}".rstrip('0')
    if s.endswith('.'):
        s += '0'
    return s


def py_bool_str(b):
    return 'True' if b else 'False'


def finalize(correct_str, wrong):
    seen = {correct_str}
    uniq = []
    for w in wrong:
        w = str(w)
        if w not in seen:
            seen.add(w)
            uniq.append(w)
        if len(uniq) >= 3:
            break
    pool = ['N/A', 'None of these', '\u2014', 'Error']
    pi = 0
    while len(uniq) < 3 and pi < len(pool):
        if pool[pi] not in seen:
            seen.add(pool[pi])
            uniq.append(pool[pi])
        pi += 1
    options = [correct_str] + uniq
    random.shuffle(options)
    return options, options.index(correct_str)


# ------------------------------------------------------------------ MCQ (Levels 1-3)

def T_arithmetic():
    op = pick(['+', '-', '*', '//', '%', '/'])
    if op == '/':
        b = pick([2, 3, 4, 5, 8]); a = rnd(b, b * 9)
        correct = a / b; correct_str = py_float_str(correct)
    elif op == '//':
        b = rnd(2, 9); a = rnd(10, 80); correct = a // b; correct_str = str(correct)
    elif op == '%':
        b = rnd(2, 9); a = rnd(10, 80); correct = a % b; correct_str = str(correct)
    elif op == '+':
        a = rnd(1, 50); b = rnd(1, 50); correct = a + b; correct_str = str(correct)
    elif op == '-':
        a = rnd(20, 80); b = rnd(1, 19); correct = a - b; correct_str = str(correct)
    else:
        a = rnd(2, 12); b = rnd(2, 12); correct = a * b; correct_str = str(correct)
    code = f"result = {a} {op} {b}\nprint(result)"
    if op == '/':
        deltas = [1, -1, 0.5, -0.5, 2]
        wrong = [py_float_str(correct + d) for d in deltas]
    else:
        deltas = [1, -1, 2, -2, 5, -5]
        wrong = [str(round(correct + d)) for d in deltas]
    options, ci = finalize(correct_str, wrong)
    op_name = {'+': 'addition', '-': 'subtraction', '*': 'multiplication', '//': 'floor division',
               '%': 'the modulo operator', '/': 'true division'}[op]
    return {'topic': 'Numbers & operators', 'q': 'What does this code print?', 'code': code,
            'options': options, 'correct': ci,
            'explain': f"This uses {op_name}. <code>{a} {op} {b}</code> evaluates to <code>{correct_str}</code>."}


def T_type():
    items = [{'lit': '42', 'type': 'int'}, {'lit': '3.14', 'type': 'float'}, {'lit': '"hello"', 'type': 'str'},
              {'lit': 'True', 'type': 'bool'}, {'lit': '[1, 2, 3]', 'type': 'list'}, {'lit': '{"a": 1}', 'type': 'dict'},
              {'lit': 'None', 'type': 'NoneType'}, {'lit': '(1, 2)', 'type': 'tuple'}]
    it = pick(items)
    all_types = ['int', 'float', 'str', 'bool', 'list', 'dict', 'NoneType', 'tuple']
    wrong = random.sample([t for t in all_types if t != it['type']], 3)
    options, ci = finalize(it['type'], wrong)
    return {'topic': 'Data types', 'q': f"What does type({it['lit']}) return?", 'code': None,
            'options': options, 'correct': ci,
            'explain': f"<code>{it['lit']}</code> is a Python <code>{it['type']}</code>, so <code>type()</code> reports <code>&lt;class '{it['type']}'&gt;</code>."}


def T_string():
    w = pick(['Python', 'Coding', 'Variable', 'Function', 'Keyboard', 'Sunshine'])
    kind = pick(['slice', 'upper', 'lower', 'len', 'index'])
    if kind == 'slice':
        start = rnd(0, 2); end = rnd(start + 2, min(len(w), start + 5))
        code = f'text = "{w}"\nprint(text[{start}:{end}])'
        correct = w[start:end]
        wrong = [w[start:end + 1], w[max(0, start - 1):end], w[start + 1:end]]
    elif kind == 'upper':
        code = f'text = "{w}"\nprint(text.upper())'; correct = w.upper()
        wrong = [w, w.lower(), w.upper() + '!']
    elif kind == 'lower':
        code = f'text = "{w}"\nprint(text.lower())'; correct = w.lower()
        wrong = [w, w.upper(), w.lower()[1:]]
    elif kind == 'len':
        code = f'text = "{w}"\nprint(len(text))'; correct = str(len(w))
        wrong = [str(len(w) - 1), str(len(w) + 1), str(len(w) + 2)]
    else:
        idx = rnd(0, len(w) - 1)
        code = f'text = "{w}"\nprint(text[{idx}])'; correct = w[idx]
        others = {correct}; wrong = []
        while len(wrong) < 3:
            c = w[rnd(0, len(w) - 1)]
            if c not in others:
                others.add(c); wrong.append(c)
    options, ci = finalize(correct, wrong)
    return {'topic': 'Strings', 'q': 'What does this print?', 'code': code, 'options': options, 'correct': ci,
            'explain': f"Tracing the code: <code>{code.splitlines()[1]}</code> outputs <code>{correct}</code>."}


def T_list():
    arr = pick([[3, 7, 1, 9, 5], [10, 20, 30, 40], [2, 4, 6, 8, 10], [15, 3, 42, 8]])
    kind = pick(['index', 'len', 'append', 'sum', 'slice'])
    arr_str = ', '.join(map(str, arr))
    if kind == 'index':
        idx = rnd(0, len(arr) - 1)
        code = f"nums = [{arr_str}]\nprint(nums[{idx}])"; correct = str(arr[idx])
        others = [v for i, v in enumerate(arr) if i != idx]
        random.shuffle(others)
        wrong = [str(v) for v in others[:3]]
    elif kind == 'len':
        code = f"nums = [{arr_str}]\nprint(len(nums))"; correct = str(len(arr))
        wrong = [str(len(arr) - 1), str(len(arr) + 1), str(len(arr) + 2)]
    elif kind == 'append':
        code = f"nums = [{arr_str}]\nnums.append(100)\nprint(len(nums))"; correct = str(len(arr) + 1)
        wrong = [str(len(arr)), str(len(arr) + 2), str(len(arr) - 1)]
    elif kind == 'sum':
        code = f"nums = [{arr_str}]\nprint(sum(nums))"
        s = sum(arr); correct = str(s)
        wrong = [str(s + arr[0]), str(max(0, s - arr[0])), str(s + 10)]
    else:
        start = rnd(0, 1); end = rnd(start + 1, len(arr))
        code = f"nums = [{arr_str}]\nprint(nums[{start}:{end}])"
        correct = '[' + ', '.join(map(str, arr[start:end])) + ']'
        wrong = ['[' + ', '.join(map(str, arr[start:min(len(arr), end + 1)])) + ']',
                 '[' + ', '.join(map(str, arr[:end])) + ']',
                 '[' + ', '.join(map(str, arr[start:])) + ']']
    options, ci = finalize(correct, wrong)
    return {'topic': 'Lists', 'q': 'What does this print?', 'code': code, 'options': options, 'correct': ci,
            'explain': f"Tracing the code line by line gives <code>{correct}</code>."}


def T_conditional():
    x = rnd(-5, 25); t1 = rnd(15, 20); t2 = rnd(5, 10)
    code = f"x = {x}\nif x > {t1}:\n    print(\"high\")\nelif x > {t2}:\n    print(\"medium\")\nelse:\n    print(\"low\")"
    correct = 'high' if x > t1 else 'medium' if x > t2 else 'low'
    opts = ['high', 'medium', 'low', 'Nothing \u2014 this is a syntax error']
    ci = opts.index(correct)
    options, ci = finalize_fixed(opts, ci)
    why = (f"Since {x} &gt; {t1}, the first branch runs." if x > t1 else
           f"{x} isn't &gt; {t1}, but it is &gt; {t2}, so the elif branch runs." if x > t2 else
           f"{x} isn't greater than {t1} or {t2}, so the else branch runs.")
    return {'topic': 'Conditionals', 'q': 'What does this print?', 'code': code, 'options': options, 'correct': ci,
            'explain': f"x is {x}. {why}"}


def finalize_fixed(options, correct_idx):
    """Shuffle a fixed option list (used when the option set must stay exact, e.g. T_conditional)."""
    pairs = list(enumerate(options))
    random.shuffle(pairs)
    new_options = [o for _, o in pairs]
    new_correct = [i for i, (orig_i, _) in enumerate(pairs) if orig_i == correct_idx][0]
    return new_options, new_correct


def T_boolean():
    a = pick([True, False]); b = pick([True, False])
    op = pick(['and', 'or', 'not'])
    if op == 'and':
        code = f"a = {py_bool_str(a)}\nb = {py_bool_str(b)}\nprint(a and b)"; correct = py_bool_str(a and b)
    elif op == 'or':
        code = f"a = {py_bool_str(a)}\nb = {py_bool_str(b)}\nprint(a or b)"; correct = py_bool_str(a or b)
    else:
        code = f"a = {py_bool_str(a)}\nprint(not a)"; correct = py_bool_str(not a)
    wrong = [v for v in ['True', 'False', 'None', 'Error'] if v != correct][:3]
    options, ci = finalize(correct, wrong)
    return {'topic': 'Booleans & logic', 'q': 'What does this print?', 'code': code, 'options': options,
            'correct': ci, 'explain': f"Evaluating the boolean expression gives <code>{correct}</code>."}


def T_conversion():
    kind = pick(['int-from-str', 'str-from-int', 'float-from-int', 'bool-zero', 'bool-str'])
    if kind == 'int-from-str':
        n = rnd(1, 99)
        code = f'x = int("{n}")\nprint(x + 1)'; correct = str(n + 1)
        wrong = [f'"{n}1"', 'TypeError', str(n)]
    elif kind == 'str-from-int':
        n = rnd(1, 99)
        code = f'x = str({n})\nprint(x + "0")'; correct = f'"{n}0"'
        wrong = [str(n * 10), 'TypeError', f'"{n}"']
    elif kind == 'float-from-int':
        n = rnd(1, 20)
        code = f'x = float({n})\nprint(x)'; correct = py_float_str(n)
        wrong = [str(n), py_float_str(n + 1), py_float_str(max(0, n - 1))]
    elif kind == 'bool-zero':
        code = 'print(bool(0))'; correct = 'False'; wrong = ['True', 'None', 'Error']
    else:
        code = 'print(bool(""))'; correct = 'False'; wrong = ['True', 'None', 'Error']
    options, ci = finalize(correct, wrong)
    return {'topic': 'Type conversion', 'q': 'What does this print?', 'code': code, 'options': options,
            'correct': ci, 'explain': f"Converting between types here produces <code>{correct}</code>."}


T_POOL = [T_arithmetic, T_type, T_boolean]
T_POOL_2 = [T_arithmetic, T_type, T_boolean, T_string, T_conversion]
T_POOL_3 = [T_arithmetic, T_type, T_boolean, T_string, T_conversion, T_list, T_conditional]


# ------------------------------------------------------------- Code challenges (Levels 4-5)

def _cap(s):
    return s[:1].upper() + s[1:]


def code_ins(story, task):
    return f"<h4>Instructions</h4><p>{story}</p><p><strong>Your Task:</strong> {task}</p>"


def code_item(topic, story, task, starter, expected, explain):
    return {'topic': topic, 'kind': 'code', 'q': code_ins(story, task), 'starter': starter,
            'expected': expected, 'explain': explain}


def C_arith():
    n = rnd(2, 5); sc = pick([1.5, 2.5, 0.5, 2]); mk = pick([0.75, 1.25, 1.5, 0.5])
    cs = n * sc + rnd(2, 9); ms = n * mk + rnd(3, 12)
    return code_item('Arithmetic Operators',
        f"A robot needs to make cereal for {n} customers. Each person gets exactly <code>{sc}</code> scoops of cereal and <code>{mk}</code> cups of milk. The kitchen starts with <code>{cs}</code> scoops of cereal and <code>{ms}</code> cups of milk.",
        'Using the arithmetic operators <code>*</code> and <code>-</code>, set the four variables at the bottom to the total cereal and milk needed, and the amounts left after serving everyone.',
        f"customers = {n}\nscoops_each = {sc}\nmilk_each = {mk}\ncereal_stock = {cs}\nmilk_stock = {ms}\n\ncereal_needed = 0\nmilk_needed = 0\ncereal_left = 0\nmilk_left = 0",
        {'cereal_needed': n * sc, 'milk_needed': n * mk, 'cereal_left': cs - n * sc, 'milk_left': ms - n * mk},
        'Multiply the per-person amount by the number of customers, then subtract that from the starting stock.')


def C_divmod():
    box = rnd(4, 12); total = box * rnd(3, 9) + rnd(1, box - 1)
    return code_item('Arithmetic Operators',
        f"A bakery has <code>{total}</code> cookies and packs them into boxes that each hold exactly <code>{box}</code> cookies.",
        'Use <code>//</code> to find how many boxes are completely full, and <code>%</code> to find how many cookies are left over.',
        f"cookies = {total}\nbox_size = {box}\n\nfull_boxes = 0\nleftover = 0",
        {'full_boxes': total // box, 'leftover': total % box},
        '<code>//</code> gives the whole number of times one number fits into another; <code>%</code> gives what remains.')


def C_string():
    F = ['ada', 'grace', 'alan', 'linus', 'margaret', 'dennis']; Z = ['lovelace', 'hopper', 'turing', 'torvalds', 'hamilton', 'ritchie']
    f = pick(F); l = pick(Z)
    return code_item('Strings',
        "A school prints name badges. The first and last name arrive in lowercase.",
        'Set <code>full_name</code> to both names in Title Case with a space between them, <code>initials</code> to the two first letters in uppercase (like <code>"AL"</code>), and <code>name_length</code> to the number of characters in <code>full_name</code>.',
        f'first = "{f}"\nlast = "{l}"\n\nfull_name = ""\ninitials = ""\nname_length = 0',
        {'full_name': _cap(f) + ' ' + _cap(l), 'initials': (f[0] + l[0]).upper(), 'name_length': len(f) + len(l) + 1},
        'Use <code>.title()</code>, join with <code>+</code> and a space, index with <code>[0]</code> plus <code>.upper()</code>, and <code>len()</code>.')


def C_list():
    s = [rnd(50, 99) for _ in range(4)]; x = rnd(50, 99); allv = s + [x]
    return code_item('Lists',
        'A teacher keeps quiz scores in a list. A late score has just been added to the list.',
        'Set <code>highest</code> to the best score, <code>total</code> to the sum of all scores, <code>count</code> to how many scores there are, and <code>average</code> to the total divided by the count (do not round).',
        f"scores = [{', '.join(map(str, s))}]\nscores.append({x})\n\nhighest = 0\ntotal = 0\ncount = 0\naverage = 0",
        {'highest': max(allv), 'total': sum(allv), 'count': len(allv), 'average': sum(allv) / len(allv)},
        'Use <code>max()</code>, <code>sum()</code> and <code>len()</code>; the average is <code>total / count</code>.')


def C_convert():
    age = rnd(18, 60); price = pick([9.5, 12.25, 19.5, 4.75])
    return code_item('Type Conversion',
        'A form gives you numbers as text, so they cannot be used in maths until they are converted.',
        'Set <code>age_next_year</code> to the age plus one (use <code>int()</code>), <code>double_price</code> to twice the price (use <code>float()</code>), and <code>label</code> to <code>"Next year: "</code> followed by the age (use <code>str()</code>).',
        f'age_text = "{age}"\nprice_text = "{price}"\n\nage_next_year = 0\ndouble_price = 0\nlabel = ""',
        {'age_next_year': age + 1, 'double_price': price * 2, 'label': f"Next year: {age + 1}"},
        'Convert first with <code>int()</code> / <code>float()</code>, then do the maths; <code>str()</code> turns a number back into text so it can join with other text.')


def C_dict():
    a = rnd(3, 12); b = rnd(2, 9)
    return code_item('Dictionaries',
        'A shop tracks its fruit stock in a dictionary.',
        'Set <code>apple_count</code> to the stock of apples, <code>total_fruit</code> to apples plus pears, <code>has_kiwi</code> to whether <code>"kiwi"</code> is a key in the dictionary, and <code>kiwi_count</code> to the kiwi stock, or <code>0</code> if there is none (use <code>.get()</code>).',
        f'stock = {{"apples": {a}, "pears": {b}}}\n\napple_count = 0\ntotal_fruit = 0\nhas_kiwi = False\nkiwi_count = 0',
        {'apple_count': a, 'total_fruit': a + b, 'has_kiwi': False, 'kiwi_count': 0},
        'Look values up with <code>stock["apples"]</code>, test keys with <code>in</code>, and use <code>.get(key, 0)</code> for a safe lookup with a default.')


def C_bool():
    t = rnd(-5, 32); rain = pick([True, False])
    return code_item('Booleans & Logic',
        'A weather app decides what to tell the user each morning.',
        'Set <code>take_umbrella</code> to whether it is raining; <code>wear_coat</code> to <code>True</code> if the temperature is below <code>12</code> or it is raining; and <code>perfect_day</code> to <code>True</code> only when it is not raining and the temperature is from <code>20</code> to <code>28</code> (inclusive).',
        f"temperature = {t}\nis_raining = {py_bool_str(rain)}\n\ntake_umbrella = None\nwear_coat = None\nperfect_day = None",
        {'take_umbrella': rain, 'wear_coat': (t < 12) or rain, 'perfect_day': (not rain) and 20 <= t <= 28},
        'Combine comparisons with <code>and</code>, <code>or</code> and <code>not</code>.')


def H_arith():
    secs = rnd(3700, 20000); base = pick([2.5, 3, 4]); km = rnd(5, 30); rate = pick([0.5, 1.25, 1.5]); disc = pick([10, 20, 25])
    before = base + km * rate
    return code_item('Arithmetic Operators',
        f"A taxi ride lasted <code>{secs}</code> seconds and covered <code>{km}</code> km. The fare is a base fee of <code>{base}</code> plus <code>{rate}</code> per km, and then a <code>{disc}</code>% discount is taken off.",
        'Set <code>hours</code> and <code>minutes</code> to the whole hours and the remaining whole minutes of the ride, <code>fare_before</code> to the fare before the discount, and <code>fare_after</code> to the fare after the discount.',
        f"seconds = {secs}\nkm = {km}\nbase_fee = {base}\nrate_per_km = {rate}\ndiscount_percent = {disc}\n\nhours = 0\nminutes = 0\nfare_before = 0\nfare_after = 0",
        {'hours': secs // 3600, 'minutes': (secs % 3600) // 60, 'fare_before': before, 'fare_after': before * (1 - disc / 100)},
        '<code>//</code> and <code>%</code> split seconds into hours and minutes; the discounted fare is <code>fare_before * (1 - discount_percent / 100)</code>.')


def H_string():
    nm = pick(['Ada.Lovelace', 'Grace.Hopper', 'Alan.Turing', 'Linus.Torvalds']); dom = pick(['Example.com', 'School.org', 'Mail.net', 'Club.org'])
    clean = f"{nm}@{dom}".lower(); user, domain = clean.split('@')
    return code_item('Strings',
        'A sign-up form receives messy email addresses with extra spaces and mixed capitals.',
        'Set <code>clean</code> to the email with surrounding spaces removed and all letters lowercase; <code>username</code> to the part before the <code>@</code>; <code>domain</code> to the part after it; <code>slug</code> to the username with every <code>"."</code> replaced by <code>"-"</code>; and <code>is_org</code> to whether the domain ends with <code>".org"</code>.',
        f'raw_email = "  {nm}@{dom}  "\n\nclean = ""\nusername = ""\ndomain = ""\nslug = ""\nis_org = False',
        {'clean': clean, 'username': user, 'domain': domain, 'slug': user.replace('.', '-'), 'is_org': domain.endswith('.org')},
        'Chain string methods: <code>.strip().lower()</code>, <code>.split("@")</code> with indexing, <code>.replace()</code> and <code>.endswith()</code>.')


def H_list():
    nums = [rnd(1, 40) for _ in range(7)]
    if random.random() < 0.5:
        nums[rnd(0, 6)] = 10
    top3 = sorted(nums)[-3:]
    return code_item('Lists',
        'A game stores its recent scores in a list and needs a few summaries of it.',
        'Set <code>first_three</code> to the first three scores, <code>last_two</code> to the last two, <code>middle</code> to everything except the first and last score, <code>top_three_total</code> to the sum of the three largest scores, and <code>has_ten</code> to whether <code>10</code> is in the list.',
        f"nums = [{', '.join(map(str, nums))}]\n\nfirst_three = []\nlast_two = []\nmiddle = []\ntop_three_total = 0\nhas_ten = False",
        {'first_three': nums[:3], 'last_two': nums[-2:], 'middle': nums[1:-1], 'top_three_total': sum(top3), 'has_ten': 10 in nums},
        'Slices like <code>nums[:3]</code>, <code>nums[-2:]</code> and <code>nums[1:-1]</code>, plus <code>sorted()</code>, <code>sum()</code> and <code>in</code>.')


def H_dict():
    menu = {'tea': rnd(2, 5), 'cake': rnd(4, 9), 'juice': rnd(3, 7)}; keys = list(menu.keys())
    order = [pick(keys), pick(keys), pick(keys)]
    order_items = ', '.join(f'"{o}"' for o in order)
    return code_item('Dictionaries',
        'A cafe stores its menu prices in a dictionary, and an order is a list of item names.',
        'Set <code>first_price</code> to the price of the first item in the order, <code>order_total</code> to the total price of all three items, <code>pie_price</code> to the price of <code>"pie"</code> or <code>0</code> if it is not on the menu, and <code>priciest</code> to the highest price on the menu.',
        f'prices = {{"tea": {menu["tea"]}, "cake": {menu["cake"]}, "juice": {menu["juice"]}}}\norder = [{order_items}]\n\nfirst_price = 0\norder_total = 0\npie_price = 0\npriciest = 0',
        {'first_price': menu[order[0]], 'order_total': sum(menu[o] for o in order), 'pie_price': 0, 'priciest': max(menu.values())},
        'Combine lookups such as <code>prices[order[0]]</code>, <code>.get("pie", 0)</code> and <code>max(prices.values())</code>.')


def H_cond():
    score = rnd(30, 95); att = rnd(60, 100)
    bonus = 5 if att >= 90 else 0; fin = score + bonus
    return code_item('Conditional Expressions',
        'A course awards 5 bonus points for attendance of 90% or more, then assigns a grade.',
        'Using conditional expressions (<code>x if condition else y</code>), set <code>bonus</code> (5 or 0), <code>final_score</code> (score plus bonus), <code>grade</code> (<code>"A"</code> if final is 85 or more, otherwise <code>"B"</code> if 70 or more, otherwise <code>"C"</code>), and <code>passed</code> (<code>True</code> when final is at least 60 and attendance is at least 75).',
        f"score = {score}\nattendance = {att}\n\nbonus = 0\nfinal_score = 0\ngrade = \"\"\npassed = False",
        {'bonus': bonus, 'final_score': fin, 'grade': 'A' if fin >= 85 else 'B' if fin >= 70 else 'C', 'passed': fin >= 60 and att >= 75},
        'A conditional expression can be chained: <code>"A" if final_score >= 85 else "B" if final_score >= 70 else "C"</code>.')


def H_mix():
    nm = pick(['Ife', 'Chidi', 'Amara', 'Tunde']); out = pick([70, 80, 120, 150])
    while True:
        pts = rnd(30, out - 5)
        if round(pts / out * 1000) % 10 != 0:
            break
    pct = round(pts / out * 100, 1)
    return code_item('Type Conversion & Strings',
        "A results sheet stores a student's points as text. You need to turn it into a percentage and a short report line.",
        'Set <code>points</code> to the number of points (as an integer), <code>percent</code> to <code>points</code> as a percentage of <code>out_of</code>, rounded to 1 decimal place, and <code>report</code> to an f-string such as <code>"Ife scored 63.3%"</code> using the student\'s name and the percent.',
        f'student = "{nm}"\npoints_text = "{pts}"\nout_of = {out}\n\npoints = 0\npercent = 0\nreport = ""',
        {'points': pts, 'percent': pct, 'report': f"{nm} scored {pct}%"},
        'Convert with <code>int()</code>, use <code>round(points / out_of * 100, 1)</code>, and build the text with <code>f"{student} scored {percent}%"</code>.')


C_POOL = [C_arith, C_divmod, C_string, C_list, C_convert, C_dict, C_bool]
H_POOL = [H_arith, H_string, H_list, H_dict, H_cond, H_mix]

LEVELS = [
    {'id': 1, 'name': 'Level 1', 'difficulty': 'Beginner', 'count': 10, 'type': 'mcq', 'pool': T_POOL},
    {'id': 2, 'name': 'Level 2', 'difficulty': 'Basic', 'count': 10, 'type': 'mcq', 'pool': T_POOL_2},
    {'id': 3, 'name': 'Level 3', 'difficulty': 'Intermediate', 'count': 10, 'type': 'mcq', 'pool': T_POOL_3},
    {'id': 4, 'name': 'Level 4', 'difficulty': 'Advanced', 'count': 10, 'type': 'code', 'pool': C_POOL},
    {'id': 5, 'name': 'Level 5', 'difficulty': 'Expert', 'count': 10, 'type': 'code', 'pool': H_POOL},
]
PASS_RATIO = 0.75


def level_by_id(level_id):
    return next((l for l in LEVELS if l['id'] == level_id), None)


def generate_level_questions(level):
    return [pick(level['pool'])() for _ in range(level['count'])]


def public_question(q):
    """Strip answer-revealing fields before sending a question to the client."""
    if q.get('kind') == 'code':
        return {'topic': q['topic'], 'kind': 'code', 'q': q['q'], 'starter': q['starter']}
    return {'topic': q['topic'], 'q': q['q'], 'code': q.get('code'), 'options': q['options']}
