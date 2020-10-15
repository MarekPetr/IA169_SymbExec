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

        self.path_cond = [True]
        self.fork = False

    def copy(self):
        n = SymbolicExecutionState(self.pc)
        n.variables = self.variables.copy()
        n.values = self.values.copy()        
        n.path_cond = self.path_cond.copy()
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

    def handleUnknownCheckSolver(self, path_cond):
        raise RuntimeError(f"Solver failed for: {path_cond}")

    def forkJump(self, state, path_cond, op_idx):
        jump = state.pc
        s = Solver()
        s.add(path_cond)
        res = s.check()
        if res == sat:
            pc_state = state.copy()
            successorblock = jump.get_operand(op_idx)
            pc_state.path_cond = path_cond
            pc_state.pc = successorblock[0]
            self.stack.put(pc_state)
        elif res == unknown:
            self.handleUnknownCheckSolver(path_cond)

    def getExtendedPathCond(self, state, condval):
        path_cond = state.path_cond.copy()
        path_cond.append(condval)
        return path_cond

    def executeJump(self, state):
        jump = state.pc
        condval = state.eval(jump.get_condition())
        if condval is None:
            state.error = f"Using unknown value: {jump.get_condition()}"
            return state

        assert (isinstance(condval, BoolRef) or isinstance(condval, list) 
                or condval in [True, False])\
            , f"Invalid condition: {exprs}"
        
        path_cond = self.getExtendedPathCond(state, condval)
        self.forkJump(state, path_cond, 0)

        not_pc = state.path_cond.copy()
        not_pc.append(Not(condval))
        self.forkJump(state, not_pc, 1)
        
        state.fork = True
        return state

    def handleUninitVar(self, state):
        instruction = state.pc
        op = instruction.get_operand(0)
        state.set(instruction, Int(op.get_name()))
    
    def executeAssert(self, state):
        instruction = state.pc
        condval = state.eval(instruction.get_condition())
        if condval is None:
            state.error = f"Using unknown value: {jump.get_condition()}"
            return state

        assert isinstance(condval, BoolRef), f"Invalid condition: {condval}"

        path_cond = self.getExtendedPathCond(state, condval)
        s = Solver()
        s.add(path_cond)
        res = s.check()
        if res == sat:
            pc_state = state.copy()
            pc_state.pc = pc_state.pc.get_next_inst()
            if not pc_state.pc:
                self.executed_paths += 1
            else:
                self.stack.put(pc_state)
        elif res == unknown:
            self.handleUnknownCheckSolver(path_cond)

        s.reset()
        not_path_cond = self.getExtendedPathCond(state, Not(condval))
        s.add(not_path_cond)
        res = s.check()
        if res == sat:
            state.error = f"Assertion failed: {instruction}"
        elif res == unknown:
            self.handleUnknownCheckSolver(not_path_cond)
        return state

    def run(self):
        entryblock = program.get_entry()
        state = SymbolicExecutionState(entryblock[0])
        self.stack.put(state)

        while not self.stack.empty():
            state = self.stack.get()

            while state:
                state = self.executeInstruction(state)
                if state is None:
                    break
                if state.error:
                    self.errors += 1
                    self.executed_paths += 1
                    break
                if state.fork:
                    break
            if state is None:
                self.executed_paths += 1

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
