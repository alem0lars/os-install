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
    r'(.+)' + '\n' +                                 # before
    REGEXP_SEP_LINE + '\n' +                         # .. begin (1/2) ..
    r'[#]\s*COMMONS\s*\(generated\)\s*[-]*' + '\n' + # .. begin (2/2) ..
    r'^((?!' + REGEXP_SEP_LINE + ').)*$' + '\n' +    # .. body ..
    REGEXP_SEP_LINE + '\n' +                         # .. end ..
    r'(.+)',                                         # after
    flags = re.IGNORECASE | re.MULTILINE | re.DOTALL)

BEGIN_REPL = '\\1\n{first_line}\n{second_line}\n\n'.format(
             first_line='# '.ljust(80, '-'),
             second_line='# COMMONS (generated) '.ljust(80, '-'))

END_REPL = '\n{line}\n\\3'.format(line='# '.ljust(80, '-'))

# ------------------------------------------------------------------------------
# TASKS ------------------------------------------------------------------------

@invoke.task
def bundle_commons():
    '''Bundle `commons` inside the roles libraries (python files).
    '''
    for file_path in glob.glob('*/*/library/*.py'):
        with open(file_path, 'r') as file:
            file_content = file.read()

        if REGEXP.match(file_content):
            print('-> Performing bundle of `commons` in `{file}`.'.format(
                file=file_path))

            commons_content = ''
            for common in commons.COMMONS:
                commons_content += ''.join(inspect.getsourcelines(common)[0])

            replacement  = '{begin}{content}{end}'.format(
                begin=BEGIN_REPL, content=commons_content, end=END_REPL)
            file_content = REGEXP.sub(replacement, file_content)

            with open(file_path, 'w') as file:
                file.write(file_content)

@invoke.task
def test_gentoo_install():
    '''Test the role: `gentoo_install`.
    '''
    command = 'ansible-playbook -i inventories/test site.yml -v -e install=true'
    invoke.run(command, pty=True)
