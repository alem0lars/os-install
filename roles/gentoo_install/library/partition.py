#!/usr/bin/python
# -*- coding: utf-8 -*-

DOCUMENTATION = '''
---
module: partition
short_description: Create a new partition
author:
    - "Alessandro Molari"
'''

EXAMPLES = '''
# Create a partition
- name: Create the UEFI partition
  partition:
    name: UEFI
    disk: /dev/sda
    fs: fat32
    end: 512MiB
    flags:
      - boot

# Create partitions defined in the variable `partitions`
- name: Create partitions
  partition:
    name: "{{ item.name }}"
    disk: "{{ item.disk }}"
    fs: "{{ item.fs }}"
    end: "{{ item.end }}"
    flags: "{{ item.flags | default(omit) }}"
  with_items: "{{ partitions }}"
'''

# ------------------------------------------------------------------------------
# IMPORTS ----------------------------------------------------------------------

import os, re

# ------------------------------------------------------------------------------
# GLOBALS ----------------------------------------------------------------------

AVAILABLE_UNITS = ['s', 'B', 'kB', 'MB', 'GB', 'TB', 'compact', 'cyl', 'chs',
                   '%', 'kiB', 'MiB', 'GiB', 'TiB']

# ------------------------------------------------------------------------------
# UTILITIES --------------------------------------------------------------------

fail = lambda x: None # Initialized by the main() function.
run_command = lambda *args, **kwargs: None

def list_get(l, idx, default=None):
    try:
        return l[idx]
    except IndexError:
        return default

# ------------------------------------------------------------------------------
# LOGIC ------------------------------------------------------------------------

class StorageSize(object):
    def __init__(self, value, unit):
        self.value = value
        self.unit = unit

    @classmethod
    def fromstr(cls, size):
        md = re.match(r'([.\d]+)\s*([^\s]+)', size)
        if md:
            value = md.group(1)
            unit = md.group(2)
            if not unit in AVAILABLE_UNITS:
                fail('Invalid unit {} for size {}'.format(unit, size))
            return cls(value, unit)
        else:
            fail('Invalid size: {}'.format(size))

    def __repr__(self):
        return 'StorageSize(value={}, unit={})'.format(self.value, self.unit)

    def __str__(self):
        return '{value}{unit}'.format(value=self.value, unit=self.unit)

class PartitionManager(object):
    def __init__(self, name, disk, fs, end, flags):
        self._name = name
        self._disk = disk
        self._flags = flags
        self._fs = fs
        self._end = StorageSize.fromstr(end)
        prev_partitions = self.ls()
        self._number = len(prev_partitions) + 1
        if len(prev_partitions) == 0:
            self._start = StorageSize(1, 'MiB') # Initial padding.
        else:
            self._start = prev_partitions[-1]['end']

    def create(self):
        # Create partition.
        self._run_parted_command('mkpart {name} {fs} {start} {end}'.format(
            name=self._name, fs=self._fs, start=self._start, end=self._end))

        # Set flags.
        for flag in self._flags:
            self._run_parted_command('set {number} {flag} on'.format(
                number=self._number, flag=flag))

    def ls(self):
        _, out, err = self._run_parted_command('print')
        lines = filter(None, out.split('\n'))
        header = '^{columns}$'.format(columns=r'\s+'.join(
            ['Number', 'Start', 'End', 'Size', 'File system', 'Name', 'Flags']))
        idxs = [idx for idx, line in enumerate(lines) if re.match(header, line)]
        if len(idxs) != 1:
            fail(msg='Internal error: cannot parse parted print output')
        partitions = []
        for line in lines[idxs[0] + 1:]:
            tokens = filter(None, re.split(r'\s+', line))
            partitions.append(dict(
                number=list_get(tokens, 0),
                start=StorageSize.fromstr(list_get(tokens, 1)),
                end=StorageSize.fromstr(list_get(tokens, 2)),
                size=StorageSize.fromstr(list_get(tokens, 3)),
                fs=list_get(tokens, 4),
                name=list_get(tokens, 5),
                flags=list_get(tokens, 6)
            ))
        return partitions

    def _run_parted_command(self, command):
        with open('/tmp/ansible.log', 'a') as f:
            f.write(command + '\n')
        return run_command(
            'parted -s -a opt ' +
            '{disk}  '.format(disk=self._disk) +
            '{command}'.format(command=command),
            check_rc=True)

# ------------------------------------------------------------------------------
# MAIN FUNCTION ----------------------------------------------------------------

def main():
    argument_spec = dict(
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
            flags=dict(type='list', default=[]))
    module = AnsibleModule(argument_spec=argument_spec)

    global fail, run_command
    fail = lambda msg: module.fail_json(msg=msg)
    run_command = lambda *args, **kwargs: module.run_command(*args, **kwargs)

    partition_manager = PartitionManager(
            module.params['name'], module.params['disk'], module.params['fs'],
            module.params['end'], module.params['flags'])
    partition_manager.create()

    module.exit_json(changed=True, result={},
                     msg='Partition successfully created')

# ------------------------------------------------------------------------------
# ENTRY POINT ------------------------------------------------------------------

from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()
