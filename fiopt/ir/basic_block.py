"""Basic block representation for the Control Flow Graph."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto

from fiopt.ir.ir_nodes import IRNode


class BlockType(Enum):
    """Classification of a basic block."""
    ENTRY = auto()          # function entry point
    EXIT = auto()           # function exit point
    NORMAL = auto()         # regular code
    LOOP_HEADER = auto()    # loop entry/condition check
    LOOP_BODY = auto()      # loop body
    LOOP_EXIT = auto()      # post-loop code
    BRANCH_TRUE = auto()    # if-true branch
    BRANCH_FALSE = auto()   # if-false / else branch
    EXCEPT_HANDLER = auto() # exception handler
    FINALLY_BLOCK = auto()  # finally block


@dataclass
class BasicBlock:
    """A basic block — a sequence of instructions with no internal branches.

    A basic block has:
    - Exactly one entry point (the first instruction)
    - Exactly one exit point (the last instruction)
    - No internal branches or targets

    Control flow only enters at the top and leaves at the bottom.
    """
    id: int
    label: str
    block_type: BlockType
    instructions: list[IRNode] = field(default_factory=list)
    # Control flow edges
    successors: list[int] = field(default_factory=list)   # block IDs
    predecessors: list[int] = field(default_factory=list)  # block IDs
    # Loop information
    loop_depth: int = 0       # nesting depth (0 = not in a loop)
    loop_header_id: int = -1  # ID of the loop header this block belongs to
    # Source line range
    start_line: int = 0
    end_line: int = 0

    @property
    def is_loop_header(self) -> bool:
        return self.block_type == BlockType.LOOP_HEADER

    @property
    def is_empty(self) -> bool:
        return len(self.instructions) == 0

    @property
    def has_call(self) -> bool:
        """Check if this block contains any function calls."""
        from fiopt.ir.ir_nodes import IROpcode
        return any(inst.opcode == IROpcode.CALL for inst in self.instructions)

    @property
    def called_functions(self) -> list[str]:
        """Get names of functions called in this block."""
        from fiopt.ir.ir_nodes import IROpcode
        return [
            inst.call_target
            for inst in self.instructions
            if inst.opcode == IROpcode.CALL and inst.call_target
        ]

    def add_instruction(self, node: IRNode) -> None:
        """Add an instruction to this block."""
        self.instructions.append(node)
        if not self.start_line:
            self.start_line = node.lineno
        self.end_line = node.lineno

    def add_successor(self, block_id: int) -> None:
        """Add a successor edge."""
        if block_id not in self.successors:
            self.successors.append(block_id)

    def add_predecessor(self, block_id: int) -> None:
        """Add a predecessor edge."""
        if block_id not in self.predecessors:
            self.predecessors.append(block_id)

    def __repr__(self) -> str:
        return (
            f"Block({self.id}, {self.label}, {self.block_type.name}, "
            f"inst={len(self.instructions)}, succ={self.successors}, "
            f"depth={self.loop_depth})"
        )
