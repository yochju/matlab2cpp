Paren = "(%(0)s)"

def End(node):
    """The 'end' statement indicating not end of block, but end-of-range."""

    # find context for what end refers to
    pnode = node
    while pnode.parent.cls not in \
            ("Get", "Cget", "Nget", "Fget", "Sget",
            "Set", "Cset", "Nset", "Fset", "Sset", "Block"):
        pnode = pnode.parent

    # end statement only makes sense in certain contexts
    if pnode.cls == "Block":
        node.error("Superfluous end-statement")
        return "end"

    index = pnode.parent.children.index(pnode)
    name = pnode = pnode.parent.name

    # what end is referring to
    if index == 0:
        return name + ".n_rows"
    elif index == 1:
        return name + ".n_cols"
    elif index == 2:
        return name + ".n_slices"
    else:
        node.error("end statement in arg>3")

Break = "break"

def Return(node):
    func = node.func
    if func["backend"] == "func_returns":
        return "return"

    if func["backend"] == "func_lambda":
        return "return _retval"

    return_value = func[1][0].name
    return "return " + return_value


# simple operators
def Mul(node):
    """(Matrix-)multiplication
    """

    # unknown input
    if node.type == "TYPE":
        return "", "*", ""

    # not numerical
    if not node.num:
        node.error("non-numerical multiplication %s" % str([n.type for n in node]))
        return "", "*", ""

    dim = node[0].dim
    for child in node[1:]:

        if dim == 0:
            dim = child.dim

        if dim == 1:
            if child.dim == 0:
                dim = 1
            elif child.dim == 1:
                child.error("multiplication shape mismatch, colvec*colvec")
            elif child.dim == 2:
                dim = 3
            elif child.dim == 3:
                child.error("multiplication shape mismatch, colvec*matrix")
            elif child.dim == 4:
                child.error("multiplication shape mismatch, colvec*cube")

        elif dim == 2:
            if child.dim == 0:
                dim = 2
            elif child.dim == 1:
                dim = 0
            elif child.dim == 2:
                child.error("multiplication shape mismatch, rowvec*rowvec")
            elif child.dim == 3:
                dim = 3

        elif dim == 3:
            if child.dim == 0:
                dim = 3
            elif child.dim == 1:
                dim = 1
            elif child.dim == 2:
                child.error("multiplication shape mismatch, matrix*rowvec")
            elif child.dim == 3:
                dim = 3

    node.dim = dim

    return "", "*", ""

def Elmul(node):
    """Element multiplication
    """

    # unknown input
    if node.type == "TYPE":
        return "", ".*", ""

    # not numerical
    if not node.num:
        node.error("non-numerical multiplication %s" % str([n.type for n in node]))
        return "", ".*", ""

    # scalar multiplication
    if node.dim == 0:
        return "", "*", ""

    # Sclar's multiplication in Armadillo '%' needs special handle because of
    # interpolation in python
    return "", "__percent__", ""

def Plus(node):

    # non-numerical addition
    if not node.num:
        node.error("non-numerical addition %s" % str([n.type for n in node]))

    return "", "+", ""

def Minus(node):
    return "", "-", ""

Gt      = "", ">", ""
Ge      = "", ">=", ""
Lt      = "", "<", ""
Le      = "", "<=", ""
Ne      = "", "~=", ""
Eq      = "", "==", ""
Band    = "", "&&", ""
Land    = "", "&", ""
Bor     = "", "||", ""
Lor     = "", "|", ""

def Elementdivision(node):
    """Element wise division
    """

    # unknown input
    if node.type == "TYPE":

        # default to assume everything scalar
        out = str(node[0])
        for child in node[1:]:

            # force to be float if int in divisor
            if child.cls == "Int":
                out = out + "/" + str(child) + ".0"
            else:
                out = out + "/" + str(child)
        return out

    out = str(node[0])

    # force float output
    mem = node[0].mem
    if mem<2:
        mem = 2

    for child in node[1:]:

        # convert ints to floats
        if child.cls == "Int":
            out = out + "/" + str(child) + ".0"

        # avoid int/uword division
        elif mem < 2:
            out = out + "*1.0/" + str(child)

        else:
            out = out + "/" + str(child)

        mem = max(mem, child.mem)

    node.mem = mem

    return out


def Leftelementdivision(node):
    """Left element wise division
    """

    # unknown input
    if node.type == "TYPE":
        return "", "\\", ""

    # iterate backwards
    out = str(node[-1])

    # force float output
    mem = node[-1].mem
    if mem<2:
        mem = 2

    for child in node[-2::-1]:

        # avoid explicit integer division
        if child.cls == "Int":
            out = str(child) + ".0/" + out

        # avoid implicit integer division
        if child.mem < 2 and mem < 2:
            out = str(child) + "*1.0/" + out

        else:
            out = str(child) + "/" + out

        mem = max(mem, child.mem)

    node.mem = mem
    
    return out


def Matrixdivision(node):

    # unknown input
    if node.type == "TYPE":
        return "", "/", ""

    # start with first element ...
    out = str(node[0])

    mem = node[0].mem
    dim = node[0].dim

    # everything scalar -> use element division
    if {n.dim for n in node} == {0}:

        return Elementdivision(node)

    else:

        # ... iterate over the others
        for child in node[1:]:

            # matrix handle
            if child.dim == 3:
                out = "arma::solve(" + str(child) + ".t(), " + out + ".t()).t()"

            # avoid integer division
            elif child.mem < 2 and mem < 2:
                out = out + "*1.0/" + str(child)
                mem = 2

            else:
                out = out + "/" + str(child)

            # track memory output
            mem = max(mem, child.mem)

            # assert if division legal in matlab
            if dim == 0:
                dim = child.dim

            elif dim == 1:
                if child.dim == 0:
                    dim = 1
                elif child.dim == 1:
                    node.error("Matrix division error 'colvec\\colvec'")
                elif child.dim == 2:
                    dim = 3
                elif child.dim == 3:
                    node.error("Matrix division error 'colvec\\matrix'")
                elif child.dim == 3:
                    node.error("Matrix division error 'colvec\\cube'")

            elif dim == 2:
                if child.dim == 0:
                    dim = 2
                elif child.dim == 1:
                    dim = 0
                elif child.dim == 2:
                    node.error("Matrix division error 'rowvec\\rowvec'")
                elif child.dim == 3:
                    dim = 2
                elif child.dim == 4:
                    dim = 3

            elif dim == 3:
                if child.dim == 0:
                    dim = 3
                elif child.dim == 1:
                    dim = 1
                elif child.dim == 2:
                    node.error("Matrix division error 'matrix\\rowvec'")
                elif child.dim == 3:
                    dim = 3
                elif child.dim == 4:
                    dim = 4

    node.type = (dim, mem)

    return out


def Leftmatrixdivision(node):
    """Left operator matrix devision
    """

    # unknown input
    if node.type == "TYPE":
        return "", "\\", ""

    # start with first node ...
    out = str(node[0])

    mem = node[0].mem
    dim = node[0].dim

    # everything scalar -> use left element division
    if {n.dim for n in node} == {0}:
        return Leftelementdivision(node)

    else:

        # ... iterate forwards
        for child in node[1:]:

            # classical array inversion
            if child.dim > 0:
                out = "arma::solve(" + out + ", " + str(child) + ")"

            # avoid integer division
            # backwords since left division is reverse
            elif child.mem < 2 and mem < 2:
                out = "(" + out + ")*1.0/" + str(child)
                mem = 2

            # backwords since left division is reverse
            else:
                out = "(" + out + ")/" + str(child)
                # out = str(child) + "/" + out

            mem = max(mem, child.mem)

            # assert division as legal
            if dim == 0:
                dim = node.dim

            elif dim == 1:
                if node.dim == 0:
                    dim = 1
                elif node.dim == 1:
                    node.error("Matrix division error 'colvec\\colvec'")
                elif node.dim == 2:
                    dim = 3
                elif node.dim == 3:
                    node.error("Matrix division error 'colvec\\matrix'")
                elif node.dim == 3:
                    node.error("Matrix division error 'colvec\\cube'")

            elif dim == 2:
                if node.dim == 0:
                    dim = 2
                elif node.dim == 1:
                    dim = 0
                elif node.dim == 2:
                    node.error("Matrix division error 'rowvec\\rowvec'")
                elif node.dim == 3:
                    dim = 2
                elif node.dim == 4:
                    dim = 3

            elif dim == 3:
                if node.dim == 0:
                    dim = 3
                elif node.dim == 1:
                    dim = 1
                elif node.dim == 2:
                    node.error("Matrix division error 'matrix\\rowvec'")
                elif node.dim == 3:
                    dim = 3
                elif node.dim == 4:
                    dim = 4

    node.type = (dim, mem)

    return out



def Exp(node):
    """Exponent
    """

    out = str(node[0])
    for child in node[1:]:
        out = "arma::pow(" + str(out) + "," + str(child) + ")"

    return out

def Elexp(node):
    """Elementwise exponent
    """

    out = str(node[0])
    for child in node[1:]:
        out = "pow(" + str(out) + "," + str(child) + ")"
    return out


def All(node):
    """All ':' element
    """
    arg = node.parent.name

    # is first arg
    if len(node.parent) > 0 and node.parent[0] is node:
        arg += ".n_rows"

    # is second arg
    elif len(node.parent) > 1 and node.parent[1] is node:
        arg += ".n_cols"

    # is third arg
    elif len(node.parent) > 2 and node.parent[2] is node:
        arg += ".n_slices"

    else:
        return "span::all"

    return "m2cpp::uspan(0, " + arg + "-1)"

Neg = "-(", "", ")"
Not = "not ", "", ""

def Transpose(node):
    """(Simple) transpose
    """

    # unknown datatype
    if not node.num:
        return "arma::strans(%(0)s)"

    # colvec -> rowvec
    if node[0].dim == 1:
        node.dim = 2

    # rowvec -> colvec
    elif node[0].dim == 2:
        node.dim = 1

    return "arma::strans(", "", ")"

def Ctranspose(node):
    """Complex transpose
    """

    # unknown input
    if not node.num:
        return "arma::trans(", "", ")"

    # colvec -> rowvec
    if node[0].dim == 1:
        node.dim = 2

    # rowvec -> colvec
    elif node[0].dim == 2:
        node.dim = 1

    # not complex type
    if node.mem < 5:
        return "arma::strans(", "", ")"
    
    return "arma::trans(", "", ")"

def Colon(node):

    # context: array argument (must always be uvec)
    if node.parent.cls in ("Get", "Cget", "Nget", "Fget", "Sget",
                "Set", "Cset", "Nset", "Fset", "Sset") and node.parent.num:
        node.type = "uvec"

        # two arguments
        if len(node) == 2:
            return "arma::span(%(0)s-1, %(1)s-1)"

        # three arguments
        elif len(node) == 3:
            node.include("uspan")
            return "m2cpp::uspan(%(0)s-1, %(1)s, %(2)s-1)"

        else:
            return "", ":", ""

    else:

        # context: matrix concatination
        if node.group.cls in ("Matrix",) and node.group.num:
            node.type = "ivec"

        # context: pass to function
        elif node.parent.cls in ("Get", "Cget", "Nget", "Fget", "Sget",
                "Set", "Cset", "Nset", "Fset", "Sset"):
            node.type = "ivec"

        # context: assignment
        elif node.group.cls in ("Assign",) and node.group[0].num:
            node.type = "uvec"

        else:
            node.type = "ivec"

        # <start>:<stop>
        if len(node) == 2:
            return "arma::span(%(0)s, %(1)s)"

        # <start>:<step>:<stop>
        elif len(node) == 3:
            args = "(%(0)s, %(1)s, %(2)s)"

        # no negative indices
        if node.mem == 0:
            return "m2cpp::uspan"+args

        return "m2cpp::span"+args
