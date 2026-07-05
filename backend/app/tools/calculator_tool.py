"""
Calculator Tool — EnterpriseMind AI.

Digunakan untuk melakukan kalkulasi matematis sederhana.
Penting untuk Verifier/Analyzer saat membandingkan angka (misal budget, cuti).

Sifat: READ-ONLY (pure function).
"""

import ast
import logging
import operator

logger = logging.getLogger(__name__)

# Subset operator matematika yang diizinkan (keamanan)
_ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.BitXor: operator.xor,
    ast.USub: operator.neg
}


def calculate(expression: str) -> str:
    """
    Evaluasi ekspresi matematika sederhana secara aman.

    Args:
        expression: String matematika (misal: "12 + 5 * 2").

    Returns:
        String hasil kalkulasi, atau pesan error.
    """
    logger.info("Menghitung ekspresi: %s", expression)
    
    def _eval(node):
        if isinstance(node, ast.Num):  # Angka statis (python < 3.8)
            return node.n
        elif isinstance(node, ast.Constant):  # Angka statis (python >= 3.8)
            return node.value
        elif isinstance(node, ast.BinOp):  # Operasi binary (a + b)
            return _ALLOWED_OPERATORS[type(node.op)](_eval(node.left), _eval(node.right))
        elif isinstance(node, ast.UnaryOp):  # Unary op (-a)
            return _ALLOWED_OPERATORS[type(node.op)](_eval(node.operand))
        else:
            raise TypeError(node)

    try:
        # Parse ekspresi jadi AST, lalu evaluasi node per node (menghindari eval() yang berbahaya)
        tree = ast.parse(expression, mode='eval').body
        result = _eval(tree)
        
        # Return format dengan presisi wajar
        if isinstance(result, float):
            return f"{result:.4f}".rstrip('0').rstrip('.')
            
        return str(result)
        
    except (SyntaxError, TypeError, KeyError, ZeroDivisionError) as e:
        logger.warning("Kalkulasi gagal untuk '%s': %s", expression, e)
        return "Error: Ekspresi matematika tidak valid."
