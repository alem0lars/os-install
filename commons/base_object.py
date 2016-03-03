class BaseObject(object):
    import syslog, os

    '''Base class for all classes that use AnsibleModule.
    '''
    def __init__(self, module, *params):
        syslog.openlog('ansible-{module}-{name}'.format(
            module=os.path.basename(__file__), name=self.__class__.__name__))
        self._module = module
        self._parse_params(*params)

    def run_command(self, *args, **kwargs):
        if not 'check_rc' in kwargs:
            kwargs['check_rc'] = True
        if len(args) < 1:
            self.fail('Invalid command')
        self.log('Performing command `{}`'.format(args[0]))
        rc, out, err = self._module.run_command(*args, **kwargs)
        if rc != 0:
            self.log('Command `{}` returned invalid status code: `{}`'.format(
                args[0], rc), level=syslog.LOG_WARNING)
        return {'rc': rc, 'out': out, 'err': err}

    def log(self, msg, level=syslog.LOG_DEBUG):
        '''Log to the system logging facility of the target system.'''
        if os.name == 'posix': # syslog is unsupported on Windows.
            syslog.syslog(level, str(msg))

    def fail(self, msg):
        self._module.fail_json(msg=msg)

    def exit(self, changed=True, msg='', result=None):
        self._module.exit_json(changed=changed, msg=msg, result=result)

    def _parse_params(self, *params):
        for param in params:
            if param in self._module.params:
                setattr(self, param, self._module.params[param])
            else:
                setattr(self, param, None)
