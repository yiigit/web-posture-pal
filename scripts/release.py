"""Consistent local/Actions releases; Commitizen owns version changes, commits and tags."""
import argparse
import os
from pathlib import Path
import re
import subprocess
import sys
import tomllib

STABLE_VERSION = re.compile(r'(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)')
RELEASE_HEADING = re.compile(r'^## v(\d+\.\d+\.\d+) \(\d{4}-\d{2}-\d{2}\)$', re.M)


def git(*args):
    return subprocess.check_output(['git', *args], text=True).strip()


def stable_version(value):
    if not STABLE_VERSION.fullmatch(value):
        raise ValueError('Use a stable semantic version without a v prefix, for example 0.13.0')
    return tuple(map(int, value.split('.')))


def current_version():
    return tomllib.loads(Path('pyproject.toml').read_text())['project']['version']


def release_sections():
    text = Path('CHANGELOG.md').read_text()
    if not text.startswith('# Changelog\n\n## Unreleased\n'):
        raise ValueError('CHANGELOG.md must start with a separate Unreleased section')
    headings = list(RELEASE_HEADING.finditer(text))
    if not headings:
        raise ValueError('No released version found in CHANGELOG.md')
    return text, headings


def release_notes():
    text, headings = release_sections()
    end = headings[1].start() if len(headings) > 1 else len(text)
    return text[headings[0].end():end].strip() + '\n'


def verify(tag=None):
    version = current_version()
    stable_version(version)
    if Path('VERSION').read_text().strip() != version:
        raise ValueError('VERSION disagrees with pyproject.toml')
    patterns = {
        'compose.yaml': r'^\s+image: posturepal:(\d+\.\d+\.\d+)\s*$',
        'README.md': r'Current release: \*\*(\d+\.\d+\.\d+)\*\*',
        **{f'frontend/src/{name}.js': r'v(\d+\.\d+\.\d+)' for name in ('main', 'breaks', 'dashboard')},
    }
    for filename, pattern in patterns.items():
        found = re.findall(pattern, Path(filename).read_text(), re.M)
        if not found or set(found) != {version}:
            raise ValueError(f'{filename} disagrees with pyproject.toml')
    text, headings = release_sections()
    versions = [heading[1] for heading in headings]
    if versions[0] != version or len(versions) != len(set(versions)):
        raise ValueError('Changelog release headings disagree with the current version or are duplicated')
    if not release_notes().strip():
        raise ValueError('The current release has no notes')
    if tag is not None:
        if tag != 'v' + version:
            raise ValueError('Tag disagrees with project version')
        if git('cat-file', '-t', tag) != 'tag' or git('rev-parse', tag + '^{}') != git('rev-parse', 'HEAD'):
            raise ValueError('Release tag must be annotated and point to the checked-out commit')
        if text[len('# Changelog\n\n## Unreleased\n'):headings[0].start()].strip():
            raise ValueError('Tagged releases must have an empty Unreleased section')
    return version


def prepare(version):
    requested = stable_version(version)
    current = verify()
    if git('status', '--porcelain'):
        raise ValueError('Release preparation requires a clean working tree')
    if version == current:
        # Allows a failed GitHub publication to be retried without another bump.
        verify('v' + version)
        return version
    if requested <= stable_version(current):
        raise ValueError('Release version must be greater than the current version')
    if git('tag', '--list', 'v' + version):
        raise ValueError('Requested release tag already exists; tags are never overwritten')
    old_text, headings = release_sections()
    notes = old_text[len('# Changelog\n\n## Unreleased\n'):headings[0].start()].strip()
    if not notes:
        raise ValueError('Add release notes under Unreleased before preparing a release')
    history = old_text[headings[0].start():]
    subprocess.run([sys.executable, '-m', 'commitizen', 'bump', version,
                    '--check-consistency', '--template', '.github/release-notes.md.j2',
                    '--extra', 'release_notes=' + notes], check=True)
    verify('v' + version)
    new_text, new_headings = release_sections()
    if len(new_headings) < 2 or new_text[new_headings[1].start():] != history:
        raise ValueError('Changelog history changed unexpectedly; refusing publication')
    if release_notes().strip() != notes:
        raise ValueError('Detailed release notes were not preserved; refusing publication')
    return version


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    check = commands.add_parser('verify')
    check.add_argument('--tag')
    bump = commands.add_parser('prepare')
    bump.add_argument('version')
    notes = commands.add_parser('notes')
    notes.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'prepare':
            version = prepare(args.version)
        else:
            version = verify(args.tag if args.command == 'verify' else None)
            if args.command == 'notes':
                args.output.write_text(release_notes())
        output = os.getenv('GITHUB_OUTPUT')
        if output:
            with open(output, 'a') as file:
                file.write(f'version={version}\ntag=v{version}\n')
        print(f'Verified PosturePal {version}')
    except (ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'Release check failed: {error}\n')


if __name__ == '__main__':
    main()
