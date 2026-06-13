"""IR node types for the intermediate representation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto


class IROpcode(Enum):
    """Opcodes for IR instructions."""
    # Basic operations
    ASSIGN = auto()         # variable = expression
    LOAD = auto()           # load variable
    STORE = auto()          # store to variable
    CALL = auto()           # function call
    RETURN = auto()         # return from function

    # Control flow
    JUMP = auto()           # unconditional jump
    BRANCH = auto()         # conditional branch (if/elif)
    LOOP_HEADER = auto()    # loop entry point (for/while)
    LOOP_END = auto()       # loop exit point
    LOOP_CONTINUE = auto()  # continue statement
    LOOP_BREAK = auto()     # break statement

    # Exception handling
    TRY_ENTER = auto()
    TRY_EXIT = auto()
    EXCEPT = auto()
    FINALLY = auto()

    # Context management
    WITH_ENTER = auto()
    WITH_EXIT = auto()

    # Special
    YIELD = auto()
    AWAIT = auto()
    RAISE = auto()
    ASSERT = auto()
    PASS = auto()
    NOP = auto()            # no-operation (placeholder)


class LoopType(Enum):
    """Type of loop construct."""
    FOR = "for"
    WHILE = "while"
    COMPREHENSION_LIST = "listcomp"
    COMPREHENSION_SET = "setcomp"
    COMPREHENSION_DICT = "dictcomp"
    COMPREHENSION_GEN = "genexpr"


@dataclass
class IRNode:
    """A single instruction in the IR.

    Each node represents one logical operation and carries
    metadata about its source location and variable references.
    """
    opcode: IROpcode
    lineno: int
    # Variables read by this instruction
    reads: list[str] = field(default_factory=list)
    # Variables written by this instruction
    writes: list[str] = field(default_factory=list)
    # Additional metadata
    label: str = ""         # human-readable label
    target: str = ""        # jump/branch target label
    # For calls
    call_target: str = ""   # function being called
    call_args: int = 0      # number of arguments
    # For loops
    loop_type: LoopType | None = None
    loop_var: str = ""      # iteration variable
    loop_iterable: str = "" # what is being iterated over

    def __repr__(self) -> str:
        parts = [f"L{self.lineno}: {self.opcode.name}"]
        if self.label:
            parts.append(f"[{self.label}]")
        if self.writes:
            parts.append(f"writes={self.writes}")
        if self.reads:
            parts.append(f"reads={self.reads}")
        if self.call_target:
            parts.append(f"call={self.call_target}")
        if self.loop_type:
            parts.append(f"loop={self.loop_type.value}")
        return " ".join(parts)
