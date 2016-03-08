# ------------------------------------------------------------------------------
# IMPORTS ----------------------------------------------------------------------

import glob
import inspect
import os
import re

import invoke

import commons

# ------------------------------------------------------------------------------
# GLOBALS ----------------------------------------------------------------------

REGEXP_SEP_LINE = r'[#]\s*[-]+'

REGEXP = re.compile(
    r'('                                   + # Begin of 1st capture
    '.*'                                   + # Match before the section start
    REGEXP_SEP_LINE + '\n'                 + # Section start (1st line)
    r'[#]\s*COMMONS\s*\(generated\)\s*'    + # Section start (begin of 2nd line)
    r'(?:<(.+)>\s*)?'                      + # (Optional) 2nd capture
    r'[-]*\n'                              + # Section start (end of 2nd line)
    r')'                                   + # End of 1st capture
    r'^(?:(?!' + REGEXP_SEP_LINE + ').)*$' + # Section body
    r'('                                   + # Begin of 3rd capture
    r'\n' + REGEXP_SEP_LINE + '\n'         + # Section end
    r'.+'                                  + # End of 3rd capture
    r')',                                    # Match after the section end
    flags = re.IGNORECASE | re.MULTILINE | re.DOTALL)

# ------------------------------------------------------------------------------
# TASKS ------------------------------------------------------------------------

@invoke.task
def bundle_commons():
    '''Bundle `commons` inside the roles python files.
    '''
    file_paths = (list(glob.glob('*/*/*_plugins/*.py')) +
                  list(glob.glob('*/*/library/*.py')))
    for file_path in file_paths:
        with open(file_path, 'r') as file:
            file_content = file.read()

        md = REGEXP.match(file_content)
        if md:
            print('-> Performing bundle of `commons` in `{file}`.'.format(
                file=file_path))

            before  = md.group(1)
            allowed = md.group(2)
            after   = md.group(3)

            allowed_commons = []
            if allowed:
                for elem in re.split(r'\s*[,]\s*', allowed):
                    allowed_commons.append(elem)

            commons_content = ''
            for common in commons.COMMONS:
                if (len(allowed_commons) == 0 or
                    common.__name__ in allowed_commons):
                    source_code = ''.join(inspect.getsourcelines(common)[0])
                    commons_content += '\n' + source_code

            replacement  = '{before}{content}{after}'.format(
                before=before, content=commons_content, after=after)
            file_content = REGEXP.sub(replacement, file_content)

            with open(file_path, 'w') as file:
                file.write(file_content)

@invoke.task(bundle_commons,
             help={'role': 'The role name',
                   'verbosity': 'The verbosity level'})
def test(role, ask_pass=False, verbosity=0):
    '''Test a role
    '''
    tests_dir = 'roles/{name}/tests'.format(name=role)
    if not os.path.isdir(tests_dir):
        print('Invalid role name')
        return -1

    command = []
    # 1. Command name
    command.append('ansible-playbook')
    # 2. Inventory
    command.append('-i {tests_dir}/inventory'.format(tests_dir=tests_dir))
    # 3. Entry point
    command.append('site.yml')
    # 4. Tags
    with open('{tests_dir}/tags'.format(tests_dir=tests_dir), 'r') as f:
        tags = ','.join(map(lambda line: line.strip(), f.readlines()))
    command.append('-t {tags}'.format(tags=tags))
    # 5. Verbosity level
    if verbosity > 0:
        command.append('-' + ('v' * verbosity))
    # 6. Ask password
    if ask_pass:
        command.append('--ask-pass')
    command = ' '.join(command)

    print('Running command: `{}`'.format(command))
    invoke.run(command, pty=True)
