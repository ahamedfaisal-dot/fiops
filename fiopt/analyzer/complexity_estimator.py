"""Big-O complexity estimation engine.

Estimates time complexity for Python functions using:
- AST-based loop nesting analysis
- Recursion pattern detection
- Built-in function complexity knowledge
- Symbolic reasoning about iteration bounds
- Pattern matching for common algorithms

Supports: O(1), O(log n), O(n), O(n log n), O(n²), O(n³), O(nᵏ), O(2ⁿ), O(n!)
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field

from fiopt.config import ComplexityClass
from fiopt.analyzer.loop_detector import LoopAnalysis, LoopDetail, LoopKind, detect_loops
from fiopt.analyzer.recursion_detector import RecursionInfo, detect_recursion


# Functions known to have specific complexities
_KNOWN_COMPLEXITIES: dict[str, ComplexityClass] = {
    # O(n log n)
    "sorted": ComplexityClass.O_N_LOG_N,
    "list.sort": ComplexityClass.O_N_LOG_N,
    "sort": ComplexityClass.O_N_LOG_N,
    # O(n)
    "sum": ComplexityClass.O_N,
    "min": ComplexityClass.O_N,
    "max": ComplexityClass.O_N,
    "len": ComplexityClass.O_1,
    "any": ComplexityClass.O_N,
    "all": ComplexityClass.O_N,
    "enumerate": ComplexityClass.O_1,  # creates iterator, O(1)
    "zip": ComplexityClass.O_1,
    "map": ComplexityClass.O_1,        # lazy
    "filter": ComplexityClass.O_1,     # lazy
    "reversed": ComplexityClass.O_1,   # lazy
    "list": ComplexityClass.O_N,       # list() conversion
    "set": ComplexityClass.O_N,
    "dict": ComplexityClass.O_N,
    "tuple": ComplexityClass.O_N,
    "str.join": ComplexityClass.O_N,
    "join": ComplexityClass.O_N,
    # O(1)
    "dict.get": ComplexityClass.O_1,
    "set.add": ComplexityClass.O_1,
    "dict.setdefault": ComplexityClass.O_1,
    "list.append": ComplexityClass.O_1,
    "set.discard": ComplexityClass.O_1,
    "dict.pop": ComplexityClass.O_1,
    # O(n) — linear search
    "list.index": ComplexityClass.O_N,
    "list.count": ComplexityClass.O_N,
    "list.remove": ComplexityClass.O_N,
    "str.find": ComplexityClass.O_N,
    "str.replace": ComplexityClass.O_N,
    "str.split": ComplexityClass.O_N,
    "str.strip": ComplexityClass.O_N,
    # O(n) — copy
    "list.copy": ComplexityClass.O_N,
    "dict.copy": ComplexityClass.O_N,
    "copy.copy": ComplexityClass.O_N,
    "copy.deepcopy": ComplexityClass.O_N,
    # O(n) membership
    "list.__contains__": ComplexityClass.O_N,
    # O(1) membership
    "set.__contains__": ComplexityClass.O_1,
    "dict.__contains__": ComplexityClass.O_1,
}


@dataclass
class ComplexityExplanation:
    """Explanation for a complexity component."""
    source: str       # "loop", "recursion", "call", etc.
    complexity: ComplexityClass
    lineno: int
    description: str
    detail: str = ""  # longer explanation


@dataclass
class ComplexityResult:
    """Result of complexity estimation for a single function."""
    function_name: str
    lineno: int
    end_lineno: int
    # Estimated overall complexity
    estimated_complexity: ComplexityClass
    # Confidence: 0.0 (guess) to 1.0 (certain)
    confidence: float
    # Individual components that contribute to the complexity
    explanations: list[ComplexityExplanation] = field(default_factory=list)
    # Sub-analysis results
    loop_analysis: LoopAnalysis | None = None
    recursion_info: RecursionInfo | None = None
    # Bottleneck info
    bottleneck_lines: list[int] = field(default_factory=list)
    bottleneck_description: str = ""
    # Warnings
    warnings: list[str] = field(default_factory=list)

    @property
    def is_efficient(self) -> bool:
        return self.estimated_complexity <= ComplexityClass.O_N_LOG_N

    @property
    def summary(self) -> str:
        return (
            f"{self.function_name}: {self.estimated_complexity.value} "
            f"(confidence: {self.confidence:.0%})"
        )


def _combine_complexities(
    c1: ComplexityClass, c2: ComplexityClass, operation: str = "multiply"
) -> ComplexityClass:
    """Combine two complexity classes.

    For nested loops: multiply (O(n) * O(n) = O(n²))
    For sequential code: take the max (O(n) + O(n²) = O(n²))
    """
    if operation == "max":
        return max(c1, c2)

    # Multiply — used for nested loops.
    # Use polynomial degree (not rank) so that O(n) × O(n²) = O(n³).
    _degree: dict[ComplexityClass, float] = {
        ComplexityClass.O_1: 0,
        ComplexityClass.O_LOG_N: 0.5,
        ComplexityClass.O_N: 1,
        ComplexityClass.O_N_LOG_N: 1.5,
        ComplexityClass.O_N_SQUARED: 2,
        ComplexityClass.O_N_CUBED: 3,
        ComplexityClass.O_N_K: 4,
        ComplexityClass.O_2_N: 100,       # sentinel — exponential
        ComplexityClass.O_N_FACTORIAL: 200,
        ComplexityClass.UNKNOWN: 0,
    }

    degree_sum = _degree.get(c1, 0) + _degree.get(c2, 0)

    if degree_sum <= 0:
        return ComplexityClass.O_1
    elif degree_sum <= 0.5:
        return ComplexityClass.O_LOG_N
    elif degree_sum <= 1:
        return ComplexityClass.O_N
    elif degree_sum <= 1.5:
        return ComplexityClass.O_N_LOG_N
    elif degree_sum <= 2:
        return ComplexityClass.O_N_SQUARED
    elif degree_sum <= 3:
        return ComplexityClass.O_N_CUBED
    elif degree_sum <= 4:
        return ComplexityClass.O_N_K
    elif degree_sum <= 100:
        return ComplexityClass.O_2_N
    else:
        return ComplexityClass.O_N_FACTORIAL


def _estimate_loop_iterations(loop: LoopDetail) -> ComplexityClass:
    """Estimate the iteration count complexity of a loop.

    Analyzes the loop's iterable to determine how many iterations it performs.
    """
    if not loop.variables:
        # While loop or unknown — assume O(n)
        return ComplexityClass.O_N

    iterable = loop.variables[0].iterable
    iterable_node = loop.variables[0].iterable_node

    # range(constant) — O(1) (fixed number of iterations)
    if iterable.startswith("range("):
        if iterable_node and isinstance(iterable_node, ast.Call):
            args = iterable_node.args
            if len(args) == 1 and isinstance(args[0], ast.Constant):
                # range(10) — constant iterations
                return ComplexityClass.O_1
            if len(args) == 1 and isinstance(args[0], ast.Name):
                # range(n) — O(n)
                return ComplexityClass.O_N
            if len(args) >= 2:
                # range(0, n) or range(0, n, 2) — O(n)
                return ComplexityClass.O_N
        return ComplexityClass.O_N

    # Iterating over a variable — O(n) (assume variable-sized)
    if isinstance(iterable_node, ast.Name):
        return ComplexityClass.O_N

    # Iterating over a method call result
    if isinstance(iterable_node, ast.Call):
        call_name = ""
        if isinstance(iterable_node.func, ast.Name):
            call_name = iterable_node.func.id
        elif isinstance(iterable_node.func, ast.Attribute):
            call_name = iterable_node.func.attr

        # dict.keys(), dict.values(), dict.items() — O(n)
        if call_name in ("keys", "values", "items"):
            return ComplexityClass.O_N
        # enumerate(), zip() — O(n)
        if call_name in ("enumerate", "zip"):
            return ComplexityClass.O_N

    # Default: assume O(n)
    return ComplexityClass.O_N


def _check_halving_pattern(node: ast.While) -> bool:
    """Check if a while loop has a halving pattern (binary search).

    Looks for patterns like:
    - low < high with mid = (low + high) // 2
    - n = n // 2
    - left, right pointers moving toward center
    """
    # Check for assignments in body that halve a variable
    for stmt in ast.walk(node):
        if isinstance(stmt, ast.AugAssign):
            if isinstance(stmt.op, ast.FloorDiv):
                if isinstance(stmt.value, ast.Constant) and stmt.value.value == 2:
                    return True
        elif isinstance(stmt, ast.Assign):
            if isinstance(stmt.value, ast.BinOp):
                if isinstance(stmt.value.op, ast.FloorDiv):
                    if isinstance(stmt.value.right, ast.Constant) and stmt.value.right.value == 2:
                        return True
                # mid = (low + high) // 2 pattern
                if isinstance(stmt.value.op, ast.FloorDiv):
                    return True
    return False


def _check_exponential_growth(node: ast.While) -> bool:
    """Check if a while loop doubles on each iteration (exponential)."""
    for stmt in ast.walk(node):
        if isinstance(stmt, ast.AugAssign):
            if isinstance(stmt.op, ast.Mult):
                if isinstance(stmt.value, ast.Constant) and stmt.value.value == 2:
                    return True
    return False


def _estimate_while_complexity(node: ast.While) -> ComplexityClass:
    """Estimate complexity of a while loop by analyzing its pattern."""
    if _check_halving_pattern(node):
        return ComplexityClass.O_LOG_N
    if _check_exponential_growth(node):
        return ComplexityClass.O_LOG_N  # log n iterations in the loop itself
    # Default while loop — assume O(n)
    return ComplexityClass.O_N


def _analyze_body_calls(
    body: list[ast.stmt],
) -> list[tuple[str, ComplexityClass, int]]:
    """Find function calls in a body and their known complexities.

    Returns list of (call_name, complexity, lineno).
    """
    results = []
    for stmt in body:
        for node in ast.walk(stmt):
            if isinstance(node, ast.Call):
                call_name = ""
                if isinstance(node.func, ast.Name):
                    call_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    call_name = node.func.attr
                    # Try full dotted name
                    if isinstance(node.func.value, ast.Name):
                        full_name = f"{node.func.value.id}.{node.func.attr}"
                        if full_name in _KNOWN_COMPLEXITIES:
                            call_name = full_name

                if call_name in _KNOWN_COMPLEXITIES:
                    results.append((
                        call_name,
                        _KNOWN_COMPLEXITIES[call_name],
                        node.lineno,
                    ))

            # Check for `in` operator on lists (O(n) membership check)
            if isinstance(node, ast.Compare):
                for op in node.ops:
                    if isinstance(op, (ast.In, ast.NotIn)):
                        # If comparing against a list literal or list variable, it's O(n)
                        for comparator in node.comparators:
                            if isinstance(comparator, ast.List):
                                results.append((
                                    "list.__contains__",
                                    ComplexityClass.O_N,
                                    node.lineno,
                                ))

    return results


def estimate_complexity(
    func_node: ast.FunctionDef | ast.AsyncFunctionDef,
    all_function_names: set[str] | None = None,
    all_functions: dict[str, ast.FunctionDef] | None = None,
) -> ComplexityResult:
    """Estimate the Big-O time complexity of a function.

    Uses a combination of:
    1. Loop nesting analysis — nested loops multiply complexity
    2. Recursion pattern detection — branching factor and depth
    3. Known function complexities — sorted(), .index(), etc.
    4. Special pattern detection — binary search, divide & conquer

    Args:
        func_node: The function AST node to analyze.
        all_function_names: Names of all functions (for recursion analysis).
        all_functions: Map of name->AST node (for mutual recursion).

    Returns:
        ComplexityResult with estimated complexity, explanations, and confidence.
    """
    result = ComplexityResult(
        function_name=func_node.name,
        lineno=func_node.lineno,
        end_lineno=func_node.end_lineno or func_node.lineno,
        estimated_complexity=ComplexityClass.O_1,
        confidence=1.0,
    )

    # Step 1: Loop analysis
    loop_analysis = detect_loops(func_node)
    result.loop_analysis = loop_analysis

    loop_complexity = _estimate_loops_complexity(loop_analysis, result)

    # Step 2: Recursion analysis
    recursion_info = detect_recursion(func_node, all_function_names, all_functions)
    result.recursion_info = recursion_info

    recursion_complexity = _estimate_recursion_complexity(recursion_info, result)

    # Step 3: Known function call analysis (in the body, not in loops)
    body_calls = _analyze_body_calls(func_node.body)
    call_complexity = ComplexityClass.O_1
    for call_name, complexity, lineno in body_calls:
        if complexity > call_complexity:
            call_complexity = complexity
            result.explanations.append(ComplexityExplanation(
                source="call",
                complexity=complexity,
                lineno=lineno,
                description=f"Call to '{call_name}' has {complexity.value} complexity",
            ))

    # Step 4: Combine complexities
    # Take the maximum of loop, recursion, and call complexities
    # (since they're in the same scope, not nested)
    overall = max(loop_complexity, recursion_complexity, call_complexity)
    result.estimated_complexity = overall

    # Adjust confidence based on analysis quality
    if loop_analysis.total_loops == 0 and not recursion_info.is_recursive:
        result.confidence = 0.95  # Simple function
    elif loop_analysis.max_depth <= 2 and not recursion_info.is_recursive:
        result.confidence = 0.85  # Moderate loops
    elif recursion_info.is_recursive and recursion_info.has_base_case:
        result.confidence = 0.70  # Recursive with base case detected
    elif recursion_info.is_recursive:
        result.confidence = 0.50  # Recursive without clear base case
    else:
        result.confidence = 0.75

    # Determine bottleneck
    if result.explanations:
        worst = max(result.explanations, key=lambda e: e.complexity.rank)
        result.bottleneck_lines = [worst.lineno]
        result.bottleneck_description = worst.description

    return result


def _estimate_loops_complexity(
    loop_analysis: LoopAnalysis,
    result: ComplexityResult,
) -> ComplexityClass:
    """Estimate complexity contribution from loops."""
    if loop_analysis.total_loops == 0:
        return ComplexityClass.O_1

    # Process top-level loops (depth == 1)
    top_level_loops = [l for l in loop_analysis.loops if l.depth == 1]
    max_complexity = ComplexityClass.O_1

    for loop in top_level_loops:
        loop_c = _estimate_single_loop_tree_complexity(loop, result)
        max_complexity = max(max_complexity, loop_c)

    return max_complexity


def _estimate_single_loop_tree_complexity(
    loop: LoopDetail,
    result: ComplexityResult,
) -> ComplexityClass:
    """Estimate complexity of a loop and its nested children."""
    # Base: this loop's iteration complexity
    if loop.kind == LoopKind.WHILE and loop.node:
        this_loop_c = _estimate_while_complexity(loop.node)
    else:
        this_loop_c = _estimate_loop_iterations(loop)

    result.explanations.append(ComplexityExplanation(
        source="loop",
        complexity=this_loop_c,
        lineno=loop.lineno,
        description=(
            f"{'Nested ' if loop.is_nested else ''}"
            f"{loop.kind.value} loop at line {loop.lineno} — {this_loop_c.value} iterations"
        ),
        detail=(
            f"Iterating over {loop.variables[0].iterable if loop.variables else 'unknown'}"
            + (f" (depth {loop.depth})" if loop.depth > 1 else "")
        ),
    ))

    # Check for expensive calls inside this loop
    if loop.node:
        body = []
        if isinstance(loop.node, (ast.For, ast.While)):
            body = loop.node.body
        if body:
            calls = _analyze_body_calls(body)
            for call_name, complexity, lineno in calls:
                if complexity > ComplexityClass.O_1:
                    # This call's complexity is multiplied by the loop iterations
                    combined = _combine_complexities(this_loop_c, complexity, "multiply")
                    result.explanations.append(ComplexityExplanation(
                        source="loop_call",
                        complexity=combined,
                        lineno=lineno,
                        description=(
                            f"'{call_name}' ({complexity.value}) called inside "
                            f"{this_loop_c.value} loop — total {combined.value}"
                        ),
                    ))
                    this_loop_c = max(this_loop_c, combined)

    # Recurse into children (nested loops multiply)
    if loop.children:
        max_child_c = ComplexityClass.O_1
        for child in loop.children:
            child_c = _estimate_single_loop_tree_complexity(child, result)
            max_child_c = max(max_child_c, child_c)

        # Nested loop: multiply this loop's iterations by the child's complexity
        if max_child_c > ComplexityClass.O_1:
            total = _combine_complexities(this_loop_c, max_child_c, "multiply")
            result.explanations.append(ComplexityExplanation(
                source="nested_loop",
                complexity=total,
                lineno=loop.lineno,
                description=(
                    f"Nested loops: {this_loop_c.value} × {max_child_c.value} = {total.value}"
                ),
            ))
            return total

    return this_loop_c


def _estimate_recursion_complexity(
    info: RecursionInfo,
    result: ComplexityResult,
) -> ComplexityClass:
    """Estimate complexity contribution from recursion."""
    if not info.is_recursive:
        return ComplexityClass.O_1

    branches = info.estimated_branches
    depth = info.depth_pattern

    complexity = ComplexityClass.O_N  # default for simple recursion

    if depth == "logarithmic":
        if branches <= 1:
            complexity = ComplexityClass.O_LOG_N
        else:
            complexity = ComplexityClass.O_N  # O(n) for 2 branches with log depth
    elif depth == "linear":
        if branches <= 1:
            complexity = ComplexityClass.O_N
        elif branches == 2:
            if info.has_overlapping_subproblems:
                complexity = ComplexityClass.O_2_N  # e.g., naive fibonacci
            else:
                complexity = ComplexityClass.O_N  # e.g., merge sort recursion
        else:
            complexity = ComplexityClass.O_2_N  # exponential branching
    elif depth == "exponential":
        complexity = ComplexityClass.O_2_N

    desc = f"Recursive function with {branches} branch(es), {depth} depth"
    if info.can_be_memoized:
        desc += " (memoizable)"
        result.warnings.append(
            f"Function '{info.function_name}' at line {info.lineno}: "
            f"{info.memoization_reason}"
        )

    if not info.has_base_case:
        desc += " [no base case detected]"
        result.warnings.append(
            f"Function '{info.function_name}' at line {info.lineno}: "
            f"No clear base case detected — possible infinite recursion."
        )

    result.explanations.append(ComplexityExplanation(
        source="recursion",
        complexity=complexity,
        lineno=info.lineno,
        description=desc,
        detail=info.memoization_reason if info.can_be_memoized else "",
    ))

    return complexity
