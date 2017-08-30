#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2017 Ansible Project GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
import subprocess
#from urlparse import urlparse
from ansible.module_utils.basic import AnsibleModule
__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = '''
---
module: flatpak_repo
version_added: "2.4"
requirements:
    - flatpak
author:
    - John Kwiatkoski (@jaykayy)
short_description: Install and remove flatpaks remotes
description:
    - The flatpak_repo module allows users to manage installation and removal of flatpaks remotes.
options:
  name:
    description:
      - When I(state) is set to C(present), I(name) is added as a remote for installing flatpaks. When used with I(state=absent) the remote will be removed.
    required: true
  state:
    description:
      - Set to C(present) will install the flatpak remote.
        Set to C(absent) will remove the flatpak remote.
    default: present
    choices: [ absent, present ]
'''
EXAMPLES = '''
 - name: Add the gnome remote andd install gedit flatpak
   flatpak:
    name: https://sdk.gnome.org/gnome-apps.flatpakrepo
    state: present

 - name: Remove the gedit flatpak and remote
   flatpak:
    name: https://sdk.gnome.org/gnome-apps.flatpakrepo
    state: absent
'''
RETURN = '''
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
    process = subprocess.Popen(command.split(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = process.communicate()[0]

    return output


def main():
    # This module supports check mode
    module = AnsibleModule(
        argument_spec=dict(
            name=dict(type='str', required=True),
            state=dict(type='str', default="present", choices=['absent', 'present'])
        ),
        supports_check_mode=True,
    )
    remote = module.params['name']
    state = module.params['state']
    module_changed = False
    location = module.get_bin_path('flatpak')
    if location is None:
        module.fail_json(msg="cannot find 'flatpak' binary. Aborting.")

    if state == 'present':
        if remote is not None and not is_present_remote(location, remote):
            code, output = add_remote(location, remote, module)
            if code == 1:
                module.fail_json(msg="error while adding remote: {}".format(remote), reason=output)
    else:
        if remote is not None and is_present_remote(location, remote):
            code, output = remove_remote(location, remote, module)
            if code == 1:
                module.fail_json(msg="error while removing remote: {}".format(remote), reason=output)
            else:
                module_changed = True

    module.exit_json(changed=module_changed)


if __name__ == '__main__':
    main()
