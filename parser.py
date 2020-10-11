from os.path import isfile
from language import *
from sys import stderr

"""
Parser of our language that takes text form
of the language and create its in-memory representation
"""

def _parse_block_name(line):
    parts = line.split()
    if len(parts) != 2:
        raise RuntimeError(f"Invalid block statement: should be 'block name:'")
    if parts[0] != 'block':
        raise RuntimeError(f"Invalid block statement: should be 'block name:'")
    if parts[1][-1] != ':':
        raise RuntimeError(f"Invalid block statement: should be 'block name:'")

    return parts[1][:-1]

class Parser:
    def __init__(self, path):
        self._path = path
        self.program = Program()
        self.blocks = {}
        self.variables = {}
        self.instructions = {}
        self._currentblk = None

    def _get_file(self):
        assert isfile(self._path), f"{path} is not a file"
        return open(self._path, 'r')

    def _get_lines(self):
        with self._get_file() as f:
            for line in (l.strip() for l in f):
                if line and not line.startswith(';'):
                    yield line

    def _get_blocks(self):
        """
        Parse the text and obtain blocks without
        creating their contents (we need blocks
        created before creating instructions as
        blocks as targets of jump instructions.
        """
        def parse_line(line):
            if not line.startswith('block'):
                return
            
            name = _parse_block_name(line)
            if self.blocks.get(name):
                raise RuntimeError(f"Duplicated block name: '{name}'")

            blk = Block(name)
            self.program.add_block(blk)
            self.blocks[name] = blk

        for line in self._get_lines():
             try:
                 parse_line(line)
             except RuntimeError as e:
                 print(f"Error occured while parsing line: {line}",
                       file=stderr)
                 print(f"  {e}", file=stderr)

    def _parse_variables(self, line):
        parts = line.split()
        if parts[0] != 'variables:':
            raise RuntimeError("Wrong 'variables' clause")

        for varname in parts[1:]:
            if varname in self.variables:
                raise RuntimeError(f"Duplicated variable: {var}")
            var = Variable(varname)
            self.variables[varname] = var
            self.program.add_variable(var)

    def _get_op(self, op):
        try:
            opval = int(op)
        except ValueError:
            opval = self.instructions.get(op)
        return opval

    def _get_cond(self, op):
        cond = self._get_op(op)
        if cond is None:
            if op in ['true', 'True']:
                cond = True
            elif op in ['false', 'False']:
                cond = False
        return cond

    def _get_operands(self, ops):
        operands = []
        for op in ops:
            opval = self._get_op(op)
            if opval is not None:
                operands.append(opval)
            else:
                raise RuntimeError(f"Invalid operand: {op}")
        return operands

    def _parse_with_eq(self, line):
        parts = line.split('=')
        if len(parts) != 2:
            raise RuntimeError(f"Invalid instruction: {line}")
        lhs = parts[0].strip()
        if self.instructions.get(lhs):
            raise RuntimeError(f"Duplicated instruction name: {lhs}")

        rhs = parts[1].split()
        if rhs[0] == 'load':
            Instr = Load
            if len(rhs) != 2:
                raise RuntimeError(f"Invalid load: should be 'x = load var'")
            var = self.variables.get(rhs[1])
            if var is None:
                raise RuntimeError(f"Unknown variable: {var}")
            operands = [var]
        elif rhs[0] == 'cmp':
            if len(rhs) != 4:
                raise RuntimeError(f"Invalid cmp instruction: {rhs}")
            Instr = Cmp
            pred = None
            if rhs[1] == 'le':
                pred = Cmp.LE
            elif rhs[1] == 'lt':
                pred = Cmp.LT
            elif rhs[1] == 'ge':
                pred = Cmp.GE
            elif rhs[1] == 'gt':
                pred = Cmp.GT
            elif rhs[1] == 'eq':
                pred = Cmp.EQ
            elif rhs[1] == 'ne':
                pred = Cmp.NE
            else:
                raise RuntimeError(f"Invalid cmp instruction predicate: {rhs[1]}")
            operands = self._get_operands(rhs[2:])
            if len(operands) != 2:
                raise RuntimeError(f"Invalid cmp operands: {operands}")
            return lhs, Cmp(pred, *operands)
        else:
            Instr = None
            if rhs[0] == 'add':
                Instr = Add
            elif rhs[0] == 'sub':
                Instr = Sub
            elif rhs[0] == 'mul':
                Instr = Mul
            elif rhs[0] == 'div':
                Instr = Div

            if not Instr:
                raise RuntimeError(f"Unrecognized instruction: {rhs[0]}")
            operands = self._get_operands(rhs[1:])
            if len(operands) != 2:
                    raise RuntimeError(f"Invalid operands: {operands}")

        I = Instr(*operands, name=lhs)
        return lhs, I

    def _parse_instruction(self, line, blk):
        if line ==  'halt':
            I = Halt()
            blk.add(I)
        elif line.startswith('store'):
            parts = line.split()
            if len(parts) != 4 or parts[2] != 'to':
                raise RuntimeError(f"Invalid store instruction")
            val = self._get_op(parts[1])
            if val is None:
                raise RuntimeError(f"Invalid value to store")
            to = self.variables.get(parts[3])
            if to is None:
                raise RuntimeError(f"Invalid variable to store")
            I = Store(val, to)
            blk.add(I)
        elif line.startswith('jump'):
            parts = line.split()
            if len(parts) != 4:
                raise RuntimeError("Invalid jump instruction")
            cond = self._get_cond(parts[1])
            if cond is None:
                raise RuntimeError(f"Invalid jump condition: {parts[1]}")
            T = self.blocks.get(parts[2])
            if T is None:
                raise RuntimeError(f"Invalid jump target: {parts[2]}")
            F = self.blocks.get(parts[3])
            if F is None:
                raise RuntimeError(f"Invalid jump target: {parts[3]}")
            I = Jump(cond, T, F)
            blk.add(I)
        elif line.startswith('print'):
            parts = line.split()
            operands = self._get_operands(parts[1:])
            I = Print(operands)
            blk.add(I)
        elif line.startswith('assert'):
            parts = line.split()
            if len(parts) != 2:
                raise RuntimeError("Invalid assertion")
            cond = self._get_cond(parts[1])
            if cond is None:
                raise RuntimeError(f"Invalid assertion condition: {parts[1]}")
            I = Assert(cond)
            blk.add(I)
        elif '=' in line:
            lhs, I = self._parse_with_eq(line)
            self.instructions[lhs] = I
            blk.add(I)

    def _check_program(self):
        pass

    def parse(self):
        self._get_blocks()
        # now parse instructions and assign them to the block
        def parse_line(line):
            if line.startswith('block'):
                self._currentblk = self.blocks[_parse_block_name(line)]
                assert self._currentblk, "BUG: do not have a block"
            elif line.startswith('variables:'):
                # we should check that this goes at the beginning, but what the
                # hell...
                self._parse_variables(line)
            else:
                assert self._currentblk
                self._parse_instruction(line, self._currentblk)

        for line in self._get_lines():
             try:
                 parse_line(line)
             except RuntimeError as e:
                 print(f"Error occured while parsing line: {line}",
                       file=stderr)
                 print(f"  {e}", file=stderr)
                 return None


        self._check_program()
        return self.program


# debugging...
if __name__ == "__main__":
    from sys import argv
    if len(argv) != 2:
        print(f"Wrong numer of arguments, usage: {argv[0]} <program>")
        exit(1)
    parser = Parser(argv[1])
    program = parser.parse()
    print(program)
