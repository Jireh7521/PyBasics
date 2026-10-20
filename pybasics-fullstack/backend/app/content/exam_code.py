"""Level 4-5 code-challenge generators -- ported from the original version's
JS generators (C_* / H_*). Each returns a dict with 'starter' (code shown to
the learner) and 'expected' (dict of variable name -> correct value), which
the sandbox.run_user_code() output is compared against after submission."""
import random


def randint(a, b):
    return random.randint(a, b)


def pick(seq):
    return random.choice(seq)


def cap(s):
    return s[:1].upper() + s[1:] if s else s


def py_bool(b):
    return "True" if b else "False"


def code_ins(story, task):
    return f"<h4>Instructions</h4><p>{story}</p><p><strong>Your Task:</strong> {task}</p>"


def code_item(topic, story, task, starter, expected, explain):
    return {"topic": topic, "kind": "code", "q": code_ins(story, task), "starter": starter,
            "expected": expected, "explain": explain}


def C_arith():
    n = randint(2, 5); sc = pick([1.5, 2.5, 0.5, 2]); mk = pick([0.75, 1.25, 1.5, 0.5])
    cs = n * sc + randint(2, 9); ms = n * mk + randint(3, 12)
    return code_item(
        "Arithmetic Operators",
        f"A robot needs to make cereal for {n} customers. Each person gets exactly <code>{sc}</code> scoops of cereal and <code>{mk}</code> cups of milk. The kitchen starts with <code>{cs}</code> scoops of cereal and <code>{ms}</code> cups of milk.",
        "Using the arithmetic operators <code>*</code> and <code>-</code>, set the four variables at the bottom to the total cereal and milk needed, and the amounts left after serving everyone.",
        f"customers = {n}\nscoops_each = {sc}\nmilk_each = {mk}\ncereal_stock = {cs}\nmilk_stock = {ms}\n\ncereal_needed = 0\nmilk_needed = 0\ncereal_left = 0\nmilk_left = 0",
        {"cereal_needed": n * sc, "milk_needed": n * mk, "cereal_left": cs - n * sc, "milk_left": ms - n * mk},
        "Multiply the per-person amount by the number of customers, then subtract that from the starting stock.")


def C_divmod():
    box = randint(4, 12); total = box * randint(3, 9) + randint(1, box - 1)
    return code_item(
        "Arithmetic Operators",
        f"A bakery has <code>{total}</code> cookies and packs them into boxes that each hold exactly <code>{box}</code> cookies.",
        "Use <code>//</code> to find how many boxes are completely full, and <code>%</code> to find how many cookies are left over.",
        f"cookies = {total}\nbox_size = {box}\n\nfull_boxes = 0\nleftover = 0",
        {"full_boxes": total // box, "leftover": total % box},
        "<code>//</code> gives the whole number of times one number fits into another; <code>%</code> gives what remains.")


def C_string():
    F = ["ada", "grace", "alan", "linus", "margaret", "dennis"]
    Z = ["lovelace", "hopper", "turing", "torvalds", "hamilton", "ritchie"]
    k = randint(0, 5); f = F[k]; last = pick(Z)
    return code_item(
        "Strings",
        "A school prints name badges. The first and last name arrive in lowercase.",
        'Set <code>full_name</code> to both names in Title Case with a space between them, <code>initials</code> to the two first letters in uppercase (like <code>"AL"</code>), and <code>name_length</code> to the number of characters in <code>full_name</code>.',
        f'first = "{f}"\nlast = "{last}"\n\nfull_name = ""\ninitials = ""\nname_length = 0',
        {"full_name": f"{cap(f)} {cap(last)}", "initials": (f[0] + last[0]).upper(), "name_length": len(f) + len(last) + 1},
        'Use <code>.title()</code>, join with <code>+</code> and a space, index with <code>[0]</code> plus <code>.upper()</code>, and <code>len()</code>.')


def C_list():
    s = [randint(50, 99) for _ in range(4)]; x = randint(50, 99); all_ = s + [x]
    return code_item(
        "Lists",
        "A teacher keeps quiz scores in a list. A late score has just been added to the list.",
        "Set <code>highest</code> to the best score, <code>total</code> to the sum of all scores, <code>count</code> to how many scores there are, and <code>average</code> to the total divided by the count (do not round).",
        f"scores = [{', '.join(map(str, s))}]\nscores.append({x})\n\nhighest = 0\ntotal = 0\ncount = 0\naverage = 0",
        {"highest": max(all_), "total": sum(all_), "count": len(all_), "average": sum(all_) / len(all_)},
        "Use <code>max()</code>, <code>sum()</code> and <code>len()</code>; the average is <code>total / count</code>.")


def C_convert():
    age = randint(18, 60); price = pick([9.5, 12.25, 19.5, 4.75])
    return code_item(
        "Type Conversion",
        "A form gives you numbers as text, so they cannot be used in maths until they are converted.",
        'Set <code>age_next_year</code> to the age plus one (use <code>int()</code>), <code>double_price</code> to twice the price (use <code>float()</code>), and <code>label</code> to <code>"Next year: "</code> followed by the age (use <code>str()</code>).',
        f'age_text = "{age}"\nprice_text = "{price}"\n\nage_next_year = 0\ndouble_price = 0\nlabel = ""',
        {"age_next_year": age + 1, "double_price": price * 2, "label": f"Next year: {age + 1}"},
        "Convert first with <code>int()</code> / <code>float()</code>, then do the maths; <code>str()</code> turns a number back into text so it can join with other text.")


def C_dict():
    a = randint(3, 12); b = randint(2, 9)
    return code_item(
        "Dictionaries",
        "A shop tracks its fruit stock in a dictionary.",
        'Set <code>apple_count</code> to the stock of apples, <code>total_fruit</code> to apples plus pears, <code>has_kiwi</code> to whether <code>"kiwi"</code> is a key in the dictionary, and <code>kiwi_count</code> to the kiwi stock, or <code>0</code> if there is none (use <code>.get()</code>).',
        f'stock = {{"apples": {a}, "pears": {b}}}\n\napple_count = 0\ntotal_fruit = 0\nhas_kiwi = False\nkiwi_count = 0',
        {"apple_count": a, "total_fruit": a + b, "has_kiwi": False, "kiwi_count": 0},
        'Look values up with <code>stock["apples"]</code>, test keys with <code>in</code>, and use <code>.get(key, 0)</code> for a safe lookup with a default.')


def C_bool():
    t = randint(-5, 32); rain = pick([True, False])
    return code_item(
        "Booleans & Logic",
        "A weather app decides what to tell the user each morning.",
        "Set <code>take_umbrella</code> to whether it is raining; <code>wear_coat</code> to <code>True</code> if the temperature is below <code>12</code> or it is raining; and <code>perfect_day</code> to <code>True</code> only when it is not raining and the temperature is from <code>20</code> to <code>28</code> (inclusive).",
        f"temperature = {t}\nis_raining = {py_bool(rain)}\n\ntake_umbrella = None\nwear_coat = None\nperfect_day = None",
        {"take_umbrella": rain, "wear_coat": (t < 12) or rain, "perfect_day": (not rain) and 20 <= t <= 28},
        "Combine comparisons with <code>and</code>, <code>or</code> and <code>not</code>.")


def H_arith():
    secs = randint(3700, 20000); base = pick([2.5, 3, 4]); km = randint(5, 30); rate = pick([0.5, 1.25, 1.5]); disc = pick([10, 20, 25])
    before = base + km * rate
    return code_item(
        "Arithmetic Operators",
        f"A taxi ride lasted <code>{secs}</code> seconds and covered <code>{km}</code> km. The fare is a base fee of <code>{base}</code> plus <code>{rate}</code> per km, and then a <code>{disc}</code>% discount is taken off.",
        "Set <code>hours</code> and <code>minutes</code> to the whole hours and the remaining whole minutes of the ride, <code>fare_before</code> to the fare before the discount, and <code>fare_after</code> to the fare after the discount.",
        f"seconds = {secs}\nkm = {km}\nbase_fee = {base}\nrate_per_km = {rate}\ndiscount_percent = {disc}\n\nhours = 0\nminutes = 0\nfare_before = 0\nfare_after = 0",
        {"hours": secs // 3600, "minutes": (secs % 3600) // 60, "fare_before": before, "fare_after": before * (1 - disc / 100)},
        "<code>//</code> and <code>%</code> split seconds into hours and minutes; the discounted fare is <code>fare_before * (1 - discount_percent / 100)</code>.")


def H_string():
    nm = pick(["Ada.Lovelace", "Grace.Hopper", "Alan.Turing", "Linus.Torvalds"])
    dom = pick(["Example.com", "School.org", "Mail.net", "Club.org"])
    clean = f"{nm}@{dom}".lower(); user, domain = clean.split("@")
    return code_item(
        "Strings",
        "A sign-up form receives messy email addresses with extra spaces and mixed capitals.",
        'Set <code>clean</code> to the email with surrounding spaces removed and all letters lowercase; <code>username</code> to the part before the <code>@</code>; <code>domain</code> to the part after it; <code>slug</code> to the username with every <code>"."</code> replaced by <code>"-"</code>; and <code>is_org</code> to whether the domain ends with <code>".org"</code>.',
        f'raw_email = "  {nm}@{dom}  "\n\nclean = ""\nusername = ""\ndomain = ""\nslug = ""\nis_org = False',
        {"clean": clean, "username": user, "domain": domain, "slug": user.replace(".", "-"), "is_org": domain.endswith(".org")},
        'Chain string methods: <code>.strip().lower()</code>, <code>.split("@")</code> with indexing, <code>.replace()</code> and <code>.endswith()</code>.')


def H_list():
    nums = [randint(1, 40) for _ in range(7)]
    if random.random() < 0.5:
        nums[randint(0, 6)] = 10
    top3 = sorted(nums)[-3:]
    return code_item(
        "Lists",
        "A game stores its recent scores in a list and needs a few summaries of it.",
        "Set <code>first_three</code> to the first three scores, <code>last_two</code> to the last two, <code>middle</code> to everything except the first and last score, <code>top_three_total</code> to the sum of the three largest scores, and <code>has_ten</code> to whether <code>10</code> is in the list.",
        f"nums = [{', '.join(map(str, nums))}]\n\nfirst_three = []\nlast_two = []\nmiddle = []\ntop_three_total = 0\nhas_ten = False",
        {"first_three": nums[:3], "last_two": nums[-2:], "middle": nums[1:-1], "top_three_total": sum(top3), "has_ten": 10 in nums},
        "Slices like <code>nums[:3]</code>, <code>nums[-2:]</code> and <code>nums[1:-1]</code>, plus <code>sorted()</code>, <code>sum()</code> and <code>in</code>.")


def H_dict():
    menu = {"tea": randint(2, 5), "cake": randint(4, 9), "juice": randint(3, 7)}
    keys = list(menu.keys()); order = [pick(keys), pick(keys), pick(keys)]
    order_lit = ", ".join('"' + o + '"' for o in order)
    starter = (f'prices = {{"tea": {menu["tea"]}, "cake": {menu["cake"]}, "juice": {menu["juice"]}}}\n'
               f'order = [{order_lit}]\n\nfirst_price = 0\norder_total = 0\npie_price = 0\npriciest = 0')
    return code_item(
        "Dictionaries",
        "A cafe stores its menu prices in a dictionary, and an order is a list of item names.",
        'Set <code>first_price</code> to the price of the first item in the order, <code>order_total</code> to the total price of all three items, <code>pie_price</code> to the price of <code>"pie"</code> or <code>0</code> if it is not on the menu, and <code>priciest</code> to the highest price on the menu.',
        starter,
        {"first_price": menu[order[0]], "order_total": sum(menu[o] for o in order), "pie_price": 0, "priciest": max(menu.values())},
        'Combine lookups such as <code>prices[order[0]]</code>, <code>.get("pie", 0)</code> and <code>max(prices.values())</code>.')


def H_cond():
    score = randint(30, 95); att = randint(60, 100)
    bonus = 5 if att >= 90 else 0; fin = score + bonus
    return code_item(
        "Conditional Expressions",
        "A course awards 5 bonus points for attendance of 90% or more, then assigns a grade.",
        'Using conditional expressions (<code>x if condition else y</code>), set <code>bonus</code> (5 or 0), <code>final_score</code> (score plus bonus), <code>grade</code> (<code>"A"</code> if final is 85 or more, otherwise <code>"B"</code> if 70 or more, otherwise <code>"C"</code>), and <code>passed</code> (<code>True</code> when final is at least 60 and attendance is at least 75).',
        f"score = {score}\nattendance = {att}\n\nbonus = 0\nfinal_score = 0\ngrade = \"\"\npassed = False",
        {"bonus": bonus, "final_score": fin, "grade": "A" if fin >= 85 else "B" if fin >= 70 else "C", "passed": fin >= 60 and att >= 75},
        'A conditional expression can be chained: <code>"A" if final_score >= 85 else "B" if final_score >= 70 else "C"</code>.')


def H_mix():
    nm = pick(["Ife", "Chidi", "Amara", "Tunde"]); out = pick([70, 80, 120, 150])
    while True:
        pts = randint(30, out - 5)
        if round(pts / out * 1000) % 10 != 0:
            break
    pct = round(pts / out * 100, 1)
    return code_item(
        "Type Conversion & Strings",
        "A results sheet stores a student's points as text. You need to turn it into a percentage and a short report line.",
        'Set <code>points</code> to the number of points (as an integer), <code>percent</code> to <code>points</code> as a percentage of <code>out_of</code>, rounded to 1 decimal place, and <code>report</code> to an f-string such as <code>"Ife scored 63.3%"</code> using the student\'s name and the percent.',
        f'student = "{nm}"\npoints_text = "{pts}"\nout_of = {out}\n\npoints = 0\npercent = 0\nreport = ""',
        {"points": pts, "percent": pct, "report": f"{nm} scored {pct}%"},
        'Convert with <code>int()</code>, use <code>round(points / out_of * 100, 1)</code>, and build the text with <code>f"{student} scored {percent}%"</code>.')


CODE_POOLS = {
    "C_arith": C_arith, "C_divmod": C_divmod, "C_string": C_string, "C_list": C_list,
    "C_convert": C_convert, "C_dict": C_dict, "C_bool": C_bool,
    "H_arith": H_arith, "H_string": H_string, "H_list": H_list, "H_dict": H_dict,
    "H_cond": H_cond, "H_mix": H_mix,
}
