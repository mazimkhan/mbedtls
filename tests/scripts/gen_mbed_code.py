import os
import re
import argparse


BEGIN_CASE_REGEX = '/\*\s*BEGIN_CASE\s*(.*)\s*\*/'
END_CASE_REGEX = '/\*\s*END_CASE\s*\*/'


def find_regex(rg, str, after):
    """
    Find position of a regular expression.

    :param rg:
    :param str:
    :param after: Boolean to tell skip over found regex
    :return:
    """
    m = re.search(rg, str)
    if m:
        exact = m.group(0)
        return str.find(exact) + (len(exact) if after else 0)
    return -1


def gen_deps(deps):
    """
    Generates depedency i.e. if def and endif code
    :param deps:
    :return:
    """
    dep_start = ''
    dep_end = ''
    for dep in deps:
        dep_start += '#if defined %s\n' % dep
        dep_end += '#endif /* %s */\n' % dep
    return dep_start, dep_end


def parse_function_signature(func):
    """
    Parses function signature and gives return type, function name, argument list.

    :param func:
    :return:
    """
    deps = []
    #print "[%s]" % func
    m = re.search(BEGIN_CASE_REGEX, func)
    begin_case_skip_len = len(m.group(0))
    if len(m.group(1)):
        for x in m.group(1).split():
            m = re.match('depends_on:(\w+)',x, re.I)
            if m:
                deps.append(m.group(1))
    func = func[begin_case_skip_len:].strip()
    m = re.match('void\s+(\w+)\s*\(', func, re.I)
    if not m:
        raise ValueError("Test function should return 'void'\n%s" % func.splitlines()[0])
    name = m.group(1)
    func = func[len(m.group(0)):]
    args_list = func[:func.find(')')].split(',')
    args = []

    print name
    for arg in args_list:
        arg = arg.strip()
        if arg == '':
            continue
        if re.match('int\s+.*', arg.strip()):
            args.append('int')
        elif re.match('char\s*\*\s*.*', arg.strip()):
            args.append('char*')
        else:
            raise ValueError("Test function arguments can only be 'int' or 'char *'\n%s(%s)" %
                             (name, ', '.join(args_list)))
    return name, deps, args


def gen_function(name, deps, args, body):
    """
    Creates test function code

    :param name:
    :param deps:
    :param args:
    :param body:
    :return:
    """
    # Put deps hash defs
    code, dep_end = gen_deps(deps)

    # Put the body first
    code += body
    # Then create the wrapper
    wrapper = '''
void {name}_wrapper(){{
    char key[5];
    char int_str[12];
    {variable_decl}
    {fetch_args_code}
    {name}({args});
}}
'''
    variable_decl = ''
    fetch_args_code = ''
    params = []
    arg_idx = 0
    for var in args:
        if var == 'int':
            variable_decl += '%s p%d;\n' % (var, arg_idx)
            fetch_args_code += 'greentea_parse_kv_c(key, int_str, 5, sizeof(int_str));\n'
        elif var == 'char*':
            variable_decl += 'char p%d[100];\n' % arg_idx
            fetch_args_code += 'greentea_parse_kv_c(key, p%d, 5, sizeof(p%d));\n' % (arg_idx, arg_idx)
        params.append('p%d' % arg_idx)
        arg_idx += 1
    code += wrapper.format(name=name, variable_decl=variable_decl, fetch_args_code=fetch_args_code, args=', '.join(params))
    # Put deps endif s
    code += dep_end

    return code


def gen_dispatch(name, deps):
    """
    Generates dispatch condition for the functions.

    :param name:
    :param deps:
    :return:
    """
    dispatch_code, dep_end = gen_deps(deps)

    dispatch_code += '''
if (strcmp(func_name, "{name}") == 0){{
    {name}_wrapper();
}} else
'''.format(name=name) + dep_end
    return dispatch_code


def get_functions(funcs_f, data_f):
    """
    Get functions file

    :param funcs_f:
    :param data_f:
    :return:
    """
    # Read functions
    funcs = funcs_f.read()
    cursor = funcs
    functions_code = ''
    dispatch_code = ''

    begin = find_regex(BEGIN_CASE_REGEX, cursor, False)
    end = find_regex(END_CASE_REGEX, cursor, True)
    offset = 0
    while -1 not in (begin, end):
        body = cursor[offset + begin:offset + end]
        name, deps, args = parse_function_signature(body.strip())
        functions_code += gen_function(name, deps, args, body)
        dispatch_code += gen_dispatch(name, deps)

        # Find next function
        offset += end
        begin = find_regex(BEGIN_CASE_REGEX, cursor[offset:], False)
        end = find_regex(END_CASE_REGEX, cursor[offset:], True)

    # get function code
    # Get argument
    # generate dispatch code
    # find hex arguments
    # remove hexify code
    # create wrapper code

    return {'functions_code':functions_code, 'dispatch_code':dispatch_code}


def gen_mbed_code(funcs_file, data_file, template_file, help_file, suites_dir, c_file):
    """
    Generate mbed-os test code.

    :param funcs_file:
    :param data_file:
    :param template_file:
    :param help_file:
    :param suites_dir:
    :param c_file:
    :return:
    """
    for name, path in [('Functions file', funcs_file),
                       ('Data file', data_file),
                       ('Template file', template_file),
                       ('Help code file', help_file),
                       ('Suites dir', suites_dir)]:
        if not os.path.exists(path):
            raise IOError ("ERROR: %s [%s] not found!" % (name, path))

    snippets = {}

    # Read helpers
    with open(help_file, 'r') as help_f:
        help_code = help_f.read()
        snippets['test_common_helper_file'] = help_file
        snippets['test_common_helpers']= help_code

    # Function code
    with open(funcs_file, 'r') as funcs_f, open(data_file, 'r') as data_f:
        function_attrs = get_functions(funcs_f, data_f)
        snippets.update(function_attrs)

    snippets['test_file'] = c_file
    snippets['test_main_file'] = template_file
    snippets['test_case_file'] = funcs_file
    snippets['test_case_data_file'] = data_file
    # Read Template
    # Add functions
    #
    with open(template_file, 'r') as template_f:
        template = template_f.read()
        code = template.format(**snippets)
        with open(c_file, 'w') as c_f:
            c_f.write(code)

    pass


def check_cmd():
    """
    Command line parser.

    :return:
    """
    parser = argparse.ArgumentParser(description="Generate code for mbed-os tests.")

    parser.add_argument("-f", "--functions-file",
                        dest="funcs_file",
                        help="Functions file",
                        metavar="FUNCTIONS",
                        required=True)

    parser.add_argument("-d", "--data-file",
                        dest="data_file",
                        help="Data file",
                        metavar="DATA",
                        required=True)

    parser.add_argument("-t", "--template-file",
                        dest="template_file",
                        help="Template file",
                        metavar="TEMPLATE",
                        required=True)

    parser.add_argument("-s", "--suites-dir",
                        dest="suites_dir",
                        help="Suites dir",
                        metavar="SUITES",
                        required=True)

    parser.add_argument("--help-file",
                        dest="help_file",
                        help="Help file",
                        metavar="HELPER",
                        required=True)

    parser.add_argument("-c", "--c-file",
                        dest="c_file",
                        help="Output C file",
                        metavar="C_FILE",
                        required=True)

    args = parser.parse_args()

    gen_mbed_code(args.funcs_file, args.data_file, args.template_file, args.help_file, args.suites_dir, args.c_file)


if __name__ == "__main__":
    check_cmd()
