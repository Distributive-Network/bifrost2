def init(function_names):
    """
    Dynamically adds functions to the dcp module.
    
    Args:
        function_names (list of str): List of function names to add.
    """
    import sys
    module = sys.modules[__name__]

    for name in function_names:
        # Create a function that returns True
        func = lambda: True
        # Assign the function to the module with the given name
        setattr(module, name, func)
