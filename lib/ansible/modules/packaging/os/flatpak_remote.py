#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2017 John Kwiatkoski
# Copyright: (c) 2017 Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = r'''
---
module: flatpak_remote
version_added: '2.6'
requirements:
- flatpak
author:
- John Kwiatkoski (@jaykayy)
- Alexander Bethke (@oolongbrothers)
short_description: Manage flatpak repository remotes
description:
- Manage flatpak repository remotes.
options:
  name:
    description:
    - When I(state) is set to C(present), I(name) is added as a remote for installing flatpaks. When used with I(state=absent) the remote will be removed.
    required: true
  remote:
    description:
    - When I(state) is set to C(present), I(remote) url is added to the target as a I(method) installation flatpak.
      When used with I(state=absent), this is not required.
    required: false
  method:
    description:
    - Determines the type of installation to work on. Can be C(user) or C(system) installations.
    choices: [ user, system ]
    required: false
    default: user
  executable:
    description:
    - The path to the C(flatpak) executable to use.
    default: flatpak
  state:
    description:
      - Set to C(present) will install the flatpak remote.
      - Set to C(absent) will remove the flatpak remote.
    choices: [ absent, present ]
    default: present
'''

EXAMPLES = r'''
- name: Add the Gnome flatpak remote to the system installation under the name 'gnome'.
  flatpak_remote:
    name: gnome
    state: present
    remote: https://sdk.gnome.org/gnome-apps.flatpakrepo
    method: system

- name: Remove the Gnome flatpak remote  from the user installation.
  flatpak_remote:
    name: gnome
    state: absent

- name: Add the flathub flatpak repository remote to the user installation.
  flatpak_remote:
    name: flathub
    state: present
    remote:  https://dl.flathub.org/repo/flathub.flatpakrepo
    method: user

- name: Remove the flathub flatpak repository remote from the system installtion.
  flatpak_remote:
    name: flathub
    state: absent
    method: system
'''

RETURN = r'''
reason:
  description: On failure, the output for the failure
  returned: failed
  type: string
  sample: error while installing...
name:
  description: Remote of flatpak given for the operation
  returned: always
  type: string
  sample: https://sdk.gnome.org/gnome-apps.flatpakrepo
'''

import subprocess
from ansible.module_utils.basic import AnsibleModule


# def parse_remote(remote):
#    name = remote.split('/')[-1]
#    if '.' in name:
#        name = name.split('.')[0]
#    return name


def add_remote(module, binary, name, remote, method):
    #    remote_name = parse_remote(remote)
    if module.check_mode:
        # Check if any changes would be made but don't actually make
        # those changes
        module.exit_json(changed=True)
    command = "{0} remote-add --{1} {2} {3}".format(
        binary, method, name, remote)

    output = flatpak_command(command)
    if 'error' in output:
        return 1, output

    return 0, output


def remove_remote(module, binary, name, method):
    #    remote_name = parse_remote(remote)
    if module.check_mode:
        # Check if any changes would be made but don't actually make
        # those changes
        module.exit_json(changed=True)

    command = "{0} remote-delete --{1} --force {2} ".format(
        binary, method, name)
    output = flatpak_command(command)
    if 'error' in output and 'not found' not in output:
        return 1, output

    return 0, output

# Possible outcomes
# 0 - remote name exists with correct url
# 1 - remote name exists but different url
# 2 - remote name doesn't exist


def remote_status(binary, name, remote, method):
    #    remote_name = parse_remote(remote)
    command = "{0} remote-list -d --{1}".format(binary, method)
    output = flatpak_command(command)
    for line in output.split('\n'):
        listed_remote = line.split(' ')
        if listed_remote[0] == name:
            if listed_remote[2] == remote:
                return 0
            return 1
    return 2


def flatpak_command(command):
    process = subprocess.Popen(
        command.split(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = process.communicate()[0]

    return output


def main():
    # This module supports check mode
    module = AnsibleModule(
        argument_spec=dict(
            name=dict(type='str', required=True),
            remote=dict(type='str'),
            method=dict(type='str', default='user',
                        choices=['user', 'system']),
            state=dict(type='str', default="present",
                       choices=['absent', 'present']),
            executable=dict(type='str', default="flatpak")
        ),
        supports_check_mode=True,
    )

    name = module.params['name']
    remote = module.params['remote']
    method = module.params['method']
    state = module.params['state']
    executable = module.params['executable']

    # We want to know if the user provided it or not, so we set default here
    if executable is None:
        executable = 'flatpak'

    binary = module.get_bin_path(executable, None)

    # When executable was provided and binary not found, warn user !
    if module.params['executable'] is not None and not binary:
        module.warn("Executable '%s' is not found on the system." % executable)

    binary = module.get_bin_path(executable, required=True)
    if remote is None:
        remote = ''

    status = remote_status(binary, name, remote, method)
    changed = False
    if state == 'present':
        if status == 0:
            changed = False
        elif status == 1:
            # Found name with wrong url, replacing with desired url.
            remove_remote(module, binary, name, method)
            add_remote(module, binary, name, remote, method)
            changed = True
        else:
            add_remote(module, binary, name, remote, method)
            changed = True
    else:
        if status == 0 or status == 1:
            remove_remote(module, binary, name, method)
            changed = True
        else:
            changed = False

    module.exit_json(changed=changed)


if __name__ == '__main__':
    main()
