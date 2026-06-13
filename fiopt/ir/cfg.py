"""Control Flow Graph construction from Python AST.

The CFG builder walks the AST and creates basic blocks connected by
control flow edges. It handles:
- Sequential code
- if/elif/else branches
- for/while loops (with break/continue)
- try/except/finally
- with statements
- comprehensions
- return/raise/yield
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field

from fiopt.ir.basic_block import BasicBlock, BlockType
from fiopt.ir.ir_nodes import IRNode, IROpcode, LoopType


@dataclass
class LoopInfo:
    """Tracks information about a loop during CFG construction."""
    header_block_id: int
    exit_block_id: int
    loop_type: LoopType
    lineno: int
    loop_var: str = ""
    iterable_name: str = ""
    depth: int = 1


@dataclass
class CFG:
    """Control Flow Graph for a function or module.

    The CFG is a directed graph where:
    - Nodes are BasicBlocks (sequences of instructions with no internal branches)
    - Edges represent possible control flow transitions
    - The entry block is always block 0
    - There may be multiple exit blocks (returns, raises)
    """
    name: str  # function name or "<module>"
    blocks: dict[int, BasicBlock] = field(default_factory=dict)
    entry_block_id: int = 0
    exit_block_ids: list[int] = field(default_factory=list)
    loops: list[LoopInfo] = field(default_factory=list)

    @property
    def entry_block(self) -> BasicBlock:
        return self.blocks[self.entry_block_id]

    @property
    def block_count(self) -> int:
        return len(self.blocks)

    @property
    def edge_count(self) -> int:
        return sum(len(b.successors) for b in self.blocks.values())

    @property
    def max_loop_depth(self) -> int:
        """Maximum loop nesting depth in this CFG."""
        if not self.blocks:
            return 0
        return max(b.loop_depth for b in self.blocks.values())

    def get_loop_headers(self) -> list[BasicBlock]:
        """Get all loop header blocks."""
        return [b for b in self.blocks.values() if b.is_loop_header]

    def get_back_edges(self) -> list[tuple[int, int]]:
        """Find back edges (edges from a block to a dominating block).

        Back edges indicate loops in the CFG.
        """
        back_edges = []
        visited: set[int] = set()
        on_stack: set[int] = set()

        def _dfs(block_id: int) -> None:
            visited.add(block_id)
            on_stack.add(block_id)
            block = self.blocks.get(block_id)
            if block:
                for succ_id in block.successors:
                    if succ_id in on_stack:
                        back_edges.append((block_id, succ_id))
                    elif succ_id not in visited:
                        _dfs(succ_id)
            on_stack.discard(block_id)

        _dfs(self.entry_block_id)
        return back_edges

    def to_dot(self) -> str:
        """Export CFG to Graphviz DOT format for visualization."""
        lines = [f'digraph "{self.name}" {{']
        lines.append('  node [shape=box, style=filled, fontname="Courier"];')
        lines.append('  rankdir=TB;')

        for block in self.blocks.values():
            # Color based on block type
            color = {
                BlockType.ENTRY: "#90EE90",       # light green
                BlockType.EXIT: "#FFB6C1",        # light pink
                BlockType.LOOP_HEADER: "#87CEEB",  # light blue
                BlockType.LOOP_BODY: "#B0E0E6",   # powder blue
                BlockType.BRANCH_TRUE: "#FFFACD",  # lemon
                BlockType.BRANCH_FALSE: "#FFA07A", # light salmon
                BlockType.EXCEPT_HANDLER: "#DDA0DD", # plum
            }.get(block.block_type, "#FFFFFF")

            # Build label with instructions
            insts = "\\n".join(
                f"L{i.lineno}: {i.opcode.name}"
                + (f" {i.call_target}" if i.call_target else "")
                + (f" {i.loop_type.value}" if i.loop_type else "")
                for i in block.instructions[:8]  # limit to 8 for readability
            )
            if len(block.instructions) > 8:
                insts += f"\\n... +{len(block.instructions) - 8} more"

            label = f"{block.label}\\n(depth={block.loop_depth})\\n{insts}" if insts else block.label
            lines.append(
                f'  {block.id} [label="{label}", fillcolor="{color}"];'
            )

            for succ_id in block.successors:
                lines.append(f"  {block.id} -> {succ_id};")

        lines.append("}")
        return "\n".join(lines)


def _get_name(node: ast.expr) -> str:
    """Extract a readable name from an AST expression."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        val = _get_name(node.value)
        return f"{val}.{node.attr}" if val else node.attr
    if isinstance(node, ast.Call):
        return _get_name(node.func) + "()"
    if isinstance(node, ast.Subscript):
        return _get_name(node.value) + "[...]"
    if isinstance(node, ast.Constant):
        return repr(node.value)
    return "<expr>"


def _get_names_read(node: ast.AST) -> list[str]:
    """Extract variable names read in an expression (non-recursive into sub-statements)."""
    names = []
    for child in ast.walk(node):
        if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
            names.append(child.id)
    return names


def _get_names_written(node: ast.AST) -> list[str]:
    """Extract variable names written to in a statement."""
    names = []
    if isinstance(node, ast.Assign):
        for target in node.targets:
            for child in ast.walk(target):
                if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store):
                    names.append(child.id)
    elif isinstance(node, ast.AugAssign):
        if isinstance(node.target, ast.Name):
            names.append(node.target.id)
    elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        names.append(node.target.id)
    elif isinstance(node, ast.For):
        for child in ast.walk(node.target):
            if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store):
                names.append(child.id)
    return names


def _get_call_name(node: ast.Call) -> str:
    """Extract function name from a Call node."""
    return _get_name(node.func).rstrip("()")


class CFGBuilder:
    """Builds a Control Flow Graph from a Python AST function body."""

    def __init__(self, name: str = "<module>") -> None:
        self.name = name
        self._blocks: dict[int, BasicBlock] = {}
        self._next_id = 0
        self._current_block: BasicBlock | None = None
        self._loop_stack: list[LoopInfo] = []
        self._loops: list[LoopInfo] = []
        self._exit_blocks: list[int] = []

    def _new_block(
        self, label: str, block_type: BlockType = BlockType.NORMAL
    ) -> BasicBlock:
        """Create a new basic block."""
        block = BasicBlock(
            id=self._next_id,
            label=label,
            block_type=block_type,
            loop_depth=len(self._loop_stack),
        )
        if self._loop_stack:
            block.loop_header_id = self._loop_stack[-1].header_block_id
        self._blocks[block.id] = block
        self._next_id += 1
        return block

    def _link(self, from_block: BasicBlock, to_block: BasicBlock) -> None:
        """Create an edge from from_block to to_block."""
        from_block.add_successor(to_block.id)
        to_block.add_predecessor(from_block.id)

    def _set_current(self, block: BasicBlock) -> None:
        """Set the current block we're adding instructions to."""
        self._current_block = block

    def _emit(self, node: IRNode) -> None:
        """Add an instruction to the current block."""
        if self._current_block:
            self._current_block.add_instruction(node)

    def build(self, func_node: ast.FunctionDef | ast.AsyncFunctionDef | ast.Module) -> CFG:
        """Build a CFG from a function or module AST node.

        Args:
            func_node: The AST node to build the CFG from.

        Returns:
            A CFG object representing the control flow.
        """
        entry = self._new_block("ENTRY", BlockType.ENTRY)
        self._set_current(entry)

        body = func_node.body
        exit_block = self._new_block("EXIT", BlockType.EXIT)

        self._process_body(body, exit_block)

        # Link current block to exit if it hasn't been terminated
        if self._current_block and self._current_block.id != exit_block.id:
            self._link(self._current_block, exit_block)

        self._exit_blocks.append(exit_block.id)

        return CFG(
            name=self.name,
            blocks=self._blocks,
            entry_block_id=entry.id,
            exit_block_ids=self._exit_blocks,
            loops=self._loops,
        )

    def _process_body(
        self, stmts: list[ast.stmt], exit_block: BasicBlock
    ) -> None:
        """Process a list of statements, creating blocks and edges."""
        for stmt in stmts:
            if self._current_block is None:
                # Dead code after return/break/continue
                break
            self._process_stmt(stmt, exit_block)

    def _process_stmt(self, stmt: ast.stmt, exit_block: BasicBlock) -> None:
        """Process a single statement."""
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self._process_funcdef(stmt)
        elif isinstance(stmt, ast.ClassDef):
            self._process_classdef(stmt)
        elif isinstance(stmt, ast.Return):
            self._process_return(stmt, exit_block)
        elif isinstance(stmt, ast.If):
            self._process_if(stmt, exit_block)
        elif isinstance(stmt, ast.For):
            self._process_for(stmt, exit_block)
        elif isinstance(stmt, ast.While):
            self._process_while(stmt, exit_block)
        elif isinstance(stmt, ast.Try):
            self._process_try(stmt, exit_block)
        elif isinstance(stmt, (ast.With, ast.AsyncWith)):
            self._process_with(stmt, exit_block)
        elif isinstance(stmt, ast.Break):
            self._process_break(stmt)
        elif isinstance(stmt, ast.Continue):
            self._process_continue(stmt)
        elif isinstance(stmt, ast.Raise):
            self._process_raise(stmt, exit_block)
        elif isinstance(stmt, ast.Assert):
            self._process_assert(stmt)
        elif isinstance(stmt, ast.Pass):
            self._emit(IRNode(opcode=IROpcode.PASS, lineno=stmt.lineno))
        elif isinstance(stmt, ast.Expr):
            self._process_expr_stmt(stmt)
        elif isinstance(stmt, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
            self._process_assignment(stmt)
        elif isinstance(stmt, ast.Delete):
            self._emit(IRNode(
                opcode=IROpcode.STORE, lineno=stmt.lineno, label="del"
            ))
        elif isinstance(stmt, ast.Global):
            pass  # No IR needed
        elif isinstance(stmt, ast.Nonlocal):
            pass  # No IR needed
        elif isinstance(stmt, ast.Match):
            self._process_match(stmt, exit_block)
        else:
            # Fallback for any unhandled statement
            self._emit(IRNode(opcode=IROpcode.NOP, lineno=getattr(stmt, 'lineno', 0)))

    def _process_funcdef(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """Process a nested function definition (just record it as a store)."""
        self._emit(IRNode(
            opcode=IROpcode.STORE,
            lineno=node.lineno,
            writes=[node.name],
            label=f"def {node.name}",
        ))

    def _process_classdef(self, node: ast.ClassDef) -> None:
        """Process a class definition."""
        self._emit(IRNode(
            opcode=IROpcode.STORE,
            lineno=node.lineno,
            writes=[node.name],
            label=f"class {node.name}",
        ))

    def _process_return(self, node: ast.Return, exit_block: BasicBlock) -> None:
        """Process a return statement — links to exit block."""
        reads = _get_names_read(node.value) if node.value else []
        self._emit(IRNode(
            opcode=IROpcode.RETURN, lineno=node.lineno, reads=reads
        ))
        if self._current_block:
            self._link(self._current_block, exit_block)
            self._exit_blocks.append(self._current_block.id)
        self._current_block = None  # dead code after return

    def _process_if(self, node: ast.If, exit_block: BasicBlock) -> None:
        """Process if/elif/else chains."""
        merge_block = self._new_block(f"if_merge_L{node.lineno}", BlockType.NORMAL)

        # Condition
        cond_reads = _get_names_read(node.test)
        self._emit(IRNode(
            opcode=IROpcode.BRANCH, lineno=node.lineno,
            reads=cond_reads, label=f"if L{node.lineno}",
        ))

        # True branch
        true_block = self._new_block(f"if_true_L{node.lineno}", BlockType.BRANCH_TRUE)
        if self._current_block:
            self._link(self._current_block, true_block)
        self._set_current(true_block)
        self._process_body(node.body, exit_block)
        if self._current_block:
            self._link(self._current_block, merge_block)

        # False branch (else/elif)
        if node.orelse:
            false_block = self._new_block(f"if_false_L{node.lineno}", BlockType.BRANCH_FALSE)
            # Link from the block that had the BRANCH instruction
            branch_block = self._blocks.get(true_block.id - 1) or true_block
            # Find the block with the BRANCH
            for bid in sorted(self._blocks.keys(), reverse=True):
                b = self._blocks[bid]
                if b.instructions and b.instructions[-1].opcode == IROpcode.BRANCH:
                    self._link(b, false_block)
                    break
            else:
                if true_block.predecessors:
                    pred = self._blocks[true_block.predecessors[0]]
                    self._link(pred, false_block)

            self._set_current(false_block)
            self._process_body(node.orelse, exit_block)
            if self._current_block:
                self._link(self._current_block, merge_block)
        else:
            # No else: link condition block directly to merge
            for bid in sorted(self._blocks.keys(), reverse=True):
                b = self._blocks[bid]
                if b.instructions and b.instructions[-1].opcode == IROpcode.BRANCH:
                    self._link(b, merge_block)
                    break

        self._set_current(merge_block)

    def _process_for(self, node: ast.For, exit_block: BasicBlock) -> None:
        """Process a for loop."""
        loop_var = ""
        if isinstance(node.target, ast.Name):
            loop_var = node.target.id
        elif isinstance(node.target, ast.Tuple):
            loop_var = ", ".join(
                n.id for n in node.target.elts if isinstance(n, ast.Name)
            )

        iterable_name = _get_name(node.iter)

        # Header block (loop condition / iteration)
        header = self._new_block(f"for_header_L{node.lineno}", BlockType.LOOP_HEADER)
        if self._current_block:
            self._link(self._current_block, header)

        # Loop exit block
        loop_exit = self._new_block(f"for_exit_L{node.lineno}", BlockType.LOOP_EXIT)

        # Create loop info
        loop_info = LoopInfo(
            header_block_id=header.id,
            exit_block_id=loop_exit.id,
            loop_type=LoopType.FOR,
            lineno=node.lineno,
            loop_var=loop_var,
            iterable_name=iterable_name,
            depth=len(self._loop_stack) + 1,
        )
        self._loop_stack.append(loop_info)
        self._loops.append(loop_info)

        # Header instruction
        self._set_current(header)
        self._emit(IRNode(
            opcode=IROpcode.LOOP_HEADER,
            lineno=node.lineno,
            writes=_get_names_written(node),
            reads=_get_names_read(node.iter),
            loop_type=LoopType.FOR,
            loop_var=loop_var,
            loop_iterable=iterable_name,
            label=f"for {loop_var} in {iterable_name}",
        ))
        self._link(header, loop_exit)  # loop can exit

        # Body
        body_block = self._new_block(f"for_body_L{node.lineno}", BlockType.LOOP_BODY)
        body_block.loop_depth = len(self._loop_stack)
        body_block.loop_header_id = header.id
        self._link(header, body_block)
        self._set_current(body_block)
        self._process_body(node.body, exit_block)

        # Back edge
        if self._current_block:
            self._link(self._current_block, header)

        # Else clause
        if node.orelse:
            else_block = self._new_block(f"for_else_L{node.lineno}")
            self._link(header, else_block)
            self._set_current(else_block)
            self._process_body(node.orelse, exit_block)
            if self._current_block:
                self._link(self._current_block, loop_exit)

        self._loop_stack.pop()
        self._set_current(loop_exit)

    def _process_while(self, node: ast.While, exit_block: BasicBlock) -> None:
        """Process a while loop."""
        header = self._new_block(f"while_header_L{node.lineno}", BlockType.LOOP_HEADER)
        if self._current_block:
            self._link(self._current_block, header)

        loop_exit = self._new_block(f"while_exit_L{node.lineno}", BlockType.LOOP_EXIT)

        loop_info = LoopInfo(
            header_block_id=header.id,
            exit_block_id=loop_exit.id,
            loop_type=LoopType.WHILE,
            lineno=node.lineno,
            depth=len(self._loop_stack) + 1,
        )
        self._loop_stack.append(loop_info)
        self._loops.append(loop_info)

        self._set_current(header)
        self._emit(IRNode(
            opcode=IROpcode.LOOP_HEADER,
            lineno=node.lineno,
            reads=_get_names_read(node.test),
            loop_type=LoopType.WHILE,
            label=f"while L{node.lineno}",
        ))
        self._link(header, loop_exit)

        body_block = self._new_block(f"while_body_L{node.lineno}", BlockType.LOOP_BODY)
        body_block.loop_depth = len(self._loop_stack)
        body_block.loop_header_id = header.id
        self._link(header, body_block)
        self._set_current(body_block)
        self._process_body(node.body, exit_block)

        if self._current_block:
            self._link(self._current_block, header)

        if node.orelse:
            else_block = self._new_block(f"while_else_L{node.lineno}")
            self._link(header, else_block)
            self._set_current(else_block)
            self._process_body(node.orelse, exit_block)
            if self._current_block:
                self._link(self._current_block, loop_exit)

        self._loop_stack.pop()
        self._set_current(loop_exit)

    def _process_break(self, node: ast.Break) -> None:
        """Process a break statement — jump to loop exit."""
        self._emit(IRNode(opcode=IROpcode.LOOP_BREAK, lineno=node.lineno))
        if self._loop_stack and self._current_block:
            exit_block = self._blocks[self._loop_stack[-1].exit_block_id]
            self._link(self._current_block, exit_block)
        self._current_block = None

    def _process_continue(self, node: ast.Continue) -> None:
        """Process a continue statement — jump back to loop header."""
        self._emit(IRNode(opcode=IROpcode.LOOP_CONTINUE, lineno=node.lineno))
        if self._loop_stack and self._current_block:
            header_block = self._blocks[self._loop_stack[-1].header_block_id]
            self._link(self._current_block, header_block)
        self._current_block = None

    def _process_try(self, node: ast.Try, exit_block: BasicBlock) -> None:
        """Process try/except/finally."""
        merge_block = self._new_block(f"try_merge_L{node.lineno}")

        # Try body
        self._emit(IRNode(opcode=IROpcode.TRY_ENTER, lineno=node.lineno))
        self._process_body(node.body, exit_block)
        if self._current_block:
            self._link(self._current_block, merge_block)

        # Except handlers
        for handler in node.handlers:
            handler_block = self._new_block(
                f"except_L{handler.lineno}", BlockType.EXCEPT_HANDLER
            )
            # Any block in the try body can jump to the handler
            self._set_current(handler_block)
            self._emit(IRNode(
                opcode=IROpcode.EXCEPT,
                lineno=handler.lineno,
                label=f"except {handler.type and _get_name(handler.type) or ''}",
            ))
            self._process_body(handler.body, exit_block)
            if self._current_block:
                self._link(self._current_block, merge_block)

        # Else
        if node.orelse:
            else_block = self._new_block(f"try_else_L{node.lineno}")
            self._set_current(else_block)
            self._process_body(node.orelse, exit_block)
            if self._current_block:
                self._link(self._current_block, merge_block)

        # Finally
        if node.finalbody:
            finally_block = self._new_block(
                f"finally_L{node.lineno}", BlockType.FINALLY_BLOCK
            )
            self._link(merge_block, finally_block)
            self._set_current(finally_block)
            self._emit(IRNode(opcode=IROpcode.FINALLY, lineno=node.lineno))
            self._process_body(node.finalbody, exit_block)
            merge_block = self._new_block(f"try_end_L{node.lineno}")
            if self._current_block:
                self._link(self._current_block, merge_block)

        self._set_current(merge_block)

    def _process_with(self, node: ast.With | ast.AsyncWith, exit_block: BasicBlock) -> None:
        """Process a with statement."""
        for item in node.items:
            self._emit(IRNode(
                opcode=IROpcode.WITH_ENTER,
                lineno=node.lineno,
                reads=_get_names_read(item.context_expr),
                writes=_get_names_written(item) if item.optional_vars else [],
                label="with",
            ))

        self._process_body(node.body, exit_block)

        self._emit(IRNode(opcode=IROpcode.WITH_EXIT, lineno=node.lineno))

    def _process_raise(self, node: ast.Raise, exit_block: BasicBlock) -> None:
        """Process a raise statement."""
        reads = _get_names_read(node.exc) if node.exc else []
        self._emit(IRNode(
            opcode=IROpcode.RAISE, lineno=node.lineno, reads=reads
        ))
        if self._current_block:
            self._link(self._current_block, exit_block)
        self._current_block = None

    def _process_assert(self, node: ast.Assert) -> None:
        """Process an assert statement."""
        self._emit(IRNode(
            opcode=IROpcode.ASSERT,
            lineno=node.lineno,
            reads=_get_names_read(node.test),
        ))

    def _process_expr_stmt(self, node: ast.Expr) -> None:
        """Process an expression statement (usually a function call)."""
        if isinstance(node.value, ast.Call):
            call_name = _get_call_name(node.value)
            self._emit(IRNode(
                opcode=IROpcode.CALL,
                lineno=node.lineno,
                reads=_get_names_read(node.value),
                call_target=call_name,
                call_args=len(node.value.args) + len(node.value.keywords),
                label=f"call {call_name}",
            ))
        elif isinstance(node.value, (ast.Yield, ast.YieldFrom)):
            self._emit(IRNode(
                opcode=IROpcode.YIELD,
                lineno=node.lineno,
                reads=_get_names_read(node.value) if isinstance(node.value, ast.Yield) and node.value.value else [],
            ))
        elif isinstance(node.value, ast.Await):
            self._emit(IRNode(
                opcode=IROpcode.AWAIT,
                lineno=node.lineno,
                reads=_get_names_read(node.value.value),
            ))
        else:
            # Other expressions (e.g., standalone name, constant)
            self._emit(IRNode(
                opcode=IROpcode.NOP, lineno=node.lineno,
                reads=_get_names_read(node.value),
            ))

    def _process_assignment(
        self, node: ast.Assign | ast.AugAssign | ast.AnnAssign
    ) -> None:
        """Process an assignment statement."""
        writes = _get_names_written(node)
        reads = []

        if isinstance(node, ast.Assign):
            reads = _get_names_read(node.value)
            # Check if the value contains a call
            for child in ast.walk(node.value):
                if isinstance(child, ast.Call):
                    call_name = _get_call_name(child)
                    self._emit(IRNode(
                        opcode=IROpcode.CALL,
                        lineno=node.lineno,
                        reads=_get_names_read(child),
                        writes=writes,
                        call_target=call_name,
                        call_args=len(child.args) + len(child.keywords),
                        label=f"{', '.join(writes)} = {call_name}(...)",
                    ))
                    return
        elif isinstance(node, ast.AugAssign):
            reads = _get_names_read(node.value)
            if isinstance(node.target, ast.Name):
                reads.append(node.target.id)
        elif isinstance(node, ast.AnnAssign) and node.value:
            reads = _get_names_read(node.value)

        self._emit(IRNode(
            opcode=IROpcode.ASSIGN,
            lineno=node.lineno,
            reads=reads,
            writes=writes,
            label=f"assign {', '.join(writes)}" if writes else "assign",
        ))

    def _process_match(self, node: ast.Match, exit_block: BasicBlock) -> None:
        """Process a match statement (Python 3.10+)."""
        merge_block = self._new_block(f"match_merge_L{node.lineno}")
        reads = _get_names_read(node.subject)
        self._emit(IRNode(
            opcode=IROpcode.BRANCH,
            lineno=node.lineno,
            reads=reads,
            label=f"match L{node.lineno}",
        ))

        pre_block = self._current_block
        for case in node.cases:
            case_block = self._new_block(
                f"case_L{case.pattern.lineno}", BlockType.BRANCH_TRUE
            )
            if pre_block:
                self._link(pre_block, case_block)
            self._set_current(case_block)
            self._process_body(case.body, exit_block)
            if self._current_block:
                self._link(self._current_block, merge_block)

        self._set_current(merge_block)


def build_cfg(
    node: ast.FunctionDef | ast.AsyncFunctionDef | ast.Module,
    name: str = "<module>",
) -> CFG:
    """Build a Control Flow Graph from an AST node.

    Args:
        node: Function definition or module AST node.
        name: Name for the CFG (usually the function name).

    Returns:
        CFG representing the control flow.
    """
    builder = CFGBuilder(name=name)
    return builder.build(node)
