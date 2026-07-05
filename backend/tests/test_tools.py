import pytest
from app.tools.calculator_tool import calculate

def test_calculator_tool():
    assert calculate("5 + 10") == "15"
    assert calculate("20 / 4") == "5"
    assert calculate("2 * 8") == "16"
    assert calculate("10 - 2") == "8"
    assert calculate("10 / 0") == "Error: Ekspresi matematika tidak valid."
    assert calculate("import os; os.system('ls')") == "Error: Ekspresi matematika tidak valid."
