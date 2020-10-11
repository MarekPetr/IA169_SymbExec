"""
The representation of language elements and the program,
namely classes for instructions, variables declarations,
blocks and the program itself.
"""

class Variable:
    """ Class representing a variable and its value """
    def __init__(self, name):
        self._name = name
        self._value = None

    def get_name(self):
        """ Get name of the variable """
        return self._name

    def get_value(self):
        """ Get value of the variable """

    def set_value(self, val):
        """ Set value of the variable """
        self._value = val

class Instruction:
    """
    Base class for instructions
    """

    id_counter = 0

    ADD = 1
    SUB = 2
    MUL = 3
    DIV = 4
    CMP = 5
    JUMP = 6
    LOAD = 7
    STORE = 8
    PRINT = 9
    ASSERT = 10
    HALT = 11

    def __init__(self, ty, operands, name=None):
        assert isinstance(operands, list)
        self._ty = ty
        self._operands = operands

        # set the id of the instruction
        Instruction.id_counter += 1
        self._id = Instruction.id_counter

        # block and the instruction's position in it
        self._block = None
        self._block_idx = None

        assert name is None or isinstance(name, str)
        self._name = name

    def get_ty(self):
        """ Get the type of instruction """
        return self._ty

    def get_id(self):
        """
        Get ID of this instruction. Every instruction has a unique ID
        that is used as the jump target
        """
        return self._id

    def get_operand(self, idx):
        """ Get the operand with the given index """
        assert idx < len(self._operands)
        return self._operands[idx]

    def get_operands(self):
        """ Get all the operands """
        return self._operands

    def get_name(self):
        """ Get the name of this instruction or xID if no name is set """
        return self._name or f"x{self.get_id()}"

    def set_block(self, block, idx):
        assert 0 <= idx < block.size()
        self._block = block
        self._block_idx = idx

    def get_next_inst(self):
        """ Get instruction that follows this one in the same block """
        block = self._block
        if block is None:
            return None
        if self._block_idx >= block.size() - 1:
            return None
        return block[self._block_idx + 1] 

class Block:
    """ Block of instructions """
    def __init__(self, name):
        self._name = name
        self._instructions = []

    def get_name(self):
        """ Get name of the variable """
        return self._name

    def size(self):
        """ Return the size of this block """
        return len(self._instructions)

    def add(self, instr):
        """ Add instruction into this block """
        assert isinstance(instr, Instruction)
        self._instructions.append(instr)
        instr.set_block(self, len(self._instructions) - 1)

    def __iter__(self):
        return self._instructions.__iter__()

    def __getitem__(self, idx):
        assert idx < len(self._instructions)
        return self._instructions[idx]

    def __repr__(self):
        return "block {0}:\n  {1}".format(self._name,
                                      "\n  ".join(map(str, self._instructions)))

class Program:
    """ Program is a list of blocks, the first being the entry block """

    def __init__(self):
        self._variables = {}
        self._blocks = []

    def get_entry(self):
        """ Get entry block of the program """
        assert len(self._blocks) != 0
        return self._blocks[0]

    def add_block(self, blk):
        """ Add block to the program """

        assert isinstance(blk, Block)
        assert blk not in self._blocks, "Duplicate block"
        self._blocks.append(blk)

    def add_variable(self, var):
        """ Add variable to the program """

        assert isinstance(var, Variable)
        assert var not in self._variables, "Duplicate variable"
        self._variables[var.get_name()] = var

    def __iter__(self):
        return self._blocks.__iter__()

    def __repr__(self):
        return """variables: {0}\n\n{1} """.format(\
            " ".join(self._variables.keys()),
            "\n\n".join(map(str, self._blocks)))


######################################################################
# Particular instructions
######################################################################

def op2str(op):
    if isinstance(op, int):
        return str(op)
    assert isinstance(op, (Instruction, Variable))
    return op.get_name()



# class Print

class Load(Instruction):
    """ Represents reading a variable """

    def __init__(self, var, name=None):
        super().__init__(Instruction.LOAD, [var], name)
        assert isinstance(var, Variable)

    def __repr__(self):
        return "{0} = load {1}".format(self.get_name(),
                                       self.get_operand(0).get_name())

class Store(Instruction):
    """ Represents write to a variable """

    def __init__(self, val, var):
        super().__init__(Instruction.STORE, [val, var])

    def __repr__(self):
        return "store {0} to {1}".format(op2str(self.get_operand(0)),
                                         self.get_operand(1).get_name())

class Print(Instruction):
    """ Represents printing a value """

    def __init__(self, vals):
        super().__init__(Instruction.PRINT, vals)

    def __repr__(self):
        return "print {0}".format(" ".join(map(op2str, self.get_operands())))

class Halt(Instruction):
    """ Represents halting the program """

    def __init__(self):
        super().__init__(Instruction.HALT, [])

    def __repr__(self):
        return "halt"

class Assert(Instruction):
    """ Represents assertion """

    def __init__(self, op):
        super().__init__(Instruction.ASSERT, [op])

    def get_condition(self):
        return self.get_operand(0)

    def __repr__(self):
        return "assert {0}".format(op2str(self.get_operand(0)))


class Jump(Instruction):
    """
    Represents a jump to t1 if condition is satisfied
    or to t2 if it is not satisfied.
    """
    def __init__(self, condition, t1, t2):
        super().__init__(Instruction.JUMP, [t1, t2])
        assert isinstance(t1, Block) and\
               isinstance(t2, Block)

        assert condition is not None
        self._cond = condition

    def get_condition(self):
        """ Return the condition of this jump """
        return self._cond

    def __repr__(self):
        return "jump {0} {1} {2}".format(op2str(self.get_condition()),
                                         self.get_operand(0).get_name(),
                                         self.get_operand(1).get_name())

def predicate_to_str(pred):
    """ Transform the number of predicate to string """

    if pred == Cmp.LT:
        return 'lt'
    if pred == Cmp.LE:
        return 'le'
    if pred == Cmp.GT:
        return 'gt'
    if pred == Cmp.GE:
        return 'ge'
    if pred == Cmp.EQ:
        return 'eq'
    if pred == Cmp.NE:
        return 'ne'
    raise RuntimeError("Invalid predicate")

class Cmp(Instruction):
    """ The cmp instruction """
    LT = 1
    LE = 2
    GT = 3
    GE = 4
    EQ = 5
    NE = 6

    def __init__(self, predicate, a, b, name=None):
        super().__init__(Instruction.CMP, [a, b], name)
        assert isinstance(predicate, int) and\
               Cmp.LT <= predicate <= Cmp.NE

        self._predicate = predicate

    def get_predicate(self):
        """ Get the predicate of this comparision """
        return self._predicate

    def __repr__(self):
        return "{0} = cmp {1} {2}, {3}".format(self.get_name(),
                                           predicate_to_str(self._predicate),
                                           op2str(self.get_operand(0)),
                                           op2str(self.get_operand(1)))

class Add(Instruction):
    """ The add instruction """

    def __init__(self, a, b, name=None):
        super().__init__(Instruction.ADD, [a, b], name)

    def __repr__(self):
        return "{0} = add {1} {2}".format(self.get_name(),
                                          op2str(self.get_operand(0)),
                                          op2str(self.get_operand(1)))

class Sub(Instruction):
    """ The sub instruction """

    def __init__(self, a, b, name=None):
        super().__init__(Instruction.SUB, [a, b], name)

    def __repr__(self):
        return "{0} = sub {1} {2}".format(self.get_name(),
                                          op2str(self.get_operand(0)),
                                          op2str(self.get_operand(1)))

class Mul(Instruction):
    """ The mul instruction """

    def __init__(self, a, b, name=None):
        super().__init__(Instruction.MUL, [a, b], name)

    def __repr__(self):
        return "{0} = mul {1} {2}".format(self.get_name(),
                                          op2str(self.get_operand(0)),
                                          op2str(self.get_operand(1)))

class Div(Instruction):
    """ The div instruction """

    def __init__(self, a, b, name=None):
        super().__init__(Instruction.DIV, [a, b], name)

    def __repr__(self):
        return "{0} = div {1} {2}".format(self.get_name(),
                                          op2str(self.get_operand(0)),
                                          op2str(self.get_operand(1)))
