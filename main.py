from pyscript import web, when
import eddsa_threshold

@when("click", "#test-button")
def test_function(event):
    """
    A simple test function.
    """
    
    output_div = web.page["output"]
    output_div.innerText = "Hello from Python!"
    
@when("click", "#reset-button")
def reset_output(event):
    """
    Resets the output div to its initial state.
    """
    
    output_div = web.page["output"]
    output_div.innerText = "Output will appear here."