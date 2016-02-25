#!/usr/bin/python
# -*- coding: utf-8 -*-

# ------------------------------------------------------------------------------
# IMPORTS ----------------------------------------------------------------------

from xml.etree import ElementTree as ET
from sys import version_info as py_version_info
from copy import deepcopy as deep_copy
from json import loads as parse_json

PY3K = py_version_info >= (3, 0)

if PY3K:
    from urllib.request import urlopen as url_open
else:
    from urllib import urlopen as url_open

# ------------------------------------------------------------------------------
# MODULE INFORMATIONS ----------------------------------------------------------

DOCUMENTATION = '''
---
module: select_mirror
short_description: Select a Gentoo mirror
author:
    - "Alessandro Molari"
'''

EXAMPLES = '''
TODO
'''

# ------------------------------------------------------------------------------
# GLOBALS ----------------------------------------------------------------------

MIRRORS_XML = 'http://www.gentoo.org/main/en/mirrors3.xml'

# ------------------------------------------------------------------------------
# MIRROR INFORMATIONS ----------------------------------------------------------

class CountryInfo(object):
    def __init__(self, name, region, neighbors):
        self._name = name
        self._region = region
        self._neighbors = neighbors

    @property
    def name(self):
        return self._name

    @property
    def region(self):
        return self._region

    @property
    def neighbors(self):
        return self._neighbors

    @classmethod
    def from_ip(cls, fail_handler, ip=None):
        '''Get the country informations using provided IP address.'''
        url = 'http://ip-api.com/json'
        if ip is not None:
            url += '/{ip}'.format(ip=ip)

        try:
            info = parse_json(url_open(url).read())
        except:
            fail_handler(msg='Failed to parse country from IP')

        return cls.from_code(info['countryCode'], fail_handler)

    @classmethod
    def from_code(cls, code, fail_handler):
        '''Get the country informations using provided country code.'''
        url = 'https://restcountries.eu/rest/v1/alpha/{code}'.format(code=code)

        try:
            info = parse_json(url_open(url).read())
        except:
            fail_handler(msg='Failed to parse read informations')

        return cls(info['name'], info['region'], info['borders'])

# ------------------------------------------------------------------------------
# MIRROR INFORMATIONS ----------------------------------------------------------

class MirrorInfo(object):
    def __init__(self, initial):
        self._reset(initial)

    def _reset(self, initial={}):
        self._info = deep_copy(initial)

    @classmethod
    def parse_from_url(cls, url):
        return cls.parse(url_open(url).read())

    @classmethod
    def parse(cls, text):
        info = {}
        for mirror_group in ET.XML(text):
            for mirror in mirror_group:
                name = ''
                for e in mirror:
                    if e.tag == 'name':
                        name = e.text
                    if e.tag == 'uri':
                        uri = e.text
                        info[uri] = {
                            "name": name,
                            "country": mirror_group.get("countryname"),
                            "region": mirror_group.get("region"),
                            "ipv4": e.get("ipv4"),
                            "ipv6": e.get("ipv6"),
                            "proto": e.get("protocol")}
        return cls(info)

    def __len__(self):
        return len(self.urls())

    @property
    def info(self):
        return self._info

    def urls(self):
        return [url for url, args in list(self._info.items())]

    def filter_by_name(self, expected):
        match_fn = lambda name: name.lower().startswith(expected.lower())
        info = self._filter_by('name', match_fn)
        return MirrorInfo(info)

    def filter_by_proto(self, expected):
        match_fn = lambda proto: proto.lower() == expected.lower()
        info = self._filter_by('proto', match_fn)
        return MirrorInfo(info)

    def filter_by_country(self, expected):
        match_fn = lambda country: country.lower() == expected.lower()
        info = self._filter_by('country', match_fn)
        return MirrorInfo(info)

    def filter_by_region(self, expected):
        match_fn = lambda region: region.lower() == expected.lower()
        info = self._filter_by('region', match_fn)
        return MirrorInfo(info)

    def _filter_by(self, key, match_fn):
        result = {}
        for url, args in self._info.items():
            if match_fn(args[key]):
                result[url] = args
        return result

# ------------------------------------------------------------------------------
# FILL MECHANISMS --------------------------------------------------------------

class FillMechanisms(object):
    def __init__(self, mirrors, fail_handler):
        self._mirrors = mirrors
        self._sel_mirrors = []
        self._fail_handler = fail_handler

    @property
    def selected_mirrors(self):
        return self._sel_mirrors

    def fill_with_name(self, name):
        if name is not None:
            if len(self._sel_mirrors) == 0:
                self._sel_mirrors = self._mirrors.filter_by_name(name)
            elif len(self._sel_mirrors) > 1:
                self._sel_mirrors = self._sel_mirrors.filter_by_name(name)

    def fill_with_country(self, country):
        if country is not None:
            if len(self._sel_mirrors) == 0:
                self._sel_mirrors = self._mirrors.filter_by_country(country)
            elif len(self._sel_mirrors) > 1:
                self._sel_mirrors = self._sel_mirrors.filter_by_country(country)

    def fill_with_region(self, region):
        if region is not None:
            if len(self._sel_mirrors) == 0:
                self._sel_mirrors = self._mirrors.filter_by_region(region)
            elif len(self._sel_mirrors) > 1:
                self._sel_mirrors = self._sel_mirrors.filter_by_region(region)

    def fill_with_geo_loc(self):
        # If there isn't a matching mirror, try to find the best available.
        if len(self._sel_mirrors) == 0:
            country_info = CountryInfo.from_ip(self._fail_handler)
            self._fill_with_neighbors(country_info)

        # If the mirror isn't uniquely identified, try to narrow.
        if len(self._sel_mirrors) > 1:
            country_info = CountryInfo.from_ip(self._fail_handler)
            self.fill_with_region(country_info.region)

    def _fill_with_neighbors(self, country_info):
        self.fill_with_country(country_info.name)
        if len(self._sel_mirrors) == 0:
            for neighbor in country_info.neighbors:
                neigh_info = CountryInfo.from_code(neighbor, self._fail_handler)
                self._fill_with_neighbors(neigh_info)
                if len(self._sel_mirrors) != 0:
                    return

# ------------------------------------------------------------------------------
# MAIN FUNCTION ----------------------------------------------------------------

def main():
    module = AnsibleModule(argument_spec=dict(
        geo_loc=dict(type='bool', default=False),
        mirrors=dict(type='str', default=MIRRORS_XML),
        name=dict(type='str', default=None),
        proto=dict(type='str', default=None),
        region=dict(type='str', default=None),
        country=dict(type='str', default=None)))

    mirrors = MirrorInfo.parse_from_url(module.params['mirrors'])

    # (If provided) enforce a particular protocol.
    if module.params['proto'] is not None:
        mirrors = mirrors.filter_by_proto(module.params['proto'])

    fill_mechanisms = FillMechanisms(mirrors, module.fail_json)

    # Priority order: 'name' -> 'country' -> 'region'.
    fill_mechanisms.fill_with_name(module.params['name'])
    fill_mechanisms.fill_with_country(module.params['country'])
    fill_mechanisms.fill_with_region(module.params['region'])

    if module.params['geo_loc']:
        fill_mechanisms.fill_with_geo_loc()

    mirrors_urls = fill_mechanisms.selected_mirrors.urls()

    if len(mirrors_urls) == 0:
        module.fail_json(msg='There are no matching mirrors')

    mirror = mirrors_urls[0]

    module.exit_json(changed=True, msg='A Gentoo mirror has been selected.',
                     result=mirror)

# ------------------------------------------------------------------------------
# ENTRY POINT ------------------------------------------------------------------

from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()

# ------------------------------------------------------------------------------
# vim: set filetype=python :
