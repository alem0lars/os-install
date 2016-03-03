#!/usr/bin/python
# -*- coding: utf-8 -*-

# ------------------------------------------------------------------------------
# IMPORTS ----------------------------------------------------------------------

import collections, os, re, syslog, tempfile

# ------------------------------------------------------------------------------
# MODULE INFORMATIONS ----------------------------------------------------------

DOCUMENTATION = '''
---
module: create_partition
short_description: Create a new partition
author:
    - "Alessandro Molari"
'''

EXAMPLES = '''
# Create a partition
- name: Create the UEFI partition
  create_partition:
    name: UEFI
    disk: /dev/sda
    fs: fat32
    end: 512MiB
    flags:
      - boot

# Create partitions defined in the variable `partitions` and
# define the fact `partitions` shadowing that variable and adding some
# informations.
- name: Create partitions
  create_partition:
    name: "{{ item.name }}"
    disk: "{{ item.disk }}"
    fs: "{{ item.fs }}"
    end: "{{ item.end }}"
    flags: "{{ item.flags | default(omit) }}"
  with_items: "{{ partitions }}"
  register: partitions
- set_fact:
    partitions: "{{ partitions.results | map(attribute='ansible_facts') | list }}"
'''

# ------------------------------------------------------------------------------
# LOGGING ----------------------------------------------------------------------

syslog.openlog('ansible-{name}'.format(name=os.path.basename(__file__)))

def log(msg, level=syslog.LOG_DEBUG):
    """Log to the system logging facility of the target system."""
    if os.name == 'posix': # syslog is unsupported on Windows.
        syslog.syslog(level, msg)

# ------------------------------------------------------------------------------
# GLOBALS ----------------------------------------------------------------------

AVAILABLE_UNITS = ['s', 'B', 'kB', 'MB', 'GB', 'TB', 'compact', 'cyl', 'chs',
                   '%', 'kiB', 'MiB', 'GiB', 'TiB']

# ------------------------------------------------------------------------------
# UTILITIES --------------------------------------------------------------------

def list_get(l, idx, default=None):
    """Save version of `l[idx]`.
    If the index `idx` is outside bounds, `default` is returned instead.
    """
    try:
        return l[idx]
    except IndexError:
        return default

# ------------------------------------------------------------------------------
# DATA STRUCTURES --------------------------------------------------------------

class StorageSize(collections.Mapping):
    def __init__(self, value, unit, fail_handler):
        self._fail_handler = fail_handler
        self.value = value
        self.unit = unit

    @classmethod
    def from_str(cls, size, fail_handler):
        md = re.match(r'([.\d]+)\s*([^\s]+)', size)
        if md:
            value = md.group(1)
            unit = md.group(2)
            if not unit in AVAILABLE_UNITS:
                fail_handler('Invalid unit {} for size {}'.format(unit, size))
            return cls(value, unit, fail_handler)
        else:
            fail_handler('Invalid size: {}'.format(size))

    def to_dict(self):
        return {'value': self.value, 'unit': self.unit}

    def __getitem__(self, key):
        return self.to_dict()[key]

    def __iter__(self):
        return iter(self.to_dict())

    def __len__(self):
        return len(self.to_dict())

    def __repr__(self):
        return 'StorageSize(value={}, unit={})'.format(self.value, self.unit)

    def __str__(self):
        return '{value}{unit}'.format(value=self.value, unit=self.unit)

# ------------------------------------------------------------------------------
# LOGIC ------------------------------------------------------------------------

class PartitionManager(object):
    def __init__(self, name, disk, fs, end, flags, enc_pwd,
                 cmd_runner, fail_handler):
        # Init fields from provided arguments.
        self._name = name
        self._disk = disk
        self._fs = fs
        self._end = StorageSize.from_str(end, fail_handler)
        self._flags = flags
        self._enc_pwd = enc_pwd
        self._cmd_runner = cmd_runner
        self._fail_handler = fail_handler
        # Init other fields.
        prev_partitions = self.ls()
        self._number = len(prev_partitions) + 1
        self._raw_device = '{disk}{number}'.format(
                           disk=self._disk, number=self._number)
        self._device = self._raw_device
        self._raw_name = self._name
        if len(prev_partitions) == 0:
            # Set initial padding of `1 MiB`.
            self._start = StorageSize(1, 'MiB', self._fail_handler)
        else:
            self._start = prev_partitions[-1]['end']

    def ls(self):
        _, out, err = self._run_parted_cmd('print')
        lines = [line for line in out.split('\n') if line]
        columns = ['Number', 'Start', 'End', 'Size', 'File system', 'Name', 'Flags']
        header = '^{columns}$'.format(columns=r'\s+'.join(columns))
        idxs = [idx for idx, line in enumerate(lines) if re.match(header, line)]
        if len(idxs) != 1:
            self._fail_handler(msg='Internal error: cannot parse parted print output')
        partitions = []
        for line in lines[idxs[0] + 1:]:
            tokens = [token for token in re.split(r'\s+', line) if token]
            partitions.append(dict(
                number=list_get(tokens, 0),
                start=StorageSize.from_str(list_get(tokens, 1), self._fail_handler),
                end=StorageSize.from_str(list_get(tokens, 2), self._fail_handler),
                size=StorageSize.from_str(list_get(tokens, 3), self._fail_handler),
                fs=list_get(tokens, 4),
                name=list_get(tokens, 5),
                flags=list_get(tokens, 6)
            ))
        return partitions

    def create(self):
        # Create the physical partition.
        self._run_parted_cmd('mkpart {name} {fs} {start} {end}'.format(
            name=self._name, fs=self._fs, start=self._start, end=self._end))
        # Set the flags.
        for flag in self._flags:
            self._run_parted_cmd('set {number} {flag} on'.format(
                number=self._number, flag=flag))
        # Encrypt.
        if self._enc_pwd:
            pwd_file = tempfile.NamedTemporaryFile(delete=False)
            pwd_file.write(self._enc_pwd)
            pwd_file.close()
            enc_name = 'luks-{name}'.format(name=self._name)

            log('Encrypting device `{}` with name `{}`..'.format(
                self._raw_device, enc_name))
            self._run_crypt_cmd('luksFormat --use-urandom {device} {key_file}'.format(
                                device=self._raw_device, key_file=pwd_file.name))
            self._run_crypt_cmd('luksOpen {device} {name} --key-file {key_file}'.format(
                                device=self._raw_device, name=enc_name,
                                key_file=pwd_file.name))
            self._name   = enc_name
            self._device = "/dev/mapper/{}".format(self._name)

            os.unlink(pwd_file.name)
            log('Encrypt operation completed.')

    def _run_crypt_cmd(self, cmd):
        cmd = 'cryptsetup -q {cmd}'.format(cmd=cmd)
        log('Performing command `{}`'.format(cmd))
        rc, out, err = self._cmd_runner(cmd, check_rc=True)
        return rc, out, err

    def _run_parted_cmd(self, cmd):
        log('Running parted command `{cmd}` on disk `{disk}`.'.format(
            cmd=cmd, disk=self._disk))
        return self._cmd_runner('parted -s -a opt {disk} {cmd}'.format(
                                disk=self._disk, cmd=cmd),
                                check_rc=True)

    def to_dict(self):
        return dict(
            raw_name=self._raw_name,
            name=self._name,
            fs=self._fs,
            start=self._start,
            end=self._end,
            disk=self._disk,
            number=self._number,
            raw_device=self._raw_device,
            device=self._device,
            flags=self._flags,
            encryption=self._enc_pwd)

# ------------------------------------------------------------------------------
# MAIN FUNCTION ----------------------------------------------------------------

def main():
    module = AnsibleModule(argument_spec=dict(
        name=dict(type='str', required=True),
        disk=dict(type='str', required=True),
        fs=dict(choices=['btrfs', 'nilfs2', 'ext4', 'ext3', 'ext2',
                         'fat32', 'fat16', 'hfsx', 'hfs+', 'hfs', 'jfs',
                         'swsusp', 'linux-swap(v1)', 'linux-swap(v0)',
                         'ntfs', 'reiserfs', 'hp-ufs', 'sun-ufs', 'xfs',
                         'apfs2', 'apfs1', 'asfs', 'amufs5', 'amufs4',
                         'amu'],
                 required=True),
        end=dict(type='str', required=True),
        flags=dict(type='list', default=[]),
        encryption=dict(type='str', default=None)))

    fail_handler = lambda msg: module.fail_json(msg=msg)
    cmd_runner   = lambda *args, **kwargs: module.run_command(*args, **kwargs)

    pm = PartitionManager(module.params['name'], module.params['disk'],
                          module.params['fs'], module.params['end'],
                          module.params['flags'], module.params['encryption'],
                          cmd_runner, fail_handler)
    pm.create()

    module.exit_json(changed=True, msg='Partition successfully created.',
                     result=pm.to_dict())

# ------------------------------------------------------------------------------
# ENTRY POINT ------------------------------------------------------------------

from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()

# ------------------------------------------------------------------------------
# vim: set filetype=python :
