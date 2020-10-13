#!/usr/bin/python3

from language import Instruction, Variable, Cmp
from interpreter import ExecutionState, Interpreter
from z3 import *
from queue import LifoQueue


class SymbolicExecutionState(ExecutionState):
    def __init__(self, pc):
        super().__init__(pc)

        # add constraints here

        # dont forget to create _copy_ of attributes
        # when forking states (i.e., dont use
        # new.attr = old.attr, that would
        # only create a reference)

        self.pathCond = [True]

    def copy(self):
        n = SymbolicExecutionState(self.pc)
        n.variables = self.variables.copy()
        n.values = self.values.copy()        
        n.pathCond = self.pathCond.copy()
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

        self.stack = LifoQueue()
        self.executed_paths = 0
        self.errors = 0

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

        assert (isinstance(condval, BoolRef) or isinstance(condval, list) 
                or condval in [True, False])\
            , f"Invalid condition: {exprs}"
        
        s = Solver()
        pc = state.pathCond.copy()
        pc.append(condval)

        s.add(pc)
        if s.check() == sat:
            pc_state = state.copy()
            successorblock = jump.get_operand(0)
            pc_state.pathCond.append(condval)
            pc_state.pc = successorblock[0]
            self.stack.put(pc_state)

        s.reset()

        not_pc = state.pathCond.copy()
        not_pc.append(Not(condval))

        s.add(not_pc)
        if s.check() == sat:
            not_pc_state = state.copy()
            successorblock = jump.get_operand(1)
            not_pc_state.pathCond.append(condval)
            not_pc_state.pc = successorblock[0]
            self.stack.put(not_pc_state)
        
        return None

    def executeMem(self, state):
        instruction = state.pc
        ty = instruction.get_ty()
        op = instruction.get_operand(0)
        if ty == Instruction.LOAD:
            value = state.read(op)
            if value is None:
                state.set(instruction, Int(op.get_name()))
            else:
                state.set(instruction, value)
        elif ty == Instruction.STORE:
            value = state.eval(op)
            if value is None:
                state.error = f"Using unknown value: {op}"
            state.write(instruction.get_operand(1), value)
        else:
            raise RuntimeError(f"Invalid memory instruction: {instruction}")

        return state
    
    def executeAssert(self, state):
        instruction = state.pc
        condval = state.eval(instruction.get_condition())
        if condval is None:
            state.error = f"Using unknown value: {jump.get_condition()}"
            return state

        # TODO FORK HERE
        assert isinstance(condval, BoolRef), f"Invalid condition: {condval}"
        s = Solver()
        s.add(condval)
        print(s)
        if s.check() == unsat:
            print("fail")
            state.error = f"Assertion failed: {instruction}"
        return state

    def run(self):
        entryblock = program.get_entry()
        state = SymbolicExecutionState(entryblock[0])

        while True:
            while state:
                state = self.executeInstruction(state)
                if state and state.error:
                    print(state)
                    self.errors += 1
                    break
            
            if not self.stack.empty():
                state = self.stack.get()
                self.executed_paths += 1
            else:
                break
        
        # Paths count as leaves, if no leaves, paths = 1
        if self.executed_paths == 0:
            self.executed_paths = 1

        print(f"Executed paths: {self.executed_paths}")
        print(f"Error paths: {self.errors}")

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
