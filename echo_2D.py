from wic.api.pythonapi import Step, Workflow


def echo_2D_literal() -> Workflow:
    echo_lit = Step(clt_path='cwl_adapters/echo_2D_literal.cwl')
    echo_lit.message = [['Hello World 1']]

    steps = [echo_lit]
    filename = 'echo_2D_literal_py'  # .yml
    return Workflow(steps, filename)


def echo_2D_mixed_form() -> Workflow:
    echo_mixed_form = Step(clt_path='cwl_adapters/echo_2D_mixed_form.cwl')
    echo_mixed_form.message = [['Hello World 2']]

    steps = [echo_mixed_form]
    filename = 'echo_2D_mixed_form_py'  # .yml
    return Workflow(steps, filename)


def echo_2D_normal_form() -> Workflow:
    echo_normal_form = Step(clt_path='cwl_adapters/echo_2D_normal_form.cwl')
    echo_normal_form.message = [['Hello World 3']]

    steps = [echo_normal_form]
    filename = 'echo_2D_normal_form_py'  # .yml
    return Workflow(steps, filename)


if __name__ == '__main__':
    normal_form = echo_2D_normal_form()
    normal_form.compile()
    normal_form.run()
    # parses, validates, compiles, runs successfully

    mixed_form = echo_2D_mixed_form()
    # Ok, we're using cwl-utils and Pydantic to 'validate', right??
    mixed_form.compile()
    # And we can even call the .compile() method without error,
    # so it must run, right???
    mixed_form.run()
    # Nope! It fails validation with cwltool!

    # Why??? because
    # CWL-UTILS DOES NOT USE CANONICAL TYPES!
    # UNLIKE CWLTOOL, IT DOES NOT RECURSIVELY PERFORM VALIDATION!
    # nf_type = normal_form.steps[0].inputs[0].inp_type
    # mf_type = mixed_form.steps[0].inputs[0].inp_type
    # print('nf_type', nf_type)
    # print('mf_type', mf_type)
    # print('nf_type == mf_type ???', nf_type == mf_type)
    # print('only if you canonicalize!')

    # Same issue here, except 1 dimension higher.
    literal = echo_2D_literal()
    literal.compile()
    literal.run()

    # Notice however, that there is no problem using the syntactic sugar for 1D arrays, i.e. string[]
