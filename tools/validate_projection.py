"""Validate the finite static hosting projection without network access."""
import argparse
import hashlib
from html.parser import HTMLParser
import json
import re
import subprocess
from pathlib import Path

ORIGIN = 'https://bilateral.mesmerprism.com'
APP = '/bilateral-control/'
OVERVIEW = 'https://mesmerprism.com/projects/bilateral-streaming.html'
ASSETS = {
    'app.mjs', 'bilateral-owner.mjs', 'capture-mode.mjs', 'decoder-policy.mjs',
    'frame-status.mjs', 'gateway.mjs', 'hub.css', 'hub.mjs', 'index.html',
    'live-owner.mjs', 'manifest.webmanifest', 'public-cache.mjs', 'public-sw.mjs',
    'pwa.mjs', 'session-view.mjs', 'style.css', 'view.mjs', 'viewer.html',
    'icons/apple-touch-icon.png', 'icons/quest-multi-stream-192.png',
    'icons/quest-multi-stream-512.png',
}
HOSTING_FILES = {
    '.gitattributes', '.gitignore', '.nojekyll', 'CNAME', 'LICENSE', 'README.md',
    'index.html', 'projects/bilateral-streaming.html', 'projection.json',
    'tools/validate_projection.py', 'tools/test_validate_projection.py',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(payload):
    return hashlib.sha256(payload).hexdigest()


def source_tree(files):
    """Compute the original Git tree identity from actual file bytes and names."""
    tree = {}
    for name, payload in files.items():
        parts = name.split('/')
        branch = tree
        for part in parts[:-1]:
            branch = branch.setdefault(part, {})
        branch[parts[-1]] = payload

    def object_id(kind, payload):
        return hashlib.sha1(kind + b' ' + str(len(payload)).encode('ascii') + b'\0' + payload).digest()

    def tree_id(branch):
        entries = []
        for name in sorted(branch, key=lambda key: (key + ('/' if isinstance(branch[key], dict) else '')).encode('utf-8')):
            value = branch[name]
            mode, oid = (b'40000', tree_id(value)) if isinstance(value, dict) else (b'100644', object_id(b'blob', value))
            entries.append(mode + b' ' + name.encode('utf-8') + b'\0' + oid)
        return object_id(b'tree', b''.join(entries))
    return tree_id(tree).hex()


class Redirect(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.refresh = []
        self.links = []
        self.canonical = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'meta' and attrs.get('http-equiv', '').lower() == 'refresh':
            self.refresh.append(attrs.get('content'))
        if tag == 'a':
            self.links.append(attrs.get('href'))
        if tag == 'link' and attrs.get('rel') == 'canonical':
            self.canonical.append(attrs.get('href'))


def validate(root, require_committed=False):
    root = Path(root)
    expected = HOSTING_FILES | {'bilateral-control/' + name for name in ASSETS | {'export-manifest.json'}}
    actual = set()
    for path in root.rglob('*'):
        relative = path.relative_to(root)
        if relative.parts[0] == '.git' or (relative.parts[:2] == ('tools', '__pycache__') and path.suffix == '.pyc'):
            continue
        require(not path.is_symlink(), 'Hosting projection must not contain symbolic links')
        if path.is_file():
            actual.add(relative.as_posix())
    require(actual == expected, f'Unexpected or missing public files: {sorted(actual ^ expected)}')
    projection = json.loads((root / 'projection.json').read_bytes())
    require(projection['schema'] == 'bilateral.static-projection.v1', 'Unsupported projection schema')
    require(projection['hostingOrigin'] == ORIGIN and projection['appPath'] == APP, 'Wrong hosting origin or app path')
    require(projection['sourceRepository'] == 'https://github.com/MesmerPrism/MesmerPrism.github.io', 'Wrong website source owner')
    require(projection['sourceSubtree'] == 'bilateral-control', 'Wrong source subtree')
    for field in ('sourceRevision', 'sourceTree', 'runtimeRevision'):
        require(re.fullmatch('[0-9a-f]{40}', projection[field]) is not None, f'Invalid {field}')
    app = root / 'bilateral-control'
    files = {name: (app / name).read_bytes() for name in ASSETS | {'export-manifest.json'}}
    require(source_tree(files) == projection['sourceTree'], 'App bytes differ from the original source tree')
    exported = json.loads(files['export-manifest.json'])
    require(exported['schema'] == 'questms.public-bilateral-export.v1', 'Wrong runtime export schema')
    require(exported['sourceRepository'] == projection['runtimeRepository'] == 'https://github.com/MesmerPrism/QuestMultiStream', 'Wrong runtime owner')
    require(exported['sourceRevision'] == projection['runtimeRevision'], 'Runtime revision differs from provenance')
    require(exported['appScope'] == APP, 'Wrong exported app scope')
    inventory = exported['files']
    require(len(inventory) == len(ASSETS) and {entry['path'] for entry in inventory} == ASSETS, 'Wrong exported inventory')
    for entry in inventory:
        require(sha256(files[entry['path']]) == entry['sha256'], f'Export hash mismatch: {entry["path"]}')
    install = json.loads(files['manifest.webmanifest'])
    require([install[key] for key in ('id', 'start_url', 'scope')] == [APP] * 3, 'Install identity must stay inside the app path')
    require((root / 'CNAME').read_bytes() == b'bilateral.mesmerprism.com\n', 'Wrong CNAME')
    require((root / '.nojekyll').read_bytes() == b'', '.nojekyll must be empty')
    attributes = (root / '.gitattributes').read_text(encoding='utf-8').splitlines()
    require('bilateral-control/** -text' in attributes and 'LICENSE -text' in attributes, 'Git must preserve copied bytes')
    require(projection['licenseSourcePath'] == 'LICENSE' and sha256((root / 'LICENSE').read_bytes()) == projection['licenseSha256'], 'Owner license bytes differ')
    for name, target, canonical in [('index.html', APP, ORIGIN + APP), ('projects/bilateral-streaming.html', OVERVIEW, OVERVIEW)]:
        redirect = Redirect((root / name).read_text(encoding='utf-8'))
        require(redirect.refresh == ['0; url=' + target] and target in redirect.links and redirect.canonical == [canonical], f'Wrong redirect: {name}')
    if require_committed:
        committed = subprocess.check_output(['git', '-C', str(root), 'ls-tree', '-rz', '--name-only', 'HEAD']).decode('utf-8').split('\0')
        require(set(filter(None, committed)) == expected, 'Committed public inventory differs')
        for name in sorted(expected):
            blob = subprocess.check_output(['git', '-C', str(root), 'show', 'HEAD:' + name])
            require((root / name).read_bytes() == blob, f'Local bytes differ from committed bytes: {name}')
    return {'files': len(expected), 'sourceRevision': projection['sourceRevision'], 'sourceTree': projection['sourceTree'],
            'runtimeRevision': projection['runtimeRevision'], 'hostingOrigin': ORIGIN, 'requireCommitted': require_committed}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-committed', action='store_true')
    args = parser.parse_args()
    print(json.dumps(validate(Path(__file__).resolve().parents[1], args.require_committed), sort_keys=True))
