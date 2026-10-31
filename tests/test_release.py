"""Release safety checks use isolated Git repositories, never this checkout's refs."""
import contextlib
import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('release_helper', ROOT / 'scripts/release.py')
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)
        for name in ['pyproject.toml', 'VERSION', 'compose.yaml', 'README.md', 'CHANGELOG.md',
                     'frontend/src/main.js', 'frontend/src/breaks.js', 'frontend/src/dashboard.js',
                     '.github/release-notes.md.j2']:
            target = self.path / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        self.git('init', '--initial-branch=main')
        self.git('config', 'user.name', 'Release Test')
        self.git('config', 'user.email', 'release@example.test')
        # Test fixtures represent a clean release, independent of pending source notes.
        text = (self.path / 'CHANGELOG.md').read_text()
        historical = text[text.index('## v' + (self.path / 'VERSION').read_text().strip()):]
        (self.path / 'CHANGELOG.md').write_text('# Changelog\n\n## Unreleased\n\n' + historical)
        self.commit('chore: initial test fixture')
        self.version = (self.path / 'VERSION').read_text().strip()
        self.git('tag', '-a', 'v' + self.version, '-m', 'Test release')

    def git(self, *args):
        return subprocess.check_output(['git', *args], cwd=self.path, text=True, stderr=subprocess.DEVNULL).strip()

    def commit(self, message):
        self.git('add', '.')
        self.git('commit', '-m', message)

    def test_commitizen_preserves_curated_notes_history_and_idempotent_retry(self):
        next_version = '.'.join([self.version.split('.')[0], str(int(self.version.split('.')[1])+1), '0'])
        changelog = self.path / 'CHANGELOG.md'
        before = changelog.read_text()
        notes = '- Preserve detailed notes with a=b and literal {{ user_input }}.\n- Keep privacy controls.'
        changelog.write_text(before.replace('## Unreleased\n', '## Unreleased\n\n' + notes + '\n', 1))
        self.commit('feat: add isolated release example')
        with contextlib.chdir(self.path):
            release.prepare(next_version)
            self.assertEqual(release.verify('v' + next_version), next_version)
            self.assertEqual(release.release_notes().strip(), notes)
            head = release.git('rev-parse', 'HEAD')
            release.prepare(next_version)
            self.assertEqual(release.git('rev-parse', 'HEAD'), head)
        self.assertTrue(changelog.read_text().endswith(before[before.index('## v'):]))

    def test_consistency_detects_stale_version_files(self):
        (self.path / 'VERSION').write_text('0.0.1\n')
        with contextlib.chdir(self.path), self.assertRaisesRegex(ValueError, 'VERSION disagrees'):
            release.verify()

    def test_tag_must_match_version_and_point_to_head(self):
        with contextlib.chdir(self.path):
            with self.assertRaisesRegex(ValueError, 'Tag disagrees'):
                release.verify('v999.0.0')
            Path('README.md').write_text(Path('README.md').read_text() + '\nFixture update.\n')
            self.commit('docs: change fixture')
            with self.assertRaisesRegex(ValueError, 'annotated and point'):
                release.verify('v' + self.version)

    def test_prepare_requires_clean_tree_and_notes_and_never_downgrades(self):
        with contextlib.chdir(self.path):
            with self.assertRaisesRegex(ValueError, 'greater'):
                release.prepare('0.0.1')
            with self.assertRaisesRegex(ValueError, 'Add release notes'):
                release.prepare('0.99.0')
            Path('untracked.txt').write_text('Uncommitted fixture')
            with self.assertRaisesRegex(ValueError, 'clean working tree'):
                release.prepare('0.99.0')

    def test_strict_versions_and_lightweight_tags_are_rejected(self):
        for version in ['v0.13.0', '0.13.0;echo unsafe', '0.13.0-rc.1', '00.13.0', '0.13']:
            with self.assertRaises(ValueError):release.stable_version(version)
        self.git('tag', '-d', 'v' + self.version)
        self.git('tag', 'v' + self.version)
        with contextlib.chdir(self.path), self.assertRaisesRegex(ValueError, 'annotated'):
            release.verify('v' + self.version)
