

import os
import re
import argparse
import shutil

from mbedtls_test import TestDataParser


"""
Generates code in following structure.

<output dir>/
|-- host_tests/
|   |-- mbedtls_test.py
|   |-- suites/
|   |   |-- *.data files
|   |-- mbedtls/
|   |   |-- <test suite #1>/
|   |   |    |-- main.c
|   |   ...
|   |   |-- <test suite #n>/
|   |   |    |-- main.c
|   |   |
"""


BEGIN_HEADER_REGEX = '/\*\s*BEGIN_HEADER\s*\*/'
END_HEADER_REGEX = '/\*\s*END_HEADER\s*\*/'

BEGIN_DEP_REGEX = 'BEGIN_DEPENDENCIES'
END_DEP_REGEX = 'END_DEPENDENCIES'

BEGIN_CASE_REGEX = '/\*\s*BEGIN_CASE\s*(.*?)\s*\*/'
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
        if dep[0] == '!':
            noT = '!'
            dep = dep[1:]
        else:
            noT = ''
        dep_start += '#if %sdefined %s\n' % (noT, dep)
        dep_end = '#endif /* %s */\n' % dep + dep_end
    return dep_start, dep_end


def gen_deps_one_line(deps):
    """

    :param deps:
    :return:
    """
    defines = []
    for dep in deps:
        if dep[0] == '!':
            noT = '!'
            dep = dep[1:]
        else:
            noT = ''
        defines.append('%sdefined (%s)' % (noT, dep))
    return '#if ' + ' && '.join(defines)


def parse_function_signature(func):
    """
    Parses function signature and gives return type, function name, argument list.

    :param func:
    :return:
    """
    deps = []
    m = re.search(BEGIN_CASE_REGEX, func)
    begin_case_skip_len = len(m.group(0))
    if len(m.group(1)):
        for x in m.group(1).split():
            m = re.match('depends_on:(.*)',x, re.I)
            if m:
                deps += m.group(1).split(':')
    func = func[begin_case_skip_len:].strip()
    m = re.match('void\s+(\w+)\s*\(', func, re.I)
    if not m:
        raise ValueError("Test function should return 'void'\n%s" % func.splitlines()[0])
    name = m.group(1)
    func = func[len(m.group(0)):]
    args_list = func[:func.find(')')].split(',')
    args = []

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

    # Add prefix to function name
    body = body.replace(name, 'test_%s' % name, 1)

    # Add exit label if not present
    if body.find('exit:') == -1:
        s = body.rsplit('}', 1)
        if len(s) == 2:
            body = """
exit:
    ;;
}
""".join(s)

    # Put the body first
    code += body + '\n'
    # Then create the wrapper
    wrapper = '''
void test_{name}_wrapper(Param_t * params){{
    {variable_decl}
    {int_conversions}
    test_{name}({args});
}}
'''
    variable_decl = ''
    int_conv = ''
    params = []
    arg_idx = 0
    for var in args:
        if var == 'int':
            variable_decl += '%s p%d;\n' % (var, arg_idx)
            int_conv += "p%d = *((int *)params[%d].data);\n" % (arg_idx, arg_idx)
            params.append('p%d' % arg_idx)
        elif var == 'char*':
            params.append('(%s)params[%d].data' % (var, arg_idx))
        arg_idx += 1
    #code += wrapper.format(name=name, variable_decl=variable_decl, int_conversions=int_conv, args=', '.join(params))
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
    test_{name}_wrapper(params);
}} else
'''.format(name=name) + dep_end
    return dispatch_code


def get_func_headers(funcs_data):
    """

    :param funcs_data:
    :return:
    """
    begin = find_regex(BEGIN_HEADER_REGEX, funcs_data, False)
    end = find_regex(END_HEADER_REGEX, funcs_data, True)
    return funcs_data[begin:end]


def get_func_deps(funcs_data):
    """
    returns the macros require for the code in functions file.

    :param funcs_data:
    :return:
    """
    begin = find_regex(BEGIN_DEP_REGEX, funcs_data, False)
    end = find_regex(END_DEP_REGEX, funcs_data, True)
    deps = []
    for line in funcs_data[begin:end].splitlines():
        m = re.search('depends_on\:(.*)', line.strip())
        if m:
            deps += [x.strip() for x in m.group(1).split(':')]
    return deps


def generate_wrapper(function, wrapper_name, types, deps, test_data):
    """
    Generate test function wrappers using function signature and test data.

    :param function:
    :param wrapper_name:
    :param types:
    :param deps:
    :param test_data:
    :return:
    """
    wrapper = '''
void {wrapper_name} (){{
{deps_start}
    {variable_decl}
    {fetch_code}
    test_{function}({params});
    {cleanup}
{deps_end}
}}
'''
    if len(deps) > 0:
        deps_code = gen_deps_one_line(deps)
        deps_end = '''
#else
    printf("Test function not supported!");
    test_errors++;
#endif
'''
    else:
        deps_code = ''
        deps_end = ''
    variable_decl = ''
    fetch_code = ''
    params = []
    cleanup = ''
    for arg_idx in range(len(test_data)):
        typ = types[arg_idx]
        val = test_data[arg_idx]
        if typ == 'int':
            if re.match('\d+', val):
                variable_decl += 'int p%d;\n' % arg_idx
                fetch_code += 'p%d = serial_get_int(%d);\n' % (arg_idx, arg_idx)
                params.append('p%d' % arg_idx)
            else:
                params.append(val)
        elif typ == 'char*':
            variable_decl += 'char * p%d;\n' % arg_idx
            fetch_code += 'p%d = serial_alloc_get_string(%d);\n' % (arg_idx, arg_idx)
            params.append('p%d' % arg_idx)
            cleanup += 'free(p%d);\n' % arg_idx
        fetch_code += 'if (test_errors) return;\n'
    return wrapper.format(function=function, deps_start=deps_code, deps_end=deps_end, wrapper_name=wrapper_name,
                          variable_decl=variable_decl, fetch_code=fetch_code, params=', '.join(params),
                          cleanup=cleanup)


def gen_dispatch2(data_file, functions):
    """

    :param data_file:
    :param functions:
    :return:
    """
    parser = TestDataParser()
    parser.parse(data_file)
    tests = parser.get_test_data()

    wrappers = {} # Key: 'unique_id': {'name': <wrapper name>}
    wrapper_code = ''
    dispatch_code = ''

    for test_idx in range(len(tests)):
        test_name, test_func, test_deps, test_data = tests[test_idx]
        func_arg_types, func_deps = functions[test_func]
        assert len(func_arg_types) == len(test_data), "Test data and function argument count mismatch!"

        # inspect args if there are any int constants
        unique_wrapper_id = 'test_' + test_func + '_wrapper'
        has_int_macros = False
        for arg_idx in range(len(test_data)):
            typ = func_arg_types[arg_idx]
            val = test_data[arg_idx]
            if typ == 'int' and not re.match('\d+', val):
                unique_wrapper_id += '_' + '%s' % val
                has_int_macros = True

        if unique_wrapper_id in wrappers:
            wrapper_name = wrappers[unique_wrapper_id]['name']
        else:
            # generate wrapper function
            wrapper_name = 'test_' + test_func + '_wrapper'
            wrapper_name += '_%d' % test_idx if has_int_macros else ''
            wrapper_code += generate_wrapper(test_func, wrapper_name, func_arg_types, func_deps, test_data)
            wrappers[unique_wrapper_id] = {'name': wrapper_name}

        if len(test_deps) > 0:
            deps_code = gen_deps_one_line(test_deps)
            dispatch_code += deps_code + '\n'
        dispatch_code += wrapper_name + ',\n'
        if len(test_deps) > 0:
            dispatch_code += '#else\n'
            dispatch_code += 'test_dependency_not_supported,\n'
            dispatch_code += '#endif\n'
    return wrapper_code, dispatch_code, len(tests)


def get_functions(funcs_data, func_deps, data_file):
    """
    Get functions file

    :param funcs_data:
    :param func_deps:
    :param data_file:
    :return:
    """
    # Read functions
    cursor = funcs_data
    functions_code = ''
    dispatch_code = ''
    func_args = {}

    begin = find_regex(BEGIN_CASE_REGEX, cursor, False)
    end = find_regex(END_CASE_REGEX, cursor, True)
    offset = 0
    while -1 not in (begin, end):
        body = cursor[offset + begin:offset + end]
        name, deps, args = parse_function_signature(body.strip())
        func_args[name] = (args, deps + func_deps)
        functions_code += gen_function(name, deps, args, body)
        # Can we append special wrappers here
        # We need info of special wrappers here
        # But special wrappers need function info before
        #
        #dispatch_code += gen_dispatch(name, deps)

        # Find next function
        offset += end
        begin = find_regex(BEGIN_CASE_REGEX, cursor[offset:], False)
        end = find_regex(END_CASE_REGEX, cursor[offset:], True)

    # Do dispatch here based on the test data

    ifdef, endif = gen_deps(func_deps)
    # create wrapper code for tests that require macro substitution
    # Create function table
    functions_code = ifdef + functions_code + endif
    wrappers_code, dispatch_code, test_count = gen_dispatch2(data_file, func_args)

    return {'functions_code': functions_code, 'dispatch_code': dispatch_code,
            'dispatch_wrappers': wrappers_code, 'test_count': test_count}


def gen_dependency_checks(data_file):
    """
    Generate dependency check code for test dependencies

    :param data_file:
    :return:
    """
    parser = TestDataParser()
    parser.parse(data_file)
    test_deps = parser.get_all_deps()
    test_deps.sort()

    dep_check_block = '''
    if (dep_id == {dep_id}) {{
#if {noT}defined ({macro})
        return DEPENDENCY_SUPPORTED;
#else
        return DEPENDENCY_NOT_SUPPORTED;
#endif
    }} else
'''
    checks = ''
    for dep in set(test_deps):
        if dep[0] == '!':
            noT = '!'
            dep = dep[1:]
        else:
            noT = ''
        checks += dep_check_block.format(noT=noT, macro=dep, dep_id=(test_deps.index(dep) + 1))
    return checks


def gen_mbed_code(funcs_file, data_file, template_file, help_file, suites_dir, c_file):
    """
    Generate mbed-os test code.

    :param funcs_file:
    :param dat  a_file:
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
    with open(funcs_file, 'r') as funcs_f:
        funcs_data = funcs_f.read()
        snippets['function_headers'] = get_func_headers(funcs_data)
        deps = get_func_deps(funcs_data)
        function_attrs = get_functions(funcs_data, deps, data_file)
        snippets['dep_check_code'] = gen_dependency_checks(data_file)
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
        c_file_dir = os.path.dirname(c_file)
        if not os.path.exists(c_file_dir):
            os.makedirs(c_file_dir)
        with open(c_file, 'w') as c_f:
            c_f.write(code)

    pass


def check_cmd():
    """
    Command line parser.

    :return:
    """
    parser = argparse.ArgumentParser(description='Generate code for mbed-os tests.')

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

    parser.add_argument("-o", "--out-dir",
                        dest="out_dir",
                        help="Dir where generated code and scripts are copied",
                        metavar="OUT_DIR",
                        required=True)

    args = parser.parse_args()

    # FIXME since we are working out some paths. better revisit command line arguments
    data_name = os.path.splitext(os.path.basename(args.data_file))[0]
    c_file = os.path.join(args.out_dir, 'mbedtls', data_name, 'main.c')
    gen_mbed_code(args.funcs_file, args.data_file, args.template_file, args.help_file, args.suites_dir, c_file)


if __name__ == "__main__":
    check_cmd()
