#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2017 F5 Networks Inc.
# GNU General Public License v3.0 (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = r'''
---
module: bigip_device_dns
short_description: Manage BIG-IP device DNS settings
description:
  - Manage BIG-IP device DNS settings
version_added: 2.2
options:
  cache:
    description:
      - Specifies whether the system caches DNS lookups or performs the
        operation each time a lookup is needed. Please note that this applies
        only to Access Policy Manager features, such as ACLs, web application
        rewrites, and authentication.
    choices:
       - enabled
       - disabled
       - enable
       - disable
  name_servers:
    description:
      - A list of name servers that the system uses to validate DNS lookups
  search:
    description:
      - A list of domains that the system searches for local domain lookups,
        to resolve local host names.
  ip_version:
    description:
      - Specifies whether the DNS specifies IP addresses using IPv4 or IPv6.
    choices:
      - 4
      - 6
  state:
    description:
      - The state of the variable on the system. When C(present), guarantees
        that an existing variable is set to C(value).
    default: present
    choices:
      - absent
      - present
extends_documentation_fragment: f5
author:
  - Tim Rupp (@caphrim007)
'''

EXAMPLES = r'''
- name: Set the DNS settings on the BIG-IP
  bigip_device_dns:
    name_servers:
      - 208.67.222.222
      - 208.67.220.220
    search:
      - localdomain
      - lab.local
    password: secret
    server: lb.mydomain.com
    user: admin
    validate_certs: no
  delegate_to: localhost
'''

RETURN = r'''
cache:
  description: The new value of the DNS caching
  returned: changed
  type: string
  sample: enabled
name_servers:
  description: List of name servers that were set
  returned: changed
  type: list
  sample: ['192.0.2.10', '172.17.12.10']
search:
  description: List of search domains that were set
  returned: changed
  type: list
  sample: ['192.0.2.10', '172.17.12.10']
ip_version:
  description: IP version that was set that DNS will specify IP addresses in
  returned: changed
  type: int
  sample: 4
warnings:
  description: The list of warnings (if any) generated by module based on arguments
  returned: always
  type: list
  sample: ['...', '...']
'''

from ansible.module_utils.basic import AnsibleModule

try:
    from library.module_utils.network.f5.bigip import HAS_F5SDK
    from library.module_utils.network.f5.bigip import F5Client
    from library.module_utils.network.f5.common import F5ModuleError
    from library.module_utils.network.f5.common import AnsibleF5Parameters
    from library.module_utils.network.f5.common import cleanup_tokens
    from library.module_utils.network.f5.common import f5_argument_spec
    try:
        from library.module_utils.network.f5.common import iControlUnexpectedHTTPError
    except ImportError:
        HAS_F5SDK = False
except ImportError:
    from ansible.module_utils.network.f5.bigip import HAS_F5SDK
    from ansible.module_utils.network.f5.bigip import F5Client
    from ansible.module_utils.network.f5.common import F5ModuleError
    from ansible.module_utils.network.f5.common import AnsibleF5Parameters
    from ansible.module_utils.network.f5.common import cleanup_tokens
    from ansible.module_utils.network.f5.common import f5_argument_spec
    try:
        from ansible.module_utils.network.f5.common import iControlUnexpectedHTTPError
    except ImportError:
        HAS_F5SDK = False


class Parameters(AnsibleF5Parameters):
    api_map = {
        'dhclient.mgmt': 'dhcp',
        'dns.cache': 'cache',
        'nameServers': 'name_servers',
        'include': 'ip_version'
    }

    api_attributes = [
        'nameServers', 'search', 'include'
    ]

    updatables = [
        'cache', 'name_servers', 'search', 'ip_version'
    ]

    returnables = [
        'cache', 'name_servers', 'search', 'ip_version'
    ]

    absentables = [
        'name_servers', 'search'
    ]

    def to_return(self):
        result = {}
        for returnable in self.returnables:
            result[returnable] = getattr(self, returnable)
        result = self._filter_params(result)
        return result

    @property
    def search(self):
        result = []
        if self._values['search'] is None:
            return None
        for server in self._values['search']:
            result.append(str(server))
        return result

    @property
    def name_servers(self):
        result = []
        if self._values['name_servers'] is None:
            return None
        for server in self._values['name_servers']:
            result.append(str(server))
        return result

    @property
    def cache(self):
        if str(self._values['cache']) in ['enabled', 'enable']:
            return 'enable'
        else:
            return 'disable'

    @property
    def dhcp(self):
        valid = ['enable', 'enabled']
        return True if self._values['dhcp'] in valid else False

    @property
    def ip_version(self):
        if self._values['ip_version'] in [6, '6', 'options inet6']:
            return "options inet6"
        elif self._values['ip_version'] in [4, '4', '']:
            return ""
        else:
            return None


class ModuleManager(object):
    def __init__(self, *args, **kwargs):
        self.module = kwargs.get('module', None)
        self.client = kwargs.get('client', None)
        self.want = Parameters(params=self.module.params)
        self.have = None
        self.changes = Parameters()

    def _update_changed_options(self):
        changed = {}
        for key in Parameters.updatables:
            if getattr(self.want, key) is not None:
                attr1 = getattr(self.want, key)
                attr2 = getattr(self.have, key)
                if attr1 != attr2:
                    changed[key] = attr1
        if changed:
            self.changes = Parameters(params=changed)
            return True
        return False

    def exec_module(self):
        changed = False
        result = dict()
        state = self.want.state

        try:
            if state == "present":
                changed = self.update()
            elif state == "absent":
                changed = self.absent()
        except iControlUnexpectedHTTPError as e:
            raise F5ModuleError(str(e))

        changes = self.changes.to_return()
        result.update(**changes)
        result.update(dict(changed=changed))
        return result

    def read_current_from_device(self):
        want_keys = ['dns.cache']
        result = dict()
        dbs = self.client.api.tm.sys.dbs.get_collection()
        for db in dbs:
            if db.name in want_keys:
                result[db.name] = db.value
        dns = self.client.api.tm.sys.dns.load()
        attrs = dns.attrs
        if 'include' not in attrs:
            attrs['include'] = 4
        result.update(attrs)
        return Parameters(params=result)

    def update(self):
        self.have = self.read_current_from_device()
        if not self.should_update():
            return False
        if self.module.check_mode:
            return True
        self.update_on_device()
        return True

    def should_update(self):
        result = self._update_changed_options()
        if result:
            return True
        return False

    def update_on_device(self):
        params = self.want.api_params()
        cache = self.client.api.tm.sys.dbs.db.load(name='dns.cache')
        dns = self.client.api.tm.sys.dns.load()

        # Empty values can be supplied, but you cannot supply the
        # None value, so we check for that specifically
        if self.want.cache is not None:
            cache.update(value=self.want.cache)
        if params:
            dns.update(**params)

    def _absent_changed_options(self):
        changed = {}
        for key in Parameters.absentables:
            if getattr(self.want, key) is not None:
                set_want = set(getattr(self.want, key))
                set_have = set(getattr(self.have, key))
                set_new = set_have - set_want
                if set_new != set_have:
                    changed[key] = list(set_new)
        if changed:
            self.changes = Parameters(params=changed)
            return True
        return False

    def should_absent(self):
        result = self._absent_changed_options()
        if result:
            return True
        return False

    def absent(self):
        self.have = self.read_current_from_device()
        if not self.should_absent():
            return False
        if self.module.check_mode:
            return True
        self.absent_on_device()
        return True

    def absent_on_device(self):
        params = self.changes.api_params()
        resource = self.client.api.tm.sys.dns.load()
        resource.update(**params)


class ArgumentSpec(object):
    def __init__(self):
        self.supports_check_mode = True
        argument_spec = dict(
            cache=dict(
                choices=['disabled', 'enabled', 'disable', 'enable']
            ),
            name_servers=dict(
                type='list'
            ),
            search=dict(
                type='list'
            ),
            ip_version=dict(
                choices=[4, 6],
                type='int'
            ),
            state=dict(
                default='present',
                choices=['absent', 'present']
            )
        )
        self.argument_spec = {}
        self.argument_spec.update(f5_argument_spec)
        self.argument_spec.update(argument_spec)
        self.required_one_of = [
            ['name_servers', 'search', 'ip_version', 'cache']
        ]


def main():
    spec = ArgumentSpec()

    module = AnsibleModule(
        argument_spec=spec.argument_spec,
        supports_check_mode=spec.supports_check_mode,
        required_one_of=spec.required_one_of
    )
    if not HAS_F5SDK:
        module.fail_json(msg="The python f5-sdk module is required")

    try:
        client = F5Client(**module.params)
        mm = ModuleManager(module=module, client=client)
        results = mm.exec_module()
        cleanup_tokens(client)
        module.exit_json(**results)
    except F5ModuleError as ex:
        cleanup_tokens(client)
        module.fail_json(msg=str(ex))


if __name__ == '__main__':
    main()
