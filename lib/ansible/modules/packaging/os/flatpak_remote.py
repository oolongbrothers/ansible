#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2017 John Kwiatkoski
# Copyright: (c) 2017 Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import subprocess
#from urlparse import urlparse
from ansible.module_utils.basic import AnsibleModule

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = r'''
---
module: flatpak_remote
version_added: '2.4'
requirements:
- flatpak
author:
- John Kwiatkoski (@jaykayy)
short_description: Manage flatpaks remotes
description:
- Manage flatpak remotes.
options:
  name:
    description:
    - When I(state) is set to C(present), I(name) is added as a remote for installing flatpaks. When used with I(state=absent) the remote will be removed.
    required: true
    aliases: [ remote ]
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
- name: Add the Gnome flatpak remote
  flatpak_remote:
    name: https://sdk.gnome.org/gnome-apps.flatpakrepo
    state: present

- name: Remove the Gnome flatpak remote
  flatpak_remote:
    name: https://sdk.gnome.org/gnome-apps.flatpakrepo
    state: absent
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


def parse_remote(remote):
    name = remote.split('/')[-1]
    if '.' not in name:
        return name

    return name.split('.')[0]

def add_remote(binary, remote, module):
    remote_name = parse_remote(remote)
    if module.check_mode:
        # Check if any changes would be made but don't actually make
        # those changes
        module.exit_json(changed=True)
   # Do I need my is_present_remote function if the binary provides --if-not-exists?
    command = "{} remote-add --if-not-exists {} {}".format(
        binary, remote_name, remote)

    output = flatpak_command(command)
    if 'error' in output:
        return 1, output

    return 0, output


def remove_remote(binary, remote, module):
    remote_name = parse_remote(remote)
    if module.check_mode:
        # Check if any changes would be made but don't actually make
        # those changes
        module.exit_json(changed=True)

    command = "{} remote-delete --force {} ".format(binary, remote_name)
    output = flatpak_command(command)
    if 'error' in output and 'not found' not in output:
        return 1, output

    return 0, output


def is_present_remote(binary, remote):
    remote_name = parse_remote(remote).lower() + " "
    command = "{} remote-list".format(binary)
    output = flatpak_command(command)
    if remote_name in output.lower():
        return True

    return False


def flatpak_command(command):
    process = subprocess.Popen(
        command.split(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = process.communicate()[0]

    return output


def main():
    # This module supports check mode
    module = AnsibleModule(
        argument_spec=dict(
            name=dict(type='str', required=True, aliases=['remote']),
            state=dict(type='str', default="present",
                       choices=['absent', 'present']),
            executable=dict(type='str', default="flatpak")
        ),
        supports_check_mode=True,
    )

    name = module.params['name']
    state = module.params['state']
    executable = module.params['executable']

    # We want to know if the user provided it or not, so we set default here
    if executable is None:
        executable = 'flatpak'

    binary = module.get_bin_path(executable, None)

    # When executable was provided and binary not found, warn user !
    if module.params['executable'] is not None and not binary:
        module.warn("Executable '%s' is not found on the system." % executable)

    if state == 'present and not remote_exists(binary, remote):
        add_remote(module, binary, remote)
    elif state == 'absent and remote_exists(binary, remote):
        remove_remote(module, binary, remote)

    module.exit_json(changed=False)



if __name__ == '__main__':
    main()
