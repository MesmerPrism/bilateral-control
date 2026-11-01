# Bilateral Control static hosting

This repository hosts the reviewed Bilateral Control browser app at
`https://bilateral.mesmerprism.com/bilateral-control/`. It contains a static
projection; [QuestMultiStream](https://github.com/MesmerPrism/QuestMultiStream)
owns the browser source and exporter. The
[project overview](https://mesmerprism.com/projects/bilateral-streaming.html)
remains on the main Mesmer Prism website.

The exported `bilateral-control/` directory is copied byte for byte from website
commit `8fc44e4fd64fa66207b4e4c42895f95dc46441e0`, subtree
`c6a8dbfa209abe7b9f912735a3b9cd2fc4dfc500`. Its unchanged export manifest binds
QuestMultiStream source commit `bd1d05473256e3bfaa100655422552c0eee139d6`.
[projection.json](projection.json) records the source identities and license hash.

Run the local checks with Python 3:

```sh
python -B -m unittest discover -s tools -p test_validate_projection.py -v
python -B tools/validate_projection.py --require-committed
```

The second command runs after committing the prepared projection. It checks
the exact finite inventory, exported hashes, original Git subtree identity,
hosting configuration, and equality with this repository's committed bytes.
No network or device connection is made.

For deployment, publish a reviewed `main` branch through GitHub Pages from
the repository root. Configure the custom domain `bilateral.mesmerprism.com`
in Pages before adding its DNS CNAME to `MesmerPrism.github.io`; enable HTTPS
once GitHub has provisioned the certificate. Retain `CNAME` and `.nojekyll`.
The root redirects to the app, and the local project route redirects to the
main-site overview. Publishing these files alone does not establish DNS,
trusted HTTPS, phone installation, gateway connectivity, or media operation.

For a refresh, first validate and commit the source export in its owning
repositories. Copy the selected website commit's `bilateral-control/` Git
blobs without checkout newline conversion. Update this repository's source
commit/tree and runtime/license provenance in `projection.json` and this
README, then rerun the checks before committing and deploying. Keep the app
at `/bilateral-control/` and preserve its manifest, service worker and runtime
bytes; do not customize the app in this hosting repository. Do not add operator
links, tokens, private configuration, machine paths, captures or APKs.

The runtime files and icons retain their owner's MIT license. [LICENSE](LICENSE)
is copied unchanged from the bound QuestMultiStream commit. No separate license
is declared here for the hosting documentation and configuration.
