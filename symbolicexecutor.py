#!/usr/bin/python3

from language import Instruction, Variable, Cmp
from interpreter import ExecutionState, Interpreter
from z3 import *

class SymbolicExecutionState(ExecutionState):
    def __init__(self, pc):
        super().__init__(pc)

        # add constraints here

        # dont forget to create _copy_ of attributes
        # when forking states (i.e., dont use
        # new.attr = old.attr, that would
        # only create a reference)

    def copy(self):
        n = SymbolicExecutionState(self.pc)
        n.variables = self.variables.copy()
        n.values = self.values.copy()
        n.error = self.error
        return n

    def write(self, var, value):
        assert isinstance(var, Variable)
        assert isinstance(value, ExprRef)
        self.variables[var] = value

    def eval(self, v):
        if isinstance(v, bool):
            return BoolVal(v) # convert int to z3 BoolVal
        # NOTE: this must be before IntVal, since True/False
        # match also IntVal
        if isinstance(v, int):
            return IntVal(v) # convert int to z3 IntVal
        assert isinstance(v, Instruction)
        return self.values.get(v)

    def set(self, lhs, val):
        assert isinstance(lhs, Instruction)
        assert isinstance(val, ExprRef)
        self.values[lhs] = val

class SymbolicExecutor(Interpreter):
    def __init__(self, program):
        super().__init__(program)

    def execProgram(self, state):
        state = self.executeInstruction(state)
        if state and state.error:
            raise RuntimeError(f"Execution error: {state.error}")

    def executeJump(self, state):
        jump = state.pc
        condval = state.eval(jump.get_condition())
        if condval is None:
            state.error = f"Using unknown value: {jump.get_condition()}"
            return state

        assert isinstance(condval, BoolRef), f"Invalid condition: {condval}"
        successorblock = jump.get_operand(0 if condval else 1)
        state.pc = successorblock[0]
        return state

    def executeAssert(self, state):
        instruction = state.pc
        condval = state.eval(instruction.get_condition())
        if condval is None:
            state.error = f"Using unknown value: {jump.get_condition()}"
            return state

        assert isinstance(condval, BoolRef), f"Invalid condition: {condval}"
        if condval is False:
            state.error = f"Assertion failed: {instruction}"
        return state
        
    def run(self):
        entryblock = program.get_entry()
        state = SymbolicExecutionState(entryblock[0])

        cnt = 0
        while state:
            if cnt == 1:
                pass
            state = self.executeInstruction(state)
            if state and state.error:
                raise RuntimeError(f"Execution error: {state.error}")
            cnt += 1

        #print(f"Executed paths: {self.executed_paths}")
        #print(f"Error paths: {self.errors}")

if __name__ == "__main__":
    from parser import Parser
    from sys import argv
    if len(argv) != 2:
        print(f"Wrong number of arguments, usage: {argv[0]} <program>")
        exit(1)
    parser = Parser(argv[1])
    program = parser.parse()
    if program is None:
        print("Program parsing failed!")
        exit(1)

    I = SymbolicExecutor(program)
    exit(I.run())
