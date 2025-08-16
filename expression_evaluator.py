#!/usr/bin/env python3
"""
Expression Evaluator

This module provides expression evaluation capabilities for binary format handlers.
Supports arithmetic, logical, and comparison operators with proper precedence.
"""

from typing import Any, Dict, List, Union


class ExpressionError(Exception):
    """Custom exception for expression evaluation errors."""
    pass


class ExpressionEvaluator:
    """Evaluates expressions with proper operator precedence and context support."""
    
    def __init__(self, context_getter=None):
        """
        Initialize the expression evaluator.
        
        Args:
            context_getter: Function to get nested values from context (e.g., dot notation)
        """
        self.context_getter = context_getter or self._default_context_getter
    
    def _default_context_getter(self, context: Dict[str, Any], path: str) -> Any:
        """Default implementation for getting nested values."""
        if not isinstance(context, dict) or not path:
            return None
        
        parts = path.split('.')
        value = context
        
        for part in parts:
            if '[' in part and part.endswith(']'):
                field_name = part[:part.index('[')]
                index_part = part[part.index('[')+1:-1]
                
                if isinstance(value, dict) and field_name in value:
                    array_value = value[field_name]
                else:
                    return None
                
                if not isinstance(array_value, list):
                    return None
                
                try:
                    index = int(index_part)
                    value = array_value[index]
                except (ValueError, IndexError):
                    return None
            else:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    return None
        
        return value
    
    def evaluate(self, expression: str, context: Dict[str, Any]) -> Union[bool, float, int]:
        """
        Evaluate an expression against the given context.
        
        Args:
            expression: The expression string to evaluate
            context: Dictionary containing variable values
            
        Returns:
            The result of the expression evaluation
        """
        if not expression:
            return True
        
        expression = expression.strip()
        if not expression:
            return True
        
        try:
            return self._parse_logical_or(expression, context)
        except Exception as e:
            raise ExpressionError(f"Error evaluating expression '{expression}': {e}")
    
    def _parse_logical_or(self, expression: str, context: Dict[str, Any]) -> Union[bool, float]:
        """Parse logical OR expressions (lowest precedence)."""
        parts = self._split_by_operator(expression, '||')
        if len(parts) > 1:
            return any(self._parse_logical_and(part.strip(), context) for part in parts)
        return self._parse_logical_and(expression, context)
    
    def _parse_logical_and(self, expression: str, context: Dict[str, Any]) -> Union[bool, float]:
        """Parse logical AND expressions."""
        parts = self._split_by_operator(expression, '&&')
        if len(parts) > 1:
            return all(self._parse_equality(part.strip(), context) for part in parts)
        return self._parse_equality(expression, context)
    
    def _parse_equality(self, expression: str, context: Dict[str, Any]) -> Union[bool, float]:
        """Parse equality and inequality expressions."""
        for op in ['==', '!=']:
            parts = self._split_by_operator(expression, op)
            if len(parts) == 2:
                left = self._parse_relational(parts[0].strip(), context)
                right = self._parse_relational(parts[1].strip(), context)
                if op == '==':
                    return left == right
                else:  # !=
                    return left != right
        return self._parse_relational(expression, context)
    
    def _parse_relational(self, expression: str, context: Dict[str, Any]) -> Union[bool, float]:
        """Parse relational expressions (<, >, <=, >=)."""
        for op in ['<=', '>=', '<', '>']:
            parts = self._split_by_operator(expression, op)
            if len(parts) == 2:
                left = self._parse_additive(parts[0].strip(), context)
                right = self._parse_additive(parts[1].strip(), context)
                if op == '<':
                    return left < right
                elif op == '>':
                    return left > right
                elif op == '<=':
                    return left <= right
                else:  # >=
                    return left >= right
        return self._parse_additive(expression, context)
    
    def _parse_additive(self, expression: str, context: Dict[str, Any]) -> float:
        """Parse addition and subtraction expressions."""
        # Find the rightmost + or - that's not inside parentheses
        parts = self._split_by_operator(expression, ['+', '-'], right_to_left=True)
        if len(parts) > 1:
            # Reconstruct the operator
            for op in ['+', '-']:
                test_parts = self._split_by_operator(expression, op, right_to_left=True)
                if len(test_parts) == len(parts):
                    left = self._parse_multiplicative(parts[0].strip(), context)
                    right = self._parse_multiplicative(parts[1].strip(), context)
                    if op == '+':
                        return left + right
                    else:  # -
                        return left - right
        return self._parse_multiplicative(expression, context)
    
    def _parse_multiplicative(self, expression: str, context: Dict[str, Any]) -> float:
        """Parse multiplication, division, and modulo expressions."""
        # Find the rightmost *, /, or % that's not inside parentheses
        parts = self._split_by_operator(expression, ['*', '/', '%'], right_to_left=True)
        if len(parts) > 1:
            for op in ['*', '/', '%']:
                test_parts = self._split_by_operator(expression, op, right_to_left=True)
                if len(test_parts) == len(parts):
                    left = self._parse_unary(parts[0].strip(), context)
                    right = self._parse_unary(parts[1].strip(), context)
                    if op == '*':
                        return left * right
                    elif op == '/':
                        if right == 0:
                            raise ExpressionError("Division by zero")
                        return left / right
                    else:  # %
                        if right == 0:
                            raise ExpressionError("Modulo by zero")
                        return left % right
        return self._parse_unary(expression, context)
    
    def _parse_unary(self, expression: str, context: Dict[str, Any]) -> float:
        """Parse unary expressions (!, -, +)."""
        expression = expression.strip()
        if expression.startswith('!'):
            return not self._parse_primary(expression[1:].strip(), context)
        elif expression.startswith('-'):
            return -self._parse_primary(expression[1:].strip(), context)
        elif expression.startswith('+'):
            return self._parse_primary(expression[1:].strip(), context)
        return self._parse_primary(expression, context)
    
    def _parse_primary(self, expression: str, context: Dict[str, Any]) -> Union[bool, float, int]:
        """Parse primary expressions (parentheses, literals, field references)."""
        expression = expression.strip()
        
        # Handle parentheses
        if expression.startswith('(') and expression.endswith(')'):
            # Verify parentheses are balanced
            if self._find_matching_paren(expression, 0) == len(expression) - 1:
                return self._parse_logical_or(expression[1:-1], context)
        
        # Handle boolean literals
        if expression.lower() == 'true':
            return True
        elif expression.lower() == 'false':
            return False
        
        # Handle numeric literals
        try:
            if '.' in expression or 'e' in expression.lower():
                return float(expression)
            else:
                return int(expression)
        except ValueError:
            pass
        
        # Handle field references
        value = self.context_getter(context, expression)
        if value is None:
            raise ExpressionError(f"Field '{expression}' not found in context")
        
        return value
    
    def _split_by_operator(self, expression: str, operators: Union[str, List[str]], 
                          right_to_left: bool = False) -> List[str]:
        """Split expression by operator, respecting parentheses."""
        if isinstance(operators, str):
            operators = [operators]
        
        paren_level = 0
        quote_char = None
        
        # Choose iteration direction
        if right_to_left:
            indices = range(len(expression) - 1, -1, -1)
        else:
            indices = range(len(expression))
        
        for i in indices:
            char = expression[i]
            
            # Handle quotes
            if char in ['"', "'"]:
                if quote_char is None:
                    quote_char = char
                elif quote_char == char:
                    quote_char = None
                continue
            
            if quote_char:
                continue
            
            # Handle parentheses
            if right_to_left:
                if char == ')':
                    paren_level += 1
                elif char == '(':
                    paren_level -= 1
            else:
                if char == '(':
                    paren_level += 1
                elif char == ')':
                    paren_level -= 1
            
            # Check for operators at top level
            if paren_level == 0:
                for op in operators:
                    op_len = len(op)
                    if right_to_left:
                        start_idx = i - op_len + 1
                        if start_idx >= 0 and expression[start_idx:i + 1] == op:
                            return [expression[:start_idx], expression[i + 1:]]
                    else:
                        if expression[i:i + op_len] == op:
                            return [expression[:i], expression[i + op_len:]]
        
        return [expression]
    
    def _find_matching_paren(self, expression: str, start: int) -> int:
        """Find the index of the matching closing parenthesis."""
        if start >= len(expression) or expression[start] != '(':
            return -1
        
        paren_count = 0
        quote_char = None
        
        for i in range(start, len(expression)):
            char = expression[i]
            
            # Handle quotes
            if char in ['"', "'"]:
                if quote_char is None:
                    quote_char = char
                elif quote_char == char:
                    quote_char = None
                continue
            
            if quote_char:
                continue
            
            # Handle parentheses
            if char == '(':
                paren_count += 1
            elif char == ')':
                paren_count -= 1
                if paren_count == 0:
                    return i
        
        return -1


def main():
    """Example usage and tests."""
    # Test context
    test_context = {
        'field1': 10,
        'field2': 5,
        'header': {
            'version': 2,
            'flags': 0x01
        },
        'data': [1, 2, 3, 4],
        'status': 0,
        'retry_count': 1,
        'max_size': 100
    }
    
    evaluator = ExpressionEvaluator()
    
    # Test cases
    test_expressions = [
        ('field1 > 5', True),
        ('field1 + field2 > 10', True),
        ('field1 * field2 == 50', True),
        ('header.version >= 2', True),
        ('data[0] == 1', True),
        ('field1 > 5 && field2 < 10', True),
        ('field1 > 20 || field2 < 10', True),
        ('!(status == 0)', True),
        ('(field1 + field2) * 2 > 25', True),
        ('field1 % 3 == 1', True),
    ]
    
    print("Testing Expression Evaluator:")
    print("=" * 40)
    
    for expr, expected in test_expressions:
        try:
            result = evaluator.evaluate(expr, test_context)
            status = "✓" if result == expected else "✗"
            print(f"{status} {expr} => {result} (expected: {expected})")
        except ExpressionError as e:
            print(f"✗ {expr} => Error: {e}")
    
    print("\nTesting error cases:")
    error_cases = [
        'nonexistent_field > 0',
        'field1 / 0',
        'field1 + (',
    ]
    
    for expr in error_cases:
        try:
            result = evaluator.evaluate(expr, test_context)
            print(f"✗ {expr} => {result} (should have failed)")
        except ExpressionError as e:
            print(f"✓ {expr} => Error: {e}")


if __name__ == "__main__":
    main()
