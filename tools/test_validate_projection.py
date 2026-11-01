import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def validator():
    spec = importlib.util.spec_from_file_location('validate_projection', ROOT / 'tools/validate_projection.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class HostingProjection(unittest.TestCase):
    def copy_projection(self, directory):
        target = Path(directory) / 'projection'
        shutil.copytree(ROOT, target, ignore=shutil.ignore_patterns('.git', '__pycache__'))
        return target

    def test_original_export_and_static_hosting_are_valid_without_network_or_machine_paths(self):
        validator().validate(ROOT)

    def test_rehashed_runtime_tamper_still_fails_the_exact_source_tree(self):
        module = validator()
        with tempfile.TemporaryDirectory() as directory:
            target = self.copy_projection(directory)
            runtime = target / 'bilateral-control/capture-mode.mjs'
            runtime.write_bytes(runtime.read_bytes() + b'\n// changed hosting projection\n')
            manifest_path = target / 'bilateral-control/export-manifest.json'
            manifest = json.loads(manifest_path.read_text())
            next(entry for entry in manifest['files'] if entry['path'] == 'capture-mode.mjs')['sha256'] = module.sha256(runtime.read_bytes())
            manifest_path.write_bytes((json.dumps(manifest) + '\n').encode())
            with self.assertRaisesRegex(ValueError, 'source tree'):
                module.validate(target)

    def test_hosting_configuration_and_unknown_files_are_rejected(self):
        module = validator()
        mutations = [
            ('CNAME', b'other.mesmerprism.com\n'),
            ('index.html', b'<a href="http://unsafe.example/">Wrong app</a>'),
            ('projects/bilateral-streaming.html', b'<a href="https://evil.example/">Wrong project</a>'),
            ('private-config.json', b'{"token":"not-for-publication"}'),
            ('.gitattributes', b'* text=auto\n'),
        ]
        for path, payload in mutations:
            with self.subTest(path=path), tempfile.TemporaryDirectory() as directory:
                target = self.copy_projection(directory)
                (target / path).write_bytes(payload)
                with self.assertRaises(ValueError):
                    module.validate(target)

    def test_committed_check_rejects_uncommitted_hosting_edits(self):
        module = validator()
        with tempfile.TemporaryDirectory() as directory:
            target = self.copy_projection(directory)
            template = Path(directory) / 'empty-template'
            template.mkdir()
            env = {**os.environ, 'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_CONFIG_NOSYSTEM': '1'}
            def git(*arguments):
                return subprocess.check_output(['git', '-C', str(target), *arguments], env=env, stderr=subprocess.PIPE)
            git('init', '--quiet', '--initial-branch=fixture', f'--template={template}')
            git('config', 'user.name', 'Static projection fixture')
            git('config', 'user.email', 'projection-fixture@example.invalid')
            git('add', '--all')
            git('-c', 'commit.gpgsign=false', 'commit', '--quiet', '-m', 'Static projection fixture')
            module.validate(target, require_committed=True)
            readme = target / 'README.md'
            readme.write_bytes(readme.read_bytes() + b'\nUncommitted hosting note.\n')
            with self.assertRaisesRegex(ValueError, 'committed'):
                module.validate(target, require_committed=True)


if __name__ == '__main__':
    unittest.main()
