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
             help={'verbosity': 'The verbosity level (0 to 3)'})
def test_gentoo_install(verbosity=0):
    '''Test the role: `gentoo_install`.
    '''
    command = ['ansible-playbook']
    command.append('-i inventories/test site.yml')
    if verbosity > 0:
        command.append('-' + ('v' * verbosity))
    command.append('-e install=true')

    invoke.run(' '.join(command), pty=True)
