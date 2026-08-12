import json
import os
import pkg_resources
import re
import tomllib
from glob import glob
from subprocess import check_output, STDOUT
from operator import itemgetter
from .. import nix_base32
from .source import Source

try:
    FileNotFoundError
except NameError:
    FileNotFoundError = OSError


COMMIT_ID_RE = re.compile('^[a-fA-F0-9]{40}$')


class UnresolvableRevision(Exception):
    pass


_nix_licenses = None


def get_nix_licenses():
    """
    Generate a map of known licenses based on `nixpkgs`.
    """
    global _nix_licenses

    if _nix_licenses is None:
        nix_licenses_json = check_output([
            'nix-instantiate', '--eval', '--expr',
            'with import <nixpkgs> { }; builtins.toJSON lib.licenses'])
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
    'GNU GPL': 'gpl1',
    'GNU GPLv2 or any later version': 'gpl2Plus',
    'GNU General Public License (GPL)': 'gpl1',
    'GNU General Public License v2 or later (GPLv2+)': 'gpl2Plus',
    'GPL': 'gpl1',
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


def get_version(req):
    try:
        return req.get_dist().version
    except (FileNotFoundError, AttributeError):
        for dist in pkg_resources.find_on_path(None, req.source_dir):
            return dist.version


class PythonPackage(object):
    def __init__(self, name, version, dependencies, source, pip_req=None,
                 setup_requires=None, tests_require=None):
        """
        :param dependencies: list of (name, version) pairs.
        """
        self.name = name
        self.version = version
        self.dependencies = dependencies
        self.raw_args = {}
        self.source = source
        self.check = False
        self.setup_requires = setup_requires or []
        self.tests_require = tests_require or []
        self.pip_req = pip_req

    @classmethod
    def from_requirements(cls, req, deps, finder, check):
        # TODO: Goes away with the pip driven path, see ADR-0001. Imported
        # here so that the report path does not need pip installed.
        from pip._vendor.packaging.requirements import Requirement
        from pip._internal.req.req_install import InstallRequirement

        def name_version(dep):
            return (
                dep.name,
                get_version(dep),
            )
        source = Source.from_url(req.link.url)

        setup_requires = []
        tests_require = []

        toml_path = os.path.join(req.source_dir, 'pyproject.toml')
        if os.path.isfile(toml_path):
            with open(toml_path, 'rb') as toml_file:
                toml_dict = tomllib.load(toml_file)
            for requirement in (
                toml_dict.get('build-system') or {}
            ).get('requires') or []:
                setup_requires.append(
                    InstallRequirement(Requirement(requirement), comes_from=req))

        if (not setup_requires
                and getattr(req, 'source_dir', None) and os.path.isdir(req.source_dir)):
            pattern = os.path.join(req.source_dir, '.eggs', '*', '*', 'PKG-INFO')
            for path in glob(pattern):
                with open(path) as fp:
                    for line in fp.readlines():
                        if line.startswith('Name: '):
                            setup_requires.append(
                                InstallRequirement(Requirement(line[6:].strip()),
                                                   comes_from=req))
                            break
            pattern = os.path.join(req.source_dir, '*', '*', 'tests_require.txt')
            for path in glob(pattern):
                with open(path) as fp:
                    for line in fp.readlines():
                        # These lines may contain anything...
                        if (not line.strip() or len(line.strip()) == 1):
                            continue
                        try:
                            tests_require.append(
                                InstallRequirement(Requirement(line.strip()),
                                                   comes_from=req))
                        except:
                            pass
                        break

        if ((source.path.endswith('.whl') and not source.path.endswith('-any.whl'))
                or source.path.endswith('.egg')):
            finder.format_control.disallow_binaries()
            source = Source.from_url(
                finder.find_requirement(req, upgrade=False).url)
        return cls(
            name=req.name,
            version=get_version(req),
            dependencies=sorted([name_version(d) for d in deps],
                                key=itemgetter(0)),
            source=source,
            pip_req=req,
            setup_requires=setup_requires or [],
            tests_require=check and tests_require or [],
        )

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
            doCheck='true' if self.check else 'false',
            src=source_to_nix(self.source, cache=cache),
            buildInputs='[]',
            checkInputs='[]',
            nativeBuildInputs='[]',
            propagatedBuildInputs='[]',
        )

        if self.source.path.endswith('.whl'):
            args.update(dict(format='"wheel"'))
        else:
            args.update(dict(format='"setuptools"'))

        if self.dependencies:
            args.update(dict(
                propagatedBuildInputs='[\n  ' + (
                    '\n  '.join('self."{}"'.format(name) for name, version
                                in self.dependencies)) + '\n]'
            ))

        if self.tests_require:
            args.update(dict(
                checkInputs='[\n  ' + (
                    '\n  '.join('self."{}"'.format(req.name) for req
                            in self.tests_require or ())) + '\n]'
            ))

        unzip = self.source.url.endswith('zip')
        if unzip or self.setup_requires:
            args.update(dict(
                nativeBuildInputs='[\n  ' + (
                    unzip and self.setup_requires and 'pkgs."unzip"\n  ' or
                    unzip and 'pkgs."unzip"' or '') + (
                    '\n  '.join('self."{}"'.format(req.name) for req
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
        licenses = self.get_licenses_from_pkginfo()

        # Convert license strings to nix.
        nix_licenses = set()
        for lic in licenses:
            nix_licenses.add(license_to_nix(lic))

        template = '[ {licenses} ]'
        return template.format(licenses=' '.join(nix_licenses))

    def get_licenses_from_pkginfo(self):
        """
        Parses the license string from PKG-INFO file.
        """
        licenses = set()
        data = ""
        try:
            try:
                data = self.pip_req.get_dist().get_metadata('PKG-INFO')
            except (FileNotFoundError, IOError):
                data = self.pip_req.get_dist().get_metadata('METADATA')
        except (FileNotFoundError, AttributeError):
            for dist in pkg_resources.find_on_path(None, self.pip_req.source_dir):
                try:
                    data = dist.get_metadata('PKG-INFO')
                except (FileNotFoundError, IOError):
                    data = dist.get_metadata('METADATA')
                break

        for line in data.split('\n'):

            # License string from setup() function.
            if line.startswith('License: '):
                lic = line.split('License: ')[-1]
                licenses.add(lic.strip())

            # License strings from classifiers.
            elif line.startswith('Classifier: License ::'):
                lic = line.split('::')[-1]
                licenses.add(lic.strip())

        return filter_licenses(licenses)


def filter_licenses(licenses):
    exclude = set(['UNKNOWN'])
    return licenses - exclude


def license_to_nix(license_name, nixpkgs='pkgs'):
    template = '{nixpkgs}.lib.licenses.{attribute}'
    full_name_template = '{{ fullName = "{full_name}"; }}'

    # Convert to lowercase for searching.
    full_name = license_name
    license_name = license_name.lower()

    # First try to fetch nix attribute name from custom mapping.
    attr = license_nix_map.get(license_name)
    if attr:
        return template.format(nixpkgs=nixpkgs, attribute=attr)

    # Otherwise try to look it up in the nix licenses.
    for attr, nix_license_data in get_nix_licenses().items():
        if license_name in nix_license_data.values():
            return template.format(nixpkgs=nixpkgs, attribute=attr)

    # No luck converting the license name to an attribute in
    # nixpkgs.lib.licenses. In this case we can at least store a set with the
    # fullName attribute like sets in nixpkgs.lib.licenses.
    return full_name_template.format(full_name=full_name)


def source_to_nix(source, cache=None):
    if source.vcs == 'git':
        return _fetchgit_to_nix(source)
    elif source.vcs == 'hg':
        return _fetchhg_to_nix(source)
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
    hash, revision = _prefetch(prefetch_git, source.url, source.rev)
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


def _fetchhg_to_nix(source):
    hash, revision = _prefetch(
        prefetch_hg, source.url, source.rev or 'default')
    return '\n'.join((
        'fetchhg {{',
        '  url = "{url}";',
        '  rev = "{revision}";',
        '  sha256 = "{hash}";',
        '}}',
    )).format(
        url=source.url,
        revision=revision,
        hash=hash,
    )


def _prefetch(prefetch, url, rev):
    print('Prefetching {url} at revision {rev}.'.format(url=url, rev=rev))
    return prefetch(url, rev)


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


def prefetch_git(url, rev):
    out = check_output([
        'nix-prefetch-git',
        '--url', url,
        '--rev', resolve_git_revision(url, rev)])
    data = json.loads(out.decode('utf-8'))
    return data['sha256'], data['rev']


def resolve_git_revision(url, rev):
    """
    Resolve `rev` against `url` the way pip resolves an `@rev` fragment.

    A branch takes precedence over a tag of the same name, as in pip's
    `pip._internal.vcs.git.Git.get_revision_sha`. Resolving here rather
    than leaving it to `nix-prefetch-git` matters because that reads a
    bare name as a tag only, so pip and the prefetch would disagree
    about which commit a branch name means.
    """
    refs = _list_remote_refs(url, rev)
    for candidate in ('refs/heads/' + rev, 'refs/tags/' + rev, rev):
        if candidate in refs:
            return refs[candidate]

    if COMMIT_ID_RE.match(rev):
        return rev

    raise UnresolvableRevision(
        'Cannot resolve "{rev}" to a commit in {url}.'.format(
            rev=rev, url=url))


def _list_remote_refs(url, pattern):
    out = check_output(['git', 'ls-remote', url, pattern])
    lines = out.decode('utf-8').splitlines()
    return dict(
        (ref, sha) for sha, ref in (line.split('\t') for line in lines))


def prefetch_hg(url, rev):
    out = check_output(['nix-prefetch-hg', url, rev], stderr=STDOUT)
    data = {}
    for line in out.decode('utf-8').splitlines():
        if line.startswith('hash is '):
            data['sha256'] = line[len('hash is '):]
        if line.startswith('hg revision is '):
            data['rev'] = line[len('hg revision is '):]
    return data['sha256'], data['rev']


def prefetch_url(url):
    out = check_output(['nix-prefetch-url', url])
    data = out.decode('utf-8').strip()
    return data
