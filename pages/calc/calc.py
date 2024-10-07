from enum import Enum

class Error:
    def __init__(self, string):
        self.message = string
    def __str__(self):
        return "error:" + self.message

class LexKind(Enum):
    INVALID = -1
    PLUS = 0
    MINUS = 1
    MULT = 2
    DIV = 3
    NUM = 4
    EOF = 5
    NEG = 6
    LEFTPAREN = 7
    RIGHTPAREN = 8

class Lexeme:
    def __init__(self, string, kind):
        self.text = string
        self.kind = kind
    def __str__(self):
        return "(" + self.text + ", " + self.kind.__str__() + ")"

class Lexer:
    def __init__(self, string):
        self.string = string
        self.start = 0
        self.end = 0
        self.word = None
        self.isTracking = False

    def next(self):
        self.word = self._any()
        return self.word

    def alltokens(self):
        all = []
        l = self.next()
        while l.kind != LexKind.EOF:
            all += [l]
            l = self.next()
        return all

    def track(self, str):
        if self.isTracking:
            print(str, self.word)

    def _peek_rune(self):
        if self.end >= len(self.string):
            return ""
        return self.string[self.end]

    def _next_rune(self):
        if self.end >= len(self.string):
            return ""
        r = self.string[self.end]
        self.end += 1
        return r

    def _emit(self, kind):
        s = self.string[self.start:self.end]
        self.start = self.end
        return Lexeme(s, kind)

    def _ignore(self):
        self.start = self.end

    def _ignore_whitespace(self):
        r = self._peek_rune()
        while r == " ":
            self._next_rune()
            r = self._peek_rune()
        self._ignore()

    def _any(self):
        self._ignore_whitespace()
        r = self._peek_rune()
        if r.isnumeric():
            return self._number()
        elif r == "+":
            self._next_rune()
            return self._emit(LexKind.PLUS)
        elif r == "-":
            self._next_rune()
            return self._emit(LexKind.MINUS)
        elif r == "*":
            self._next_rune()
            return self._emit(LexKind.MULT)
        elif r == "/":
            self._next_rune()
            return self._emit(LexKind.DIV)
        elif r == "~":
            self._next_rune()
            return self._emit(LexKind.NEG)
        elif r == "(":
            self._next_rune()
            return self._emit(LexKind.LEFTPAREN)
        elif r == ")":
            self._next_rune()
            return self._emit(LexKind.RIGHTPAREN)
        elif r == "":
            return Lexeme("", LexKind.EOF)
        else:
            self._next_rune()
            return Lexeme(r, LexKind.INVALID)

    def _number(self):
        r = self._peek_rune()
        while r.isnumeric():
            self._next_rune()
            r = self._peek_rune()
        return self._emit(LexKind.NUM)

def consume(lexer):
    if lexer.word.kind == LexKind.INVALID:
        return None, Error("invalid character")
    out = lexer.word
    lexer.next()
    return Node(out), None;

class Node:
    def __init__(self, value):
        self.value = value
        self.leaves = []

    def addLeaf(self, leaf):
        self.leaves += [leaf];

    def left(self):
        return self.leaves[0]
    def right(self):
        return self.leaves[1]

def print_tree(node):
    _print_tree(node, 0)

def _print_tree(node, depth):
    print(_indent(depth), node.value)
    for n in node.leaves:
        _print_tree(n, depth+1)

def _indent(n):
    i = 0
    out = ""
    while i < n:
        out += "  "
        i += 1
    return out

# implements:
#     <prod> {<op> <prod>}
#     where <op> is recognized by the predicate
def _repeatBinary(lexer, production, predicate):
    last, err = production(lexer)
    if err != None:
        return None, err
    if last == None:
        return None, None
    while predicate(lexer):
        parent, err = consume(lexer)
        if err != None:
            return None, err
        parent.addLeaf(last)

        newLeaf, err = production(lexer)
        if err != None:
            return None, err
        parent.addLeaf(newLeaf)
        last = parent
    return last, None

def _lexTest(lexer, things):
    for kind in things:
        if lexer.word.kind == kind:
            return True
    return False

def _sumOp(lexer):
    return _lexTest(lexer, [LexKind.PLUS, LexKind.MINUS])

def _multOp(lexer):
    return _lexTest(lexer, [LexKind.MULT, LexKind.DIV])


def Parse(lexer):
    lexer.track("Parse")
    lexer.next() # we must populate lexer.word
    return _expr(lexer)

def _expr(lexer):
    lexer.track("_expr")
    return _repeatBinary(lexer, _mult, _sumOp)

def _mult(lexer):
    lexer.track("_mult")
    return _repeatBinary(lexer, _unary, _multOp)

def _unary(lexer):
    lexer.track("_unary")
    parent = None
    if lexer.word.kind == LexKind.NEG:
        parent, err = consume(lexer)
        if err != None:
            return None, err

    n, err = _term(lexer)
    if err != None:
        return None, err

    if parent != None:
        parent.addLeaf(n)
        return parent, None
    return n, None

def _term(lexer):
    lexer.track("_term")
    if lexer.word.kind == LexKind.NUM:
        return consume(lexer)
    elif lexer.word.kind == LexKind.LEFTPAREN:
        return _nestedExpr(lexer)
    else:
        return None, Error("unexpected token in term")

def _nestedExpr(lexer):
    lexer.track("_nestedExpr")
    _discard, err = consume(lexer)
    if err != None:
        return None, err
    if _discard.value.kind != LexKind.LEFTPAREN:
        return None, Error("bad use of _nestedExpr")

    exp, err = _expr(lexer)
    if err != None:
        return None, err

    _discard, err = consume(lexer)
    if err != None:
        return None, err
    if _discard.value.kind != LexKind.RIGHTPAREN:
        return None, Error("expected closing parenthesis in expression")

    return exp, None

def eval(node):
    if node.value.kind == LexKind.PLUS:
        return eval(node.left()) + eval(node.right())
    elif node.value.kind == LexKind.MINUS:
        return eval(node.left()) - eval(node.right())
    elif node.value.kind == LexKind.NEG:
        return -eval(node.left())
    elif node.value.kind == LexKind.MULT:
        return eval(node.left()) * eval(node.right())
    elif node.value.kind == LexKind.DIV:
        return eval(node.left()) / eval(node.right())
    elif node.value.kind == LexKind.NUM:
        return int(node.value.text)

def test(str, result):
    l = Lexer(str)
    n, err = Parse(l)
    if err != None:
        print(err)
        return
    print_tree(n)
    return eval(n) == result


if __name__ == "__main__":
    tests = [
        ("1+2", 3), ("3*5", 15), ("1+2*5", 11),
        ("1+10/2", 6), ("3*~5", -15), ("(5*5)/5", 5),
    ]
    for t in tests:
        ok = test(t[0], t[1])
        if ok:
            print(t[0], "OK!")
        else:
            print(t[0], "FAIL!")
