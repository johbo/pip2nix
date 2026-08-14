import json
import os
from subprocess import check_output

from .. import nix_base32
from ..prefetch import UnresolvableRevision, prefetch_git, prefetch_url


# The `buildPythonPackage` builders pip2nix generates.
WHEEL = 'wheel'
SETUPTOOLS = 'setuptools'
PYPROJECT = 'pyproject'


_nix_licenses = None


def get_nix_licenses():
    """
    Generate a map of known licenses based on `nixpkgs`.
    """
    global _nix_licenses

    if _nix_licenses is None:
        # `lib.licenses` carries the SPDX operators `AND`, `OR`, `PLUS`
        # and `WITH` next to the licenses themselves, and `toJSON`
        # refuses to serialize a function.
        nix_licenses_json = check_output([
            'nix-instantiate', '--eval', '--expr',
            'with import <nixpkgs> { }; builtins.toJSON '
            '(lib.filterAttrs (name: value: builtins.isAttrs value) '
            'lib.licenses)'])
        nix_licenses_json = nix_licenses_json.decode('utf-8')

        # Dictionary which contains the contents of nixpkgs.lib.licenses.
        _nix_licenses = json.loads(json.loads(nix_licenses_json))

        # Convert all values to lowercase.
        for entry in _nix_licenses.values():
            for key, value in entry.items():
                try:
                    entry[key] = value.lower()
                except AttributeError:
                    # Skip values which don't have a lower() function.
                    pass

    return _nix_licenses


# Mapping from license name in setup.py to attribute in nixpkgs.lib.licenses.
# TODO: Think about providing this from outside, maybe from a file.
case_sensitive_license_nix_map = {
    'Apache 2.0': 'asl20',
    'Apache License, Version 2.0': 'asl20',
    'Apache Software License': 'asl20',
    'BSD license': 'bsdOriginal',
    'BSD': 'bsdOriginal',
    'GNU GPLv2 or any later version': 'gpl2Plus',
    'GNU General Public License v2 or later (GPLv2+)': 'gpl2Plus',
    'GNU General Public License v3 or later (GPLv3+)': 'gpl3Plus',
    'GNU Lesser General Public License v2 or later (LGPLv2+)': 'lgpl2Plus',
    'GPLv2 or later': 'gpl2Plus',
    'GPLv2': 'gpl2',
    'GPLv3': 'gpl3',
    'LGPLv2.1 or later': 'lgpl21Plus',
    'PSF License': 'psfl',
    'PSF': 'psfl',
    'Python Software Foundation License': 'psfl',
    'Python style': 'psfl',
    'Two-clause BSD license': 'bsd2',
    'ZPL 2.1': 'zpl21',
    'ZPL': 'zpl21',
    'Zope Public License': 'zpl21',
}
license_nix_map = {name.lower(): nix_attr
                   for name, nix_attr in
                   case_sensitive_license_nix_map.items()}


def indent(amount, string):
    lines = string.splitlines()
    if len(lines) == 0:
        return ''
    elif len(lines) == 1:
        return lines[0]
    else:
        return (
            lines[0] + '\n' +
            '\n'.join(' ' * amount + l for l in lines[1:]))


class PythonPackage(object):
    def __init__(self, name, version, dependencies, source,
                 setup_requires=None, licenses=None, format=SETUPTOOLS):
        """
        :param dependencies: list of (name, version) pairs.
        :param setup_requires: names of the packages needed to build it.
        :param licenses: license names as declared, most authoritative
            spelling first.
        :param format: the `buildPythonPackage` builder, decided by the
            adapter from what the source declares.
        """
        self.name = name
        self.version = version
        self.dependencies = dependencies
        self.raw_args = {}
        self.source = source
        self.check = False
        self.setup_requires = setup_requires or []
        self.licenses = licenses or []
        self.format = format

    def override(self, config):
        self.raw_args = config.get('args', {})

    def to_nix(self, include_lic, cache=None):
        template = '\n'.join((
            'super.buildPythonPackage rec {{',
            '  {args}',
            '}};',
        ))
        meta_template = '\n'.join((
            'meta = {{',
            '  {meta_args}',
            '}};',
        ))

        args = dict(
            pname='"{s.name}"'.format(s=self),
            version='"{s.version}"'.format(s=self),
            format='"{s.format}"'.format(s=self),
            doCheck='true' if self.check else 'false',
            src=source_to_nix(self.source, cache=cache),
            buildInputs='[]',
            checkInputs='[]',
            nativeBuildInputs='[]',
            propagatedBuildInputs='[]',
        )

        if self.dependencies:
            args.update(dict(
                propagatedBuildInputs='[\n  ' + (
                    '\n  '.join('self."{}"'.format(name) for name, version
                                in self.dependencies)) + '\n]'
            ))

        unzip = self.source.url.endswith('zip')
        if unzip or self.setup_requires:
            args.update(dict(
                nativeBuildInputs='[\n  ' + (
                    unzip and self.setup_requires and 'pkgs."unzip"\n  ' or
                    unzip and 'pkgs."unzip"' or '') + (
                    '\n  '.join('self."{}"'.format(name) for name
                            in self.setup_requires or ())) + '\n]'
            ))

        args.update(self.raw_args)

        # Prepare meta arguments.
        meta_args = dict()
        if include_lic:
            license_nix = self.get_license_nix()
            if license_nix:
                meta_args['license'] = license_nix

        # Render name first
        raw_args = 'pname = {};\n'.format(args.pop('pname'))
        raw_args += 'version = {};\n'.format(args.pop('version'))
        raw_args += 'src = {};\n'.format(args.pop('src'))
        raw_args += 'format = {};\n'.format(args.pop('format'))
        raw_args += 'doCheck = {};'.format(args.pop('doCheck'))
        for k, v in sorted(args.items()):
            raw_args += '\n{} = {};'.format(k, v)

        # Render meta arguments.
        if meta_args:
            raw_meta_args = ''
            for k, v in sorted(meta_args.items()):
                raw_meta_args += '{} = {};\n'.format(k, v)
            meta = meta_template.format(meta_args=indent(2, raw_meta_args))
            raw_args += '\n{}'.format(meta)

        return template.format(args=indent(2, raw_args))

    def get_license_nix(self):
        """
        The `meta.license` value, or None when nothing is declared.

        Only the spellings nixpkgs knows are rendered. When it knows
        none of them the most authoritative one is kept as a full name,
        which is the shape `nixpkgs.lib.licenses` entries have anyway.
        """
        attributes = []
        for license_name in self.licenses:
            attribute = nix_license_attribute(license_name)
            if attribute and attribute not in attributes:
                attributes.append(attribute)

        if attributes:
            rendered = [license_attribute_to_nix(attribute)
                        for attribute in attributes]
        elif self.licenses:
            rendered = [license_full_name_to_nix(self.licenses[0])]
        else:
            return None

        return '[ {licenses} ]'.format(licenses=' '.join(rendered))


def nix_license_attribute(license_name):
    """
    The `nixpkgs.lib.licenses` attribute a license name maps to, if any.

    The names a package declares are free text, an SPDX identifier or a
    trove classifier, so the lookup goes through the hand-written map
    first and then through every value nixpkgs records for a license --
    `spdxId` among them, which is what makes SPDX identifiers resolve.
    """
    license_name = license_name.lower()

    attribute = license_nix_map.get(license_name)
    if attribute:
        return attribute

    for attribute, nix_license_data in get_nix_licenses().items():
        if license_name in nix_license_data.values():
            return attribute

    return None


def license_attribute_to_nix(attribute):
    return 'pkgs.lib.licenses.{attribute}'.format(attribute=attribute)


def license_full_name_to_nix(license_name):
    return '{{ fullName = "{full_name}"; }}'.format(full_name=license_name)


def source_to_nix(source, cache=None):
    if source.vcs == 'git':
        return _fetchgit_to_nix(source)
    elif source.vcs:
        raise NotImplementedError(
            'Cannot render a {vcs} repository, pip2nix renders git.'.format(
                vcs=source.vcs))
    elif source.scheme == 'file':
        return './' + os.path.relpath(source.path)
    elif source.scheme in ('http', 'https'):
        return _fetchurl_to_nix(source, cache or {})
    else:
        raise NotImplementedError(
            'Unknown source scheme "{}"'.format(source.scheme))


def _fetchgit_to_nix(source):
    if not source.rev:
        raise UnresolvableRevision(
            'No revision given for {url}. Refusing to generate a source '
            'which follows whatever the default branch points at.'.format(
                url=source.url))
    hash, revision, _checkout = prefetch_git(source.url, source.rev)
    return '\n'.join((
        'fetchgit {{',
        '  url = "{url}";',
        '  rev = "{revision}";',
        '  sha256 = "{hash}";',
        '}}',
    )).format(
        url=source.url,
        revision=revision,
        hash=hash,
    )


def _fetchurl_to_nix(source, cache):
    if source.sha256:
        hash = nix_base32.from_hex(source.sha256)
    elif source.url in cache:
        hash = cache[source.url]
    else:
        print('Prefetching {url}.'.format(url=source.url))
        hash = prefetch_url(source.url)
    return '\n'.join((
        'fetchurl {{',
        '  url = "{url}";',
        '  sha256 = "{hash}";',
        '}}'
    )).format(
        url=source.url,
        hash=hash,
    )
