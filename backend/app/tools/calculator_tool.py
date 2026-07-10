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
    
    def _eval(node, depth=0):
        if depth > 100:
            raise RecursionError("Expression terlalu kompleks")
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.BinOp):
            return _ALLOWED_OPERATORS[type(node.op)](_eval(node.left, depth + 1), _eval(node.right, depth + 1))
        elif isinstance(node, ast.UnaryOp):
            return _ALLOWED_OPERATORS[type(node.op)](_eval(node.operand, depth + 1))
        else:
            raise TypeError(node)

    try:
        # Parse ekspresi jadi AST, lalu evaluasi node per node (menghindari eval() yang berbahaya)
        tree = ast.parse(expression.strip()[:500], mode='eval').body
        result = _eval(tree)
        
        # Return format dengan presisi wajar
        if isinstance(result, float):
            return f"{result:.4f}".rstrip('0').rstrip('.')
            
        return str(result)
        
    except (SyntaxError, TypeError, KeyError, ZeroDivisionError) as e:
        logger.warning("Kalkulasi gagal untuk '%s': %s", expression, e)
        return "Error: Ekspresi matematika tidak valid."
