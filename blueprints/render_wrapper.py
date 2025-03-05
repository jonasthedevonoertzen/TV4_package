"""
Write a file that creates wrapper functions for each of the html templates.
The wrapper functions should accept the same parameters as the original templates, and should render the template with the provided parameters.
The wrapper functions should raise exceptions if the wrong parameters are passed
The wrapper functions should implement checks to ensure that the values of the parameters are correct.
If the values are not correct then the wrapper functions should raise exceptions.
The wrapper function should differentiate between optional and mandatory parameters.
For optional parameters the wrapper function should set the default parameter.
Some templates have different modes which are also parameters.
Then the wrapper function should check that all parameters fit to the current mode.
Additionally, the wrapper functions should implement input validation.
For example, if a template takes a parameter "name" and a parameter "age",
the wrapper function should check that the "name" parameter is a string and the "age" parameter is a positive integer.

The wrapper functions should be well documented and include all documentation for the html templates.
I want to use docstrings but this is not possible in html templates so all documentation for the templates and so on should be included in the documentation for the wrapper functions.
"""