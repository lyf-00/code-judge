from decimal import Decimal


def truncate_output(s, length=300):
    """Truncate output to avoid memory issues with large outputs"""
    if isinstance(s, str):
        pass
    else:
        s = str(s)
    if len(s) <= length:
        return s
    return s[: length // 2] + "...(truncated) ..." + s[-length // 2 :]


def convert_line_to_decimals(line: str) -> tuple[bool, list[Decimal]]:
    """Convert a line of space-separated values to Decimal objects for precise comparison"""
    try:
        decimal_line = [Decimal(elem) for elem in line.split()]
    except:
        return False, []
    return True, decimal_line


def get_stripped_lines(val: str):
    """Get stripped lines from a string, removing empty lines"""
    val = val.strip()
    return [val_line.strip() for val_line in val.split("\n")]


def try_json_comparison(prediction: str, expected: str) -> tuple[bool, str]:
    """
    Try to compare outputs as JSON objects (for call-based style outputs)
    Returns (is_match, error_message)
    """
    try:
        import json
        pred_obj = json.loads(prediction.strip())
        exp_obj = json.loads(expected.strip())
        
        # Handle tuple to list conversion (common in testing_util)
        if isinstance(pred_obj, list) and len(pred_obj) > 0:
            # Convert any tuples to lists recursively
            def convert_tuples(obj):
                if isinstance(obj, list):
                    return [convert_tuples(item) for item in obj]
                elif isinstance(obj, tuple):
                    return [convert_tuples(item) for item in obj]
                else:
                    return obj
            pred_obj = convert_tuples(pred_obj)
        
        if pred_obj == exp_obj:
            return True, ""
        else:
            return False, f"JSON objects don't match: {truncate_output(str(pred_obj))} != {truncate_output(str(exp_obj))}"
            
    except (json.JSONDecodeError, ValueError):
        return False, "Not valid JSON format"


def enhanced_output_comparison(prediction: str, expected: str, logger) -> tuple[bool, str]:
    """
    Enhanced output comparison using logic from testing_util_new.py
    Returns (is_match, error_message)
    
    This function tries multiple comparison strategies:
    1. Simple string comparison (original logic - prioritized)
    2. JSON comparison (for call-based outputs)
    3. Line-by-line comparison with decimal precision
    """
    
    # Strategy 1: Simple string comparison (original logic - prioritized)
    prediction_simple = prediction.strip()
    expected_simple = expected.strip()
    
    if prediction_simple == expected_simple:
        return True, ""
    
    # Strategy 2: Try JSON comparison (for call-based style outputs)
    json_match, json_error = try_json_comparison(prediction, expected)
    if json_match:
        return True, ""
    
    # Strategy 3: Enhanced line-by-line comparison
    try:
        stripped_prediction_lines = get_stripped_lines(prediction)
        stripped_expected_lines = get_stripped_lines(expected)
        
        # Check if line counts match
        if len(stripped_prediction_lines) != len(stripped_expected_lines):
            return False, f"Wrong answer: mismatched output length. Expected {len(stripped_expected_lines)} lines, got {len(stripped_prediction_lines)} lines"
        
        # Compare line by line
        for line_idx, (pred_line, exp_line) in enumerate(zip(stripped_prediction_lines, stripped_expected_lines)):
            # Case 1: Exact match
            if pred_line == exp_line:
                continue
            
            # Case 2: Try decimal comparison for numeric values
            success_pred, decimal_pred_line = convert_line_to_decimals(pred_line)
            success_exp, decimal_exp_line = convert_line_to_decimals(exp_line)
            
            if success_pred and success_exp:
                # First try exact decimal comparison
                if decimal_pred_line == decimal_exp_line:
                    continue
                
                # If exact comparison fails, try numpy.isclose for floating point tolerance
                try:
                    import numpy as np
                    pred_floats = [float(d) for d in decimal_pred_line]
                    exp_floats = [float(d) for d in decimal_exp_line]
                    
                    if len(pred_floats) == len(exp_floats) and np.allclose(pred_floats, exp_floats):
                        continue
                except (ValueError, ImportError):
                    pass
                
                return False, f"Wrong answer at line {line_idx}: {truncate_output(pred_line)} != {truncate_output(exp_line)}"
            else:
                # If not all numeric, fall back to string comparison
                return False, f"Wrong answer at line {line_idx}: {truncate_output(pred_line)} != {truncate_output(exp_line)}"
        
        # If we get here, all lines matched
        return True, ""
        
    except Exception as e:
        # If enhanced comparison fails, fall back to simple comparison
        if logger:
            logger.warning(f"Enhanced comparison failed, falling back to simple comparison: {e}")
        return prediction_simple == expected_simple, f"Comparison failed: {str(e)}" if prediction_simple != expected_simple else ""
