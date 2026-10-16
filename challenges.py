"""
challenges.py  —  Debug Dojo Phase 3
=====================================
Single source of truth for ALL challenge data.

Structure
---------
CHALLENGES  : list of dicts — safe challenge descriptions and starter code.
HIDDEN_TESTS: dict keyed by challenge id — NEVER returned through any API.

Difficulty levels: "easy" | "medium" | "hard"
Concept tags     : loops | strings | lists | math | iteration | conditionals
"""

from typing import Any

CHALLENGES: list[dict[str, Any]] = [{'id': 'last_k_total',
  'title': 'Last K Total',
  'difficulty': 'easy',
  'tags': ['lists', 'loops', 'math'],
  'description': 'Write a function `last_k_total(marks, k)` that returns the sum of the last `k` '
                 'marks in the list.\n'
                 '\n'
                 'If `k` is larger than the number of marks, return the total of all marks '
                 'instead.\n'
                 '\n'
                 '**Example:** `last_k_total([10, 20, 30, 40], 2)` → `70`',
  'starter_code': 'def last_k_total(marks, k):\n'
                  '    """Return the sum of the last k marks.\n'
                  '\n'
                  '    If k exceeds the list length, sum all marks instead.\n'
                  '    """\n'
                  '    # Bug: this slices from the front instead of the back\n'
                  '    return sum(marks[:k])',
  'visible_tests': [{'label': 'Basic last 2',
                     'call': 'last_k_total([10, 20, 30, 40], 2)',
                     'expected': '70',
                     'args': ([10, 20, 30, 40], 2),
                     'expected_val': 70},
                    {'label': 'k equals length',
                     'call': 'last_k_total([5, 15, 25], 3)',
                     'expected': '45',
                     'args': ([5, 15, 25], 3),
                     'expected_val': 45},
                    {'label': 'k larger than list',
                     'call': 'last_k_total([8, 12], 5)',
                     'expected': '20',
                     'args': ([8, 12], 5),
                     'expected_val': 20}]},
 {'id': 'count_passes',
  'title': 'Count Passes',
  'difficulty': 'easy',
  'tags': ['loops', 'conditionals', 'iteration'],
  'description': 'Write a function `count_passes(marks)` that counts how many students **passed** '
                 '— a pass is a mark of **40 or above**.\n'
                 '\n'
                 '**Example:** `count_passes([35, 40, 55, 20, 60])` → `3`',
  'starter_code': 'def count_passes(marks):\n'
                  '    """Count marks that are 40 or above."""\n'
                  '    passes = 0\n'
                  '    for mark in marks:\n'
                  '        if mark > 40:   # ← Bug on this line\n'
                  '            passes += 1\n'
                  '    return passes',
  'visible_tests': [{'label': 'Mixed marks',
                     'call': 'count_passes([35, 40, 55, 20, 60])',
                     'expected': '3',
                     'args': ([35, 40, 55, 20, 60],),
                     'expected_val': 3},
                    {'label': 'All fail',
                     'call': 'count_passes([10, 20, 39])',
                     'expected': '0',
                     'args': ([10, 20, 39],),
                     'expected_val': 0},
                    {'label': 'All pass',
                     'call': 'count_passes([40, 70, 100])',
                     'expected': '3',
                     'args': ([40, 70, 100],),
                     'expected_val': 3}]},
 {'id': 'first_n_squares',
  'title': 'First N Squares',
  'difficulty': 'easy',
  'tags': ['loops', 'lists', 'math'],
  'description': 'Write a function `first_n_squares(n)` that returns a list containing the squares '
                 'of the numbers from **1 to n** (inclusive).\n'
                 '\n'
                 'Return an **empty list** when `n` is zero.\n'
                 '\n'
                 '**Example:** `first_n_squares(4)` → `[1, 4, 9, 16]`',
  'starter_code': 'def first_n_squares(n):\n'
                  '    """Return [1², 2², ..., n²]. Empty list when n is 0."""\n'
                  '    result = []\n'
                  '    for i in range(n):   # ← Bug: range is off by one\n'
                  '        result.append(i * i)\n'
                  '    return result',
  'visible_tests': [{'label': 'n = 4',
                     'call': 'first_n_squares(4)',
                     'expected': '[1, 4, 9, 16]',
                     'args': (4,),
                     'expected_val': [1, 4, 9, 16]},
                    {'label': 'n = 1',
                     'call': 'first_n_squares(1)',
                     'expected': '[1]',
                     'args': (1,),
                     'expected_val': [1]},
                    {'label': 'n = 0 (edge case)',
                     'call': 'first_n_squares(0)',
                     'expected': '[]',
                     'args': (0,),
                     'expected_val': []}]},
 {'id': 'middle_three',
  'title': 'Middle Three',
  'difficulty': 'medium',
  'tags': ['lists', 'math'],
  'description': 'Write a function `middle_three(items)` that returns the **middle three** '
                 'elements of an odd-length list.\n'
                 '\n'
                 'If the list has **fewer than three items**, return the entire list unchanged.\n'
                 '\n'
                 '**Example:** `middle_three([1, 2, 3, 4, 5])` → `[2, 3, 4]`',
  'starter_code': 'def middle_three(items):\n'
                  '    """Return the middle three items of an odd-length list.\n'
                  '\n'
                  '    Returns the whole list when it has fewer than three items.\n'
                  '    """\n'
                  '    if len(items) < 3:\n'
                  '        return items\n'
                  '    mid = len(items) // 2\n'
                  '    return items[mid - 1 : mid + 1]   # ← Bug: slice too narrow',
  'visible_tests': [{'label': '5-element list',
                     'call': 'middle_three([1, 2, 3, 4, 5])',
                     'expected': '[2, 3, 4]',
                     'args': ([1, 2, 3, 4, 5],),
                     'expected_val': [2, 3, 4]},
                    {'label': '7-element list',
                     'call': 'middle_three([10, 20, 30, 40, 50, 60, 70])',
                     'expected': '[30, 40, 50]',
                     'args': ([10, 20, 30, 40, 50, 60, 70],),
                     'expected_val': [30, 40, 50]},
                    {'label': 'Short list (2 items)',
                     'call': 'middle_three([7, 8])',
                     'expected': '[7, 8]',
                     'args': ([7, 8],),
                     'expected_val': [7, 8]}]},
 {'id': 'count_even_numbers',
  'title': 'Count Even Numbers',
  'difficulty': 'easy',
  'tags': ['loops', 'conditionals', 'math'],
  'description': 'Write a function `count_even_numbers(numbers)` that counts how many integers in '
                 'the list are even.\n'
                 '\n'
                 '**Example:** `count_even_numbers([1, 2, 3, 4, 6])` → `3`',
  'starter_code': 'def count_even_numbers(numbers):\n'
                  '    """Count how many integers in numbers are even."""\n'
                  '    count = 0\n'
                  '    for n in numbers:\n'
                  '        if n % 2 == 1:   # ← Bug: this checks for odd, not even\n'
                  '            count += 1\n'
                  '    return count',
  'visible_tests': [{'label': 'Mixed list',
                     'call': 'count_even_numbers([1, 2, 3, 4, 6])',
                     'expected': '3',
                     'args': ([1, 2, 3, 4, 6],),
                     'expected_val': 3},
                    {'label': 'No evens',
                     'call': 'count_even_numbers([1, 3, 7])',
                     'expected': '0',
                     'args': ([1, 3, 7],),
                     'expected_val': 0},
                    {'label': 'All even',
                     'call': 'count_even_numbers([2, 4, 8])',
                     'expected': '3',
                     'args': ([2, 4, 8],),
                     'expected_val': 3}]},
 {'id': 'find_max',
  'title': 'Find Max',
  'difficulty': 'medium',
  'tags': ['loops', 'iteration', 'conditionals'],
  'description': 'Write a function `find_max(numbers)` that returns the **largest integer** in a '
                 "non-empty list **without** using Python's built-in `max()`.\n"
                 '\n'
                 '**Precondition:** the list will always contain at least one element.\n'
                 '\n'
                 '**Example:** `find_max([3, 1, 4, 1, 5, 9])` → `9`',
  'starter_code': 'def find_max(numbers):\n'
                  '    """Return the largest integer in numbers.\n'
                  '\n'
                  '    Precondition: numbers is non-empty.\n'
                  '    Do NOT use the built-in max().\n'
                  '    """\n'
                  '    largest = 0   # ← Bug: starting at 0 fails for all-negative lists\n'
                  '    for n in numbers:\n'
                  '        if n > largest:\n'
                  '            largest = n\n'
                  '    return largest',
  'visible_tests': [{'label': 'General list',
                     'call': 'find_max([3, 1, 4, 1, 5, 9])',
                     'expected': '9',
                     'args': ([3, 1, 4, 1, 5, 9],),
                     'expected_val': 9},
                    {'label': 'All negative',
                     'call': 'find_max([-5, -1, -8])',
                     'expected': '-1',
                     'args': ([-5, -1, -8],),
                     'expected_val': -1},
                    {'label': 'Single element',
                     'call': 'find_max([42])',
                     'expected': '42',
                     'args': ([42],),
                     'expected_val': 42}]},
 {'id': 'reverse_string',
  'title': 'Reverse String',
  'difficulty': 'easy',
  'tags': ['strings', 'iteration'],
  'description': 'Write a function `reverse_string(text)` that returns the input string '
                 "**reversed**, without using Python's `[::-1]` slice or `reversed()`.\n"
                 '\n'
                 '**Example:** `reverse_string("hello")` → `"olleh"`',
  'starter_code': 'def reverse_string(text):\n'
                  '    """Return text reversed without using [::-1] or reversed()."""\n'
                  '    result = ""\n'
                  '    for ch in text:\n'
                  '        result = result + ch   # ← Bug: appends forward, should prepend\n'
                  '    return result',
  'visible_tests': [{'label': 'Simple word',
                     'call': 'reverse_string("hello")',
                     'expected': '"olleh"',
                     'args': ('hello',),
                     'expected_val': 'olleh'},
                    {'label': 'Single character',
                     'call': 'reverse_string("x")',
                     'expected': '"x"',
                     'args': ('x',),
                     'expected_val': 'x'},
                    {'label': 'Empty string',
                     'call': 'reverse_string("")',
                     'expected': '""',
                     'args': ('',),
                     'expected_val': ''}]},
 {'id': 'count_vowels',
  'title': 'Count Vowels',
  'difficulty': 'easy',
  'tags': ['strings', 'loops', 'conditionals'],
  'description': 'Write a function `count_vowels(text)` that counts the number of vowels (**a, e, '
                 'i, o, u**) in a string, regardless of letter case.\n'
                 '\n'
                 '**Example:** `count_vowels("Hello World")` → `3`',
  'starter_code': 'def count_vowels(text):\n'
                  '    """Count a, e, i, o, u (case-insensitive) in text."""\n'
                  '    count = 0\n'
                  '    vowels = "aeiou"\n'
                  '    for ch in text:\n'
                  '        if ch in vowels:   # ← Bug: misses uppercase vowels\n'
                  '            count += 1\n'
                  '    return count',
  'visible_tests': [{'label': 'Mixed case',
                     'call': 'count_vowels("Hello World")',
                     'expected': '3',
                     'args': ('Hello World',),
                     'expected_val': 3},
                    {'label': 'All caps',
                     'call': 'count_vowels("AEIOU")',
                     'expected': '5',
                     'args': ('AEIOU',),
                     'expected_val': 5},
                    {'label': 'No vowels',
                     'call': 'count_vowels("gym")',
                     'expected': '0',
                     'args': ('gym',),
                     'expected_val': 0}]},
 {'id': 'sum_positive_numbers',
  'title': 'Sum Positive Numbers',
  'difficulty': 'easy',
  'tags': ['loops', 'conditionals', 'math'],
  'description': 'Write a function `sum_positive_numbers(numbers)` that returns the sum of all '
                 'numbers in the list that are **strictly greater than zero**.\n'
                 '\n'
                 '**Example:** `sum_positive_numbers([-3, 0, 4, 7, -1])` → `11`',
  'starter_code': 'def sum_positive_numbers(numbers):\n'
                  '    """Return the sum of all numbers greater than zero."""\n'
                  '    total = 0\n'
                  '    for n in numbers:\n'
                  '        if n >= 0:   # ← Bug: should exclude zero\n'
                  '            total += n\n'
                  '    return total',
  'visible_tests': [{'label': 'Mixed list with zero',
                     'call': 'sum_positive_numbers([-3, 0, 4, 7, -1])',
                     'expected': '11',
                     'args': ([-3, 0, 4, 7, -1],),
                     'expected_val': 11},
                    {'label': 'All negative',
                     'call': 'sum_positive_numbers([-5, -2, -8])',
                     'expected': '0',
                     'args': ([-5, -2, -8],),
                     'expected_val': 0},
                    {'label': 'Only zeros',
                     'call': 'sum_positive_numbers([0, 0, 0])',
                     'expected': '0',
                     'args': ([0, 0, 0],),
                     'expected_val': 0}]},
 {'id': 'remove_duplicates',
  'title': 'Remove Duplicates',
  'difficulty': 'hard',
  'tags': ['lists', 'iteration', 'conditionals'],
  'description': 'Write a function `remove_duplicates(items)` that returns a new list with '
                 '**duplicates removed** while **preserving the original order** of first '
                 'appearances.\n'
                 '\n'
                 '**Example:** `remove_duplicates([3, 1, 3, 2, 1])` → `[3, 1, 2]`',
  'starter_code': 'def remove_duplicates(items):\n'
                  '    """Return items with duplicates removed, preserving order."""\n'
                  '    seen = []\n'
                  '    result = []\n'
                  '    for item in items:\n'
                  '        if item not in seen:\n'
                  '            seen.append(item)\n'
                  '            # Bug: forgets to add the item to result\n'
                  '    return result',
  'visible_tests': [{'label': 'Has duplicates',
                     'call': 'remove_duplicates([3, 1, 3, 2, 1])',
                     'expected': '[3, 1, 2]',
                     'args': ([3, 1, 3, 2, 1],),
                     'expected_val': [3, 1, 2]},
                    {'label': 'No duplicates',
                     'call': 'remove_duplicates([10, 20, 30])',
                     'expected': '[10, 20, 30]',
                     'args': ([10, 20, 30],),
                     'expected_val': [10, 20, 30]},
                    {'label': 'Empty list',
                     'call': 'remove_duplicates([])',
                     'expected': '[]',
                     'args': ([],),
                     'expected_val': []}]}]

HIDDEN_TESTS: dict[str, list[dict[str, Any]]] = {'last_k_total': [{'description': 'Last 1 of 4', 'args': ([10, 20, 30, 40], 1), 'expected': 40},
                  {'description': 'Last 3 of 6', 'args': ([1, 2, 3, 4, 5, 6], 3), 'expected': 15},
                  {'description': 'k == length exactly', 'args': ([7, 3, 5], 3), 'expected': 15},
                  {'description': 'k == 0 → zero', 'args': ([10, 20], 0), 'expected': 0},
                  {'description': 'All negatives, k = 2',
                   'args': ([-4, -3, -2, -1], 2),
                   'expected': -3}],
 'count_passes': [{'description': 'Exact boundary 40', 'args': ([40],), 'expected': 1},
                  {'description': 'Just below boundary', 'args': ([39],), 'expected': 0},
                  {'description': 'Empty list', 'args': ([],), 'expected': 0},
                  {'description': 'All same value 50', 'args': ([50, 50, 50],), 'expected': 3},
                  {'description': 'Large mixed list',
                   'args': ([0, 39, 40, 41, 100],),
                   'expected': 3}],
 'first_n_squares': [{'description': 'n = 5', 'args': (5,), 'expected': [1, 4, 9, 16, 25]},
                     {'description': 'n = 3', 'args': (3,), 'expected': [1, 4, 9]},
                     {'description': 'n = 2', 'args': (2,), 'expected': [1, 4]},
                     {'description': 'n = 6', 'args': (6,), 'expected': [1, 4, 9, 16, 25, 36]},
                     {'description': 'n = 10 (length check)',
                      'args': (10,),
                      'expected': [1, 4, 9, 16, 25, 36, 49, 64, 81, 100]}],
 'middle_three': [{'description': '9-element list',
                   'args': ([1, 2, 3, 4, 5, 6, 7, 8, 9],),
                   'expected': [4, 5, 6]},
                  {'description': 'Exactly 3 items',
                   'args': ([10, 20, 30],),
                   'expected': [10, 20, 30]},
                  {'description': 'Single element', 'args': ([99],), 'expected': [99]},
                  {'description': 'Empty list', 'args': ([],), 'expected': []},
                  {'description': '11-element list',
                   'args': ([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],),
                   'expected': [5, 6, 7]}],
 'count_even_numbers': [{'description': 'Contains zero', 'args': ([0, 1, 2],), 'expected': 2},
                        {'description': 'Negative even', 'args': ([-2, -3, 4],), 'expected': 2},
                        {'description': 'Empty list', 'args': ([],), 'expected': 0},
                        {'description': 'All odds', 'args': ([1, 3, 5, 7],), 'expected': 0},
                        {'description': 'Large range',
                         'args': ([0, 1, 2, 3, 4, 5, 6, 7, 8, 9],),
                         'expected': 5}],
 'find_max': [{'description': 'All same value', 'args': ([7, 7, 7],), 'expected': 7},
              {'description': 'All negatives', 'args': ([-10, -3, -50],), 'expected': -3},
              {'description': 'Mixed sign', 'args': ([-1, 0, 1],), 'expected': 1},
              {'description': 'Descending order', 'args': ([9, 7, 5, 3, 1],), 'expected': 9},
              {'description': 'Large random', 'args': ([42, 17, 99, 3, 55],), 'expected': 99}],
 'reverse_string': [{'description': 'Palindrome', 'args': ('racecar',), 'expected': 'racecar'},
                    {'description': 'With spaces', 'args': ('hi there',), 'expected': 'ereht ih'},
                    {'description': 'Numbers in string', 'args': ('abc123',), 'expected': '321cba'},
                    {'description': 'Two chars', 'args': ('ab',), 'expected': 'ba'},
                    {'description': 'Uppercase', 'args': ('PYTHON',), 'expected': 'NOHTYP'}],
 'count_vowels': [{'description': 'Only consonants', 'args': ('bcd',), 'expected': 0},
                  {'description': 'Empty string', 'args': ('',), 'expected': 0},
                  {'description': 'Mixed with numbers', 'args': ('h3ll0 w0rld',), 'expected': 0},
                  {'description': 'Sentence', 'args': ('The quick brown fox',), 'expected': 5},
                  {'description': 'Repeated vowel', 'args': ('aaaaaa',), 'expected': 6}],
 'sum_positive_numbers': [{'description': 'All positive', 'args': ([1, 2, 3],), 'expected': 6},
                          {'description': 'Contains floats',
                           'args': ([1.5, -0.5, 2.5],),
                           'expected': 4.0},
                          {'description': 'Empty list', 'args': ([],), 'expected': 0},
                          {'description': 'Zero only', 'args': ([0],), 'expected': 0},
                          {'description': 'Large mixed',
                           'args': ([-100, 50, 0, 25, -1],),
                           'expected': 75}],
 'remove_duplicates': [{'description': 'All duplicates', 'args': ([5, 5, 5],), 'expected': [5]},
                       {'description': 'Strings',
                        'args': (['a', 'b', 'a', 'c'],),
                        'expected': ['a', 'b', 'c']},
                       {'description': 'Single element', 'args': ([42],), 'expected': [42]},
                       {'description': 'Order preserved',
                        'args': ([4, 2, 4, 1, 2],),
                        'expected': [4, 2, 1]},
                       {'description': 'Mixed types',
                        'args': ([1, '1', 1, '1'],),
                        'expected': [1, '1']}]}

# Convenience: O(1) lookup by id
CHALLENGE_BY_ID: dict[str, dict[str, Any]] = {c["id"]: c for c in CHALLENGES}
