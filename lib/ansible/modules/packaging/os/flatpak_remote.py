#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2017 John Kwiatkoski
# Copyright: (c) 2018 Alexander Bethke
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
    - When I(state) is set to C(present), I(name) is added as a remote for installing flatpaks.
      When used with I(state=absent) the remote with thet name will be removed.
    required: true
  remote:
    description:
    - When I(state) is set to C(present), I(remote) url is added as a flatpak remote for the
      specified installation C(method).
      When used with I(state=absent), this is not required.
  method:
    description:
    - Determines the type of installation to work on. Can be C(user) or C(system) installations.
    choices: [ user, system ]
    default: system
  executable:
    description:
    - The path to the C(flatpak) executable to use. The default will look for
      the c(flatpak) executable on the path
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

result = dict()

import subprocess
from ansible.module_utils.basic import AnsibleModule


def add_remote(check_mode, binary, name, remote, method):
    """Add a new remote."""
    command = "{0} remote-add --{1} {2} {3}".format(
        binary, method, name, remote)
    _flatpak_command(check_mode, command)


def remove_remote(check_mode, binary, name, method):
    """Remove an existing remote."""
    command = "{0} remote-delete --{1} --force {2} ".format(
        binary, method, name)
    _flatpak_command(check_mode, command)


def check_remote_status(check_mode, binary, name, remote, method):
    """
    Check the remote status.

    returns:
        status, type: int
            The status of the queried remote
            Possible values:
            0 - remote with name exists
            1 - remote with name doesn't exist
    """
    command = "{0} remote-list -d --{1}".format(binary, method)
    output = _flatpak_command(check_mode, command)
    for line in output.splitlines():
        listed_remote = line.split()
        if listed_remote[0] == name:
            return 0
    return 1


def _flatpak_command(check_mode, command):
    global result
    if check_mode:
        # Check if any changes would be made but don't actually make
        # those changes
        result['rc'] = 0
        result['command'] = command
        return ""

    process = subprocess.Popen(
        command.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout_data, stderr_data = process.communicate()
    result['rc'] = process.returncode
    result['command'] = command
    if result['rc'] != 0:
        result['msg'] = "Failed to execute flatpak command"
        result['stdout'] = stdout_data
        result['stderr'] = stderr_data
        raise RuntimeError(stderr_data)
    return stdout_data


def main():
    module = AnsibleModule(
        argument_spec=dict(
            name=dict(type='str', required=True),
            remote=dict(type='str'),
            method=dict(type='str', default='system',
                        choices=['user', 'system']),
            state=dict(type='str', default="present",
                       choices=['absent', 'present']),
            executable=dict(type='str', default="flatpak")
        ),
        # This module supports check mode
        supports_check_mode=True,
    )

    name = module.params['name']
    remote = module.params['remote']
    method = module.params['method']
    state = module.params['state']
    executable = module.params['executable']
    binary = module.get_bin_path(executable, None)
    check_mode = module.check_mode

    # If the binary was not found, warn the user
    if not binary:
        module.warn("Executable '%s' was not found on the system." % executable)
    binary = module.get_bin_path(executable, required=True)

    if remote is None:
        remote = ''

    global result
    result = {
        'changed': False
    }

    try:
        status = check_remote_status(check_mode, binary, name, remote, method)
        if state == 'present':
            if status == 0:
                result['changed'] = False
            else:
                add_remote(check_mode, binary, name, remote, method)
                result['changed'] = True
        else:
            if status == 0:
                remove_remote(check_mode, binary, name, method)
                result['changed'] = True
            else:
                result['changed'] = False
    except RuntimeError:
        module.fail_json(**result)

    module.exit_json(**result)


if __name__ == '__main__':
    main()
