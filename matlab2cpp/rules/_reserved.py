"""
Reserved translation rules

The module will always check if the specific "<class>_<name>" name
exists before finding the generic "<class>" name.
"""

# List of function names that should be handled by reserved.py:
reserved = {
"i", "and", "or", "not", "all", "any",
"false", "true", "pi", "inf", "Inf", "nan", "NaN",
"eye", "flipud", "length", "max", "min", "size",
"transpose", "ctranspose",
"abs", "nextpow2", "fft", "ifft", "hankel",
"zeros", "ones", "round", "return", "rand", "floor",
"clear", "close", "plot", "hold",
"_conv_to", "_reshape",
"interp1", "linspace", "varargins",
"sum", "conj", "real", "imag",
"tic", "toc", "diag",
}

# Common attribute

Assign = "%(0)s = %(1)s ;"

def Declare(node):
    raise ValueError("Variable name '%s' is reserved."%node["name"]\
            +"\nPlease rename variable.")

def Var(node):
    return "%(name)s"


Var_pi = "datum::pi"
Var_true = "1"
Var_false = "0"
Var_inf = "datum::inf"
Var_Inf = "datum::inf"
Var_nan = "datum::nan"
Var_NaN = "datum::nan"

# Special handle of 'i'-variable

Var_i = "cx_complex(0, 1)"

def Get_abs(node):
    node.type = node[0].type
    return "abs(", ", ", ")"

def Get_and(node):
    return "(", "*", ")"

def Get_or(node):
    return "("+"+".join(["%(" + i +")s*%(" + i + ")s" \
            for i in xrange(len(node))])+")"

def Get_not(node):
    assert len(node) == 1
    if not node[0].num:
        return "not(%(0)s)"
    return "(%(0)s == 0)"

def Get_any(node):
    if not node[0].num:
        return "any(", ", ", ")"

    node.type = node[0].type

    # unknown datatype
    if node[0].dim == 0:
        return "%(0)s"

    # colvec or rowvec
    elif node.dim in (1,2):
        node.dim = 0

    # matrix
    elif node.dim == 3:

        # axis input decides by second input
        if len(node) == 2:

            if  node[1].cls == "Int":
                val = node[1].value
                if val == "1":
                    node.dim = 2
                elif val == "2":
                    node.dim = 1

            # problem if arg not explicit
            else:
                node.num = False

    # cube
    else:
        node.dim = 3

    return "any(", ", ", ")"

def Get_all(node):

    # unkonwn datatype
    if not node[0].num:
        return "all(", ", ", ")"

    node.type = node[0].type

    # scalar value
    if node[0].dim == 0:
        return "%(0)s"

    # colvec or rowvec
    elif node.dim in (1,2):
        node.dim = 0

    # matrix
    elif node.dim == 3:

        # axis input decides by second input
        if len(node) == 2:

            if  node[1].cls == "Int":
                val = node[1].value
                if val == "1":
                    node.dim = 2
                elif val == "2":
                    node.dim = 1

            # problem if arg not explicit
            else:
                node.num = False

    # cube
    else:
        node.dim = 3

    return "all(", ", ", ")"


def Var_return(node):

    # multi-return does not return a value
    if node.func["backend"] == "func_returns":
        return "return"
    return "return " + str(node.func[0])


def Get_size(node):

    # unknown input
    if node[0].type == "TYPE" or node.parent.cls == "Assigns":
        return "size(", ", ", ")"

    var = str(node[0])

    # multiple args
    if len(node) > 1:

        # determine ax from second arg
        node.type = "uword"
        arg2 = node[1].value
        if arg2 == "1":
            return var+".n_rows"
        if arg2 == "2":
            return var+".n_cols"
        if arg2 == "3":
            return var+".n_slices"

    # colvec or rowvec
    elif node[0].dim in (1,2):
        node.type = "uword"
        return var+".n_elem"

    # matrix (returns two values)
    elif node[0].dim == 3:
        node.type = "urowvec"
        # inline calls moved to own line
        if node.parent.cls not in ("Statement", "Assign"):
            return str(node.auxiliary())

        node.parent.backend = "reserved"
        node.parent.name = "size"
        return "{%(0)s.n_rows, %(0)s.n_cols}"

    # cube (return three values)
    elif node[0].dim == 4:
        node.type = "urowvec"
        # inline calls moved to own line
        if node.parent.cls not in ("Statement", "Assign"):
            return str(node.auxiliary())

        node.parent.backend = "reserved"
        node.parent.name = "size"
        return "{%(0)s.n_rows, %(0)s.n_cols, %(0)s.n_slices}"

    return "size(", ", ", ")"

def Assign_size(node):
    num = node[-1][0].dim == 3 and "2" or "3"
    return "uword _%(0)s [] = %(1)s ;\n"+\
            "%(0)s = urowvec(_%(0)s, " + num + ", false) ;"

def Assigns_size(node):

    val = node[-1][0]
    # multi-assigned size to own line
    if val.cls != "Var":
        val = val.auxiliary()
    val = str(val)

    # suggest some types for matrix
    if len(node)==3:
        node[0].suggest = "int"
        node[1].suggest = "int"

        return "%(0)s = " +val+ ".n_rows ;\n%(1)s = " +val+ ".n_cols ;"


    # suggest some types for cube
    if len(node)==4:

        node[0].suggest = "int"
        node[1].suggest = "int"
        node[2].suggest = "int"

        return  "%(0)s = "+val+".n_rows ;\n"+\
                "%(1)s = "+val+".n_cols ;\n"+\
                "%(2)s = "+val+".n_slices ;"

    raise NotImplementedError


def Get_length(node):
    node.type = "uword"
    node.include("length")

    # array-type uses n_elem
    if node.cls == "Var":
        return "%(0)s.n_elem"

    return "m2cpp::length(%(0)s)"


def Get_min(node):

    # unknown datatype handler
    if not all([n.num for n in node]):
        return "min(", ", ", ")"

    # everything scalar
    if all([(n.dim < 2) for n in node]):
        return "std::min(", ", ", ")"

    node.type = node[0].type

    # single arg
    if len(node) == 1:

        # determine node dimensions
        if node.dim == 2:
            node.dim = 0
        else:
            node.dim = node.dim-1

        return "arma::min(%(0)s)"

    # two args
    if len(node) == 2:
        return "arma::min(%(0)s, %(1)s)"

    # three args
    if len(node) == 3:
        if node[2].dim == 0:

            # assues third arg is int and sets axis
            val = node[2].value
            if val == "1":
                node.dim = 2
                return "arma::min(%(0)s, 1)"
            elif val == "2":
                node.dim = 1
                return "arma::min(%(0)s, 0)"

            node.num = False
            return "arma::min(%(0)s, %(2)s-1)"

    assert False

def Assigns_min(node):
    assert len(node) == 3

    var = node[2][0]

    # non-numerical assignment
    if not var.num:
        return "[", ", ", "] = max(", ") ;"

    node[0].suggest = (0, var.mem)
    node[1].suggest = "int"

    # multi-assignmens on own line
    if var.cls != "Var":
        var = var.auxiliary()
    var = str(var)

    return "%(0)s = " + var + ".min(%(1)s) ;"

def Get_max(node):

    # non.numerical input
    if not all([n.num for n in node]):
        return "max(", ", ", ")"

    # everything scalar
    if all([(n.dim<2) for n in node]):
        return "std::max(", ", ", ")"

    node.type = node[0].type

    # number of args is ...
    if len(node) == 1:

        # determine dimensionality
        if node.dim == 2:
            node.dim = 0
        else:
            node.dim = node.dim-1

        return "arma::max(%(0)s)"

    if len(node) == 2:
        return "arma::max(%(0)s, %(1)s)"

    if len(node) == 3:
        if node[2].dim == 0:

            # thrid argument sets axis to take max over
            val = node[2]["value"]
            if val == "1":
                node.dim = 2
                return "arma::max(%(0)s, 1)"
            elif val == "2":
                node.dim = 1
                return "arma::max(%(0)s, 0)"

            node.num = False
            return "arma::max(%(0)s, %(2)s-1)"

    assert False

def Assigns_max(node):
    assert len(node) == 3

    # right hand side of assignment
    var = node[-1]

    # non-numerical input
    if not var.num:
        return "[", ", ", "] = max(", ") ;"

    node[0].suggest = (0, var.mem)
    node[1].suggest = "int"

    # multi-assign max on own line
    if var.cls != "Var":
        var = var.auxiliary()
    var = str(var)

    return "%(0)s = " + var + ".max(%(1)s) ;"

Var_eye = "1"

def Get_eye(node):

    node.type = "mat"

    # not numerical input
    if not node[0].num:
        return "eye(", ", ", ")"

    # single argument constructor
    if len(node) == 1:
        if node[0].dim == 0:
            return "arma::eye<mat>(%(0)s, %(0)s)"
        return "arma::eye<mat>(%(0)s(0), %(0)s(1))"

    # double arguments
    if len(node) == 2:
        return "arma::eye<mat>(%(0)s, %(1)s)"

    raise NotImplementedError

def Get_transpose(node):
    """Simple transpose
    """

    # colvec -> rowvec 
    if node[0].dim == 1:
        node.type = (2, node[0].mem)

    # rowvec -> colvec
    elif node[0].dim == 2:
        node.type = (1, node[0].mem)

    else:
        node.type = node[0].type

    return "arma::strans(%(0)s)"

def Get_ctranspose(node):
    """Complex transpose
    """

    # colvec -> rowvec 
    if node[0].dim == 1:
        node.type = (2, node[0].mem)

    # rowvec -> colvec
    elif node[0].dim == 2:
        node.type = (1, node[0].mem)

    else:
        node.type = node[0].type

    return "arma::trans(%(0)s)"


def Get_flipud(node):
    return "arma::flipud(%(0)s)"


def Get_ones(node):

    node.type = "uword"
    dim, mem = node.suggest_datatype()

    # set memory type
    if not (mem is None):
        node.mem = mem
        if dim in (1,2):
            node.dim = dim
    else:
        node.mem = 3

    # reset to uword if arg to array-node
    if node.group.cls in ("Get", "Cget", "Fget", "Nget", "Sget", "Set", "Cset",
            "Fset", "Nset", "Sset"):
        node.mem = 0

    # not vector
    if dim not in (1,2):

        # single arg creates colvec
        if len(node) == 1:
            node.dim = 2

        # double argument creates colvec/rowvec/matrix after context
        elif len(node) == 2:
            if node[0].cls == "Int" and node[0].value == "1":
                node.dim = 2
                return "arma::ones<%(type)s>(%(1)s)"
            elif node[1].cls == "Int" and node[1].value == "1":
                node.dim = 1
                return "arma::ones<%(type)s>(%(0)s)"
            else:
                node.dim = 3

        # triple arg create cube
        if len(node) == 3:
            node.dim = 4

    # arg input is vector
    if node[0].num and node[0].dim in (1,2):

        # non-trivial variables moved out to own line
        if node[0].cls != "Var":
            node[0].auxiliary()

        # indexing arg as input
        if node.dim in (1,2):
            return "arma::ones<%(type)s>(%(0)s(0))"
        if node.dim == 3:
            return "arma::ones<%(type)s>(%(0)s(0), %(0)s(1))"
        if node.dim == 4:
            return "arma::ones<%(type)s>(%(0)s(0), %(0)s(1), %(0)s(2))"

    # two args where one vector and other "1" handled specially
    elif len(node) == 2 and node.dim in (1,2):
        if node[0].cls == "Int" and node[0].value == "1":
            return "arma::ones<%(type)s>(%(1)s)"
        if node[1].cls == "Int" and node[1].value == "1":
            return "arma::ones<%(type)s>(%(0)s)"

    return "arma::ones<%(type)s>(", ", ", ")"


def Get_zeros(node):

    node.type = "uword"
    dim, mem = node.suggest_datatype()

    # set memory type
    if not (mem is None):
        node.mem = mem
        if dim in (1,2):
            node.dim = dim
    else:
        node.mem = 3

    # reset to uword if arg of array-node
    if node.group.cls in ("Get", "Cget", "Fget", "Nget", "Sget", "Set", "Cset",
            "Fset", "Nset", "Sset"):
        node.mem = 0

    # not vector
    if dim not in (1,2):

        # single arg creates colvec
        if len(node) == 1:
            node.dim = 2

        # double argument creates colvec/rowvec/matrix depending on context
        elif len(node) == 2:
            if node[0].cls == "Int" and node[0].value == "1":
                node.dim = 2
                return "arma::zeros<%(type)s>(%(1)s)"
            elif node[1].cls == "Int" and node[1].value == "1":
                node.dim = 1
                return "arma::zeros<%(type)s>(%(0)s)"
            else:
                node.dim = 3

        # triple arg create cube
        if len(node) == 3:
            node.dim = 4

    # arg input is vector
    if node[0].num and node[0].dim in (1,2):

        # non-trivial variables moved out to own line
        if node[0].cls != "Var":
            node[0].auxiliary()

        # indexing arg as input if vector
        if node.dim in (1,2):
            return "arma::zeros<%(type)s>(%(0)s(0))"
        if node.dim == 3:
            return "arma::zeros<%(type)s>(%(0)s(0), %(0)s(1))"
        if node.dim == 4:
            return "arma::zeros<%(type)s>(%(0)s(0), %(0)s(1), %(0)s(2))"

    # two args where one vector and other "1" handled specially
    elif len(node) == 2 and node.dim in (1,2):
        if node[0].cls == "Int" and node[0].value == "1":
            return "arma::zeros<%(type)s>(%(1)s)"
        if node[1].cls == "Int" and node[1].value == "1":
            return "arma::zeros<%(type)s>(%(0)s)"

    return "arma::zeros<%(type)s>(", ", ", ")"


def Get_round(node):

    assert len(node)<3

    # number of decimals to retain
    if len(node) == 2:
        decimals = str(node[1])
    else:
        decimals = "0"

    # int and uword do not have decimals
    if node[0].mem < 2:
        return "%(0)s"

    # hack to cut-off for scalars
    if node[0].dim == 0:
        node.include("math")
        if decimals == "0":
            return "std::round(%(0)s)"
        return "std::round(%(0)s*std::pow(10, %(1)s))*std::pow(10, -%(1)s)"

    # hack for cut-off for array-type
    if decimals == "0":
        return "arma::round(%(0)s)"
    return "arma::round(%(0)s*std::pow(10, %(1)s))*std::pow(10, -%(1)s)"


def Var_rand(node):
    node.type = "float"
    return "arma::randu(1)"


def Get_rand(node):

    type = node[0].type

    # unknown input
    if type == "TYPE":
        return "arma::randu<TYPE>(", ", ", ")"

    # one arg -> vec
    if len(node) == 1:
        node.type = "vec"
        return "arma::randu<vec>(%(0)s)"

    # two args -> mat
    elif len(node) == 2:
        node.type = "mat"
        return "arma::randu<mat>(%(0)s, %(1)s)"

    # three args -> cube
    elif len(node) == 3:
        node.type = "cube"
        return "arma::randu<cube>(%(0)s, %(1)s, %(2)s)"

    else:
        raise NotImplementedError


def Get_floor(node):

    # unknown input
    if node.type == "TYPE":
        return "floor(", ", ", ")"

    # returns int
    if node[0].mem > 1:
        node.type = (node[0].dim, 1)

    # scalar done through std
    if node[0].dim == 0:
        return "std::floor(%(0)s)"

    return "arma::floor(%(0)s)"


def Var_clear(node):
    return "// clear"

def Get_clear(node):
    return "// clear(", ", ", ")"

def Var_close(node):
    return "// close"

def Get_close(node):
    return "// close(", ", ", ")"

def Var_plot(node):
    return "// plot"

def Get_plot(node):
    return "// plot(", ", ", ")"

def Var_hold(node):
    return "// hold"

def Get_hold(node):
    return "// hold(", ", ", ")"

def Get__conv_to(node):
    return "conv_to<%(type)s>::from(%(0)s)"

def Get__reshape(node):
    return "%(value)s(", ", ", ")"

def Get_nextpow2(node):
    node.include("nextpow2")
    return "m2cpp::nextpow2(", ", ", ")"

def Get_fft(node):

    node.type = node[0].type
    if node.mem == 4:
        node.mem = 3

    # arma & matlab fft same for n_args in (1,2)
    if len(node) in (1,2):
        return "arma::fft(", ", ", ")"

    elif len(node) == 3:

        if node[0].dim in (1,2):
            return "arma::fft(%(0)s, %(1)s)"

        if node[1].cls == "Matrix":
            node.include("fft")
            return "m2cpp::fft<" + node[0].type + ">(%(0)s, %(2)s)"
        else:
            node.include("fftn")
            return "m2cpp::fft<" + node[0].type + ">(", ", ", ")"

    else:
        node.error("Number of args in 'fft' should be between 1 and 3")

    return "arma::fft(", ", ", ")"

def Get_ifft(node):

    node.type = node[0].type

    # unknown input
    if not node.num:
        return "ifft(", ", ", ")"

    node.mem = 4

    if len(node) == 1:
        return "arma::ifft(%(0)s)"

    elif len(node) == 2:
        return "arma::ifft(%(0)s, %(1)s)"

    elif len(node) == 3:

        if node[0].dim in (1,2):
            return "arma::ifft(%(0)s, %(1)s)"

        if node[1].cls == "Matrix":
            node.include("ifft")
            return "m2cpp::ifft<" + node[0].type + ">(%(0)s, %(2)s)"
        else:
            node.include("ifftn")
            return "m2cpp::ifft<" + node[0].type + ">(", ", ", ")"

    else:
        node.error("Number of args in 'ifft' should be between 1 and 3")

    if node[0].mem != 4:
        node.warning("Argument datatype of 'ifft' should be complex")

    return "arma::ifft(", ", ", ")"


def Get_hankel(node):

    node.include("hankel")
    return "m2cpp::hankel(", ", ", ")"

def Get_interp1(node):
    return "arma::interp1(", ", ", ")" 

def Get_linspace(node):
    node.type = "rowvec"
    return "arma::linspace<%(type)s>(", ", ", ")"


def Get_sum(node):

    arg = node[0]

    # unknown input
    if not arg.num or arg.dim == 0:
        node.error("sum over non-array")
        return "sum(", ", ", ")"

    node.type = arg.type

    # determine output dimensions
    if arg.dim == 2:
        dim = 0
    elif arg.dim == 3:
        # sum along an axis
        if len(node) == 2 and node[1].cls == "Int" and node[1].value == "2":
            dim = 1
        else:
            dim = 2
    else:
        dim = arg.dim-1
    node.dim = dim

    return "arma::sum(", ", ", "-1)"


def Get_conj(node):
    return "arma::conj(", ", ", ")"

def Get_imag(node):
    return "arma::imag(", ", ", ")"

def Get_real(node):
    arg = node[0]
    # output always real
    if arg.num and arg.mem == 4:
        node.type = arg.type
        node.mem = 3
    return "arma::real(", ", ", ")"

def Var_tic(node):
    return Get_tic(node)

def Get_tic(node):
    node.wall_clock()
    node.type = "string"
    return "_timer.tic()"

def Var_toc(node):
    return Get_toc(node)

def Get_toc(node):
    node.wall_clock()
    node.type = "string"
    if node.parent.cls != "Statement":
        return "_time.toc()"
    return 'cout << "Ellapsed time = " << _timer.toc() << endl'

def Get_diag(node):
    return "diagmat(", ", ", ")"