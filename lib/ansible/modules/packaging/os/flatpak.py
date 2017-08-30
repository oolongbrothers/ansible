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
module: flatpak
version_added: "2.4"
requirements:
    - flatpak
author:
    - John Kwiatkoski (@jaykayy)
short_description: Install and remove flatpaks
description:
    - The flatpak module allows users to manage installation and removal of flatpaks.
options:
  name:
    description:
      - When I(state) is set to C(present), I(name) is best used as `http(s)` url format.
        When set to C(absent) the same `http(s)` will try to remove it using the
        name of the flatpakref. However, there is no naming standard between
        names of flatpakrefs and what the reverse DNS name of the installed flatpak
        will be. Given that, it is best to use the http(s) url for I(state=present)
        and the reverse DNS I(state=absent). Alternatively reverse dns format can optimally
        be used with I(state=absent), ex. I(name=org.gnome.gedit).
    required: true
  remote:
    description:
      - The flatpak I(remote) repo to be used in the flatpak operation.
  state:
    description:
      - Set to C(present) will install the flatpak and/or I(remote).
        Set to C(absent) will remove the flatpak and/or I(remote).
    default: present
    choices: [ absent, present ]
'''
EXAMPLES = '''
 - name: Install the spotify flatpak
   flatpak:
    name:  https://s3.amazonaws.com/alexlarsson/spotify-repo/spotify.flatpakref
    state: present

 - name: Add the gnome remote andd install gedit flatpak
   flatpak:
    name: https://git.gnome.org/browse/gnome-apps-nightly/plain/gedit.flatpakref
    remote: https://sdk.gnome.org/gnome-apps.flatpakrepo
    state: absent

 - name: Remove the gedit flatpak and remote
   flatpak:
    name: org.gnome.gedit
    remote: https://sdk.gnome.org/gnome-apps.flatpakrepo
    state: absent

 - name: Remove the gedit package
   flatpak:
    name: org.gnome.gedit
    state: absent
'''
RETURN = '''
reason:
    description: On failure, the output for the failure
    returned: failed
    type: string
    sample: error while installing...
name:
    description: Name of flatpak given for the operation
    returned: always
    type: string
    sample: https://git.gnome.org/.../gnome-apps/gedit.flatpakref
remote:
    description: Remote of flatpak given for the operation
    returned: always
    type: string
    sample: https://sdk.gnome.org/gnome-apps.flatpakrepo
'''


def install_flat(binary, flat, module):
    if module.check_mode:
        # Check if any changes would be made but don't actually make
        # those changes
        module.exit_json(changed=True)

    command = "{} install -y --from {}".format(binary, flat)

    output = flatpak_command(command)
    if 'error' in output and 'already installed' not in output:
        return 1, output

    return 0, output


def uninstall_flat(binary, flat, module):
    # This is a difficult function because it seems there
    # is no naming convention for the flatpakref to what
    # the installed flatpak will be named.
    command = "{} list --app".format(binary)
    process = subprocess.Popen(command.split(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    process.wait()
    if module.check_mode:
        # Check if any changes would be made but don't actually make
        # those changes
        module.exit_json(changed=True)
    for row in process.communicate()[0].split('\n'):
        if parse_flat(flat) in row:
            installed_flat_name = row.split(' ')[0]
    command = "{} uninstall {}".format(binary, installed_flat_name)
    output = flatpak_command(command)
    if 'error' in output and 'not installed' not in output:
        return 1, output

    return 0, output


def parse_remote(remote):
    name = remote.split('/')[-1]
    if '.' not in name:
        return name

    return name.split('.')[0]


def parse_flat(name):
    if 'http://' in name or 'https://' in name:
        common_name = name.split('/')[-1].split('.')[0]
        # common_name = urlparse(name).path.split('/')[-1].split('.')[0]
    else:
        common_name = name

    return common_name


def add_remote(binary, remote, module):
    remote_name = parse_remote(remote)
    if module.check_mode:
        # Check if any changes would be made but don't actually make
        # those changes
        module.exit_json(changed=True)

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


def is_present_flat(binary, name):
    command = "{} list --app".format(binary)
    flat = parse_flat(name).lower()
    output = flatpak_command(command)
    if flat in output.lower():
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
            remote=dict(type='str'),
            state=dict(type='str', default="present", choices=['absent', 'present'])
        ),
        supports_check_mode=True,
    )
    name = module.params['name']
    remote = module.params['remote']
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
                module_changed = True
        if name is not None and not is_present_flat(location, name):
            code, output = install_flat(location, name, module)
            if code == 1:
                module.fail_json(msg="error while installing flatpak {}".format(name), reason=output)
            else:
                module_changed = True
    else:
        if remote is not None and is_present_remote(location, remote):
            code, output = remove_remote(location, remote, module)
            if code == 1:
                module.fail_json(msg="error while adding remote: {}".format(remote), reason=output)
            else:
                module_changed = True
        if name is not None and is_present_flat(location, name):
            code, output = uninstall_flat(location, name, module)
            if code == 1:
                module.fail_json(msg="error while uninstalling flatpak:{}".format(name), reason=output)
            else:
                module_changed = True

    module.exit_json(changed=module_changed)


if __name__ == '__main__':
    main()
