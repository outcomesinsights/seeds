# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [0.7.0a5] - 2026-09-11

**Not a public release.** Like every 0.7.0aN, this is an internal alpha on the
`0.7.0` branch: `main` is still the 0.6.x line, nothing here is on PyPI, and the
only consumers are this machine's own stores via a pinned flake input. The
format is still being exercised, which is the point.

Everything in a5 was found by USING a4 across 21 stores, and every one of the
four came from another session hitting it rather than from testing here.

Two are the store defending itself against its own tooling. `seeds normalize`
now refuses a dirty store and prints the exact path-scoped `git commit -- …`,
after three sessions each nearly swept somebody's uncommitted seed into a
commit labelled "reformat, not an edit" — and one of them showed that checking
the tree is clean at the START is not enough, because a stranger's seed landed
a minute into its run. And an unreadable seed is now a message naming the file
and pointing at `seeds check`, where five commands previously died with a
traceback on a single malformed file.

Two are routes that did not exist. `seeds update <id> --append -` reads a body
from stdin, which closes the mechanism behind the daily drift: agents built long
seeds with `seeds create` and then `cat >>` straight into the file, bypassing the
writer entirely, so a store normalized in the morning wanted a pass by evening
with no stale file involved. And `seeds search -F` matches a pasted reference
as literal text — the store holds `\[[clc-97e]\]`, which as a regex reads
`[clc-97e]` as a character class and returned two confident hits that mentioned
the reference nowhere.

### Added
- -F matches a reference as text, not as a regex ([7dc8210](https://github.com/outcomesinsights/seeds/commit/7dc821087a4d76df55c5b1614641b293d7cc04ca))
- --append reads stdin, and prime says to use it ([3a72c1e](https://github.com/outcomesinsights/seeds/commit/3a72c1e10ad3ade23236b54188a90787cf7c738d))

### Fixed
- An unreadable seed is a message, not a traceback ([f3dad23](https://github.com/outcomesinsights/seeds/commit/f3dad23aa6b271ac2f962e71cf385e1dad93bab9))
- Refuse a dirty store, and name the files to commit ([b34b922](https://github.com/outcomesinsights/seeds/commit/b34b922ab5de5ccbac64f972d1fa727c929f491a))

## [0.7.0a4] - 2026-09-10

**The store stops being able to hold a seed that a formatter rejects.** a2 made
the store a fixed point of mdformat and a3 corrected how it spells things; a4
removes the last exception, which was the writer opting a body out of formatting
altogether. That exception is now empty on every store measured — 0 bodies,
down from 4 reported and 3 genuine.

Both bodies it existed for are fenced at the source instead. A fork's git
conflict markers: `=======` is also a setext heading underline, so unfenced they
read as a heading and a formatter returns `# \<<\<<\<<< database`. And an
unfenced YAML sample — a label, a `---`, the sample, a `---` — parses as a
heading whose text is the whole sample, which formatting joins onto one `## …`
line. The tell there is the SPAN, not the content: markdown-it reports a
five-line heading, and nobody writes one of those.

The detector for that exception was also over-reporting. It fired on any body a
formatter would change, which includes one an older seeds wrote and nobody has
normalized — calling a merely stale file "stored exactly as it came, because
formatting would change what it means". Three quarters of the evidence that
prompted this release was that mislabel.

### Fixed
- Fence the fork block and the mislabelled setext block ([afbccb1](https://github.com/outcomesinsights/seeds/commit/afbccb1f11caaf9b7e69ea75415ffbd40d0c9f28))
- Body-kept-verbatim was naming files that are merely stale ([a3d43ea](https://github.com/outcomesinsights/seeds/commit/a3d43ea7437186a0a01baf3b4a0f0463b8a545e6))
- Sanitize the environment for the `bd` seam too ([1f4e9f0](https://github.com/outcomesinsights/seeds/commit/1f4e9f09f34bb40201391197c82a9e0f0ddd8183))
- Judge a numeric id reference like every other one ([6dceddd](https://github.com/outcomesinsights/seeds/commit/6dceddd8f38d1f1171f657011ae9ba275e7df205))

## [0.7.0a3] - 2026-09-09

**Everything a2 got wrong about agreeing with the ecosystem, found by using
it.** a2 made the store a fixed point of mdformat; a3 is what a day of running
it against real repos and a second machine turned up.

Three of the fixes are one shape: seeds writing a spelling no other tool
writes. Scalars were quoted where a YAML emitter leaves them plain, and
quoted the wrong way where it quotes — 16 of 49 shapes disagreed, and the
reader had to learn what the writer now emits or seeds would have written
files it could not read back. `seeds search` learned to read the formatter's
escapes rather than seeds undoing them, since undoing them only churns
against the next run.

The other two are data. `seeds check --smells` could not see a body the writer
had kept verbatim — the check compares a file against a render of itself, and
such a file renders to exactly its own bytes, so it was blind to the one case
it was documented as covering. And `seeds convert` dropped the legacy
`questions` table wholesale: fine wherever 0.6's `import` had run, silent data
loss for a store that never reached v2. Two such stores on this machine held
nine answered questions between them.

### Documentation
- The yes/no group, and the right reason for quoting it ([9c31bc3](https://github.com/outcomesinsights/seeds/commit/9c31bc3923f799869034eac0fe89f4a500324af3))
- Name the verification command, and scope it to the store ([0f73415](https://github.com/outcomesinsights/seeds/commit/0f73415c61f7321743ce96d51270136940c3cc8b))

### Fixed
- The v1 refusal now names a path that can actually be walked ([215819d](https://github.com/outcomesinsights/seeds/commit/215819d67924300b1722e00fc29c6dae092baf36))
- Translate the legacy questions table instead of dropping it ([4b112b5](https://github.com/outcomesinsights/seeds/commit/4b112b5e73419b8040635bc426c52fb6ee7cebd6))
- Stop over-quoting plain scalars, and read what that emits ([5fb8d50](https://github.com/outcomesinsights/seeds/commit/5fb8d5017fe3faf264db5856a7ff6e93a9b362df))
- Name a body the writer kept verbatim ([6b9999c](https://github.com/outcomesinsights/seeds/commit/6b9999cab12ce35635721a19e3c1fc628ad12d14))
- Emit the scalar quoting PyYAML does ([4582b43](https://github.com/outcomesinsights/seeds/commit/4582b430354e9c3c419018e9a85497e41399595c))
- Satisfy mypy on the formatter path, and reject a bad extensions key ([8d13ec1](https://github.com/outcomesinsights/seeds/commit/8d13ec1d08316177a803190701a0798435c17cfc))

## [0.7.0a2] - 2026-09-09

**An alpha, so the store's format can be exercised before it is frozen.**
0.7 replaces the SQLite database and its tracked JSONL with one markdown file
per seed — git is the store, `seeds check` is the verifier, and there is
nothing left to sync. a2 adds the half that 0.7 had not reckoned with: the
store now lives in the working tree, where every formatter in the repo can
reach it.

It reached it. A `prettier --write` over a repo left 54 of 1,324 seed files
across 13 stores unparseable, in two ways nobody had predicted — a body-less
file's trailing blank line stripped, and a `resolution:` scalar re-quoted from
double to single. Both are fixed in the WRITER rather than by loosening the
reader, because a store whose canonical form disagrees with the ecosystem's
default formatter re-dirties itself on every run. The writer now formats every
body with mdformat as it writes it, so a `mdformat .` over the repo is a no-op
on `.seeds/` instead of a churn of every file — verified over all 1,324.

Formatting a body reshapes unfenced literal text, so the writer fences its own:
agents write nearly every seed body and there is nobody standing by to be asked.
Where fencing cannot save a body, it is stored exactly as it came.

### Added
- Leave a converted store canonical, and cover two more escapes ([2ed3b03](https://github.com/outcomesinsights/seeds/commit/2ed3b038f6129f9620a77d4b555050d49d843b72))
- The writer fences its own literal text ([848609d](https://github.com/outcomesinsights/seeds/commit/848609d4c4a6babf0268b6d666cb52bc9f9f7fe4))
- Seeds normalize rewrites the store in canonical form ([d91fa23](https://github.com/outcomesinsights/seeds/commit/d91fa233df7457e1b826e09e6d7c18fd653251bc))
- Tell agents to fence anything that must stay verbatim ([435e82c](https://github.com/outcomesinsights/seeds/commit/435e82cd97c64a20e669fc9fd0ff089f3d7d8543))
- The writer formats every body with mdformat ([17c3c8c](https://github.com/outcomesinsights/seeds/commit/17c3c8c34de30b788e382560d4a94c68a2773b78))
- Give `seeds create` --content-file and --content - ([c63d487](https://github.com/outcomesinsights/seeds/commit/c63d4870a5dbf89d76d61603ab67dd63b1f4beb7))
- Add `winnow` — judge the verb's candidates and present findings ([355826a](https://github.com/outcomesinsights/seeds/commit/355826ab61d395e30b4e56684f0f67c41d65bfe0))
- Add the `glean` skill — judge and present what a session worked out ([4c12668](https://github.com/outcomesinsights/seeds/commit/4c126689b4e8bd0b03ece4ac5b8fa00294b4f8ce))
- Add the `cutting` skill for context-carrying topic capture ([d1558ae](https://github.com/outcomesinsights/seeds/commit/d1558ae545e7d5fb79ebdbf53b1c7afafe606805))
- Add the `seeds winnow` verb — corpus audit of the thinking ([bc24b17](https://github.com/outcomesinsights/seeds/commit/bc24b17cbcfa268ac5642265ac2b7dba9c921135))
- Add the `seeds glean` verb — candidates from a session transcript ([53d6a3f](https://github.com/outcomesinsights/seeds/commit/53d6a3f86dc1ed3c911d23d7820db094e6e1bb55))
- Flag a seed body rewritten in place with a frozen updated_at ([86c99e5](https://github.com/outcomesinsights/seeds/commit/86c99e5a06e2b9f4a7f807ffc2f673259e5ff480))
- Split a multi-line legacy title, and state the body's blank-line rule ([abb70fd](https://github.com/outcomesinsights/seeds/commit/abb70fdee1cc6f00f29daca4ab7c546908b79d56))
- Differential harness proving 0.7 storage costs no behaviour ([5422856](https://github.com/outcomesinsights/seeds/commit/54228561a1a5be6699eb4c17b651d7816995a93b))
- Gate flake.nix against pyproject.toml's dependency list ([725d613](https://github.com/outcomesinsights/seeds/commit/725d61372419bf238a6f2f2b68e65b9ee3030948))
- Three smells for the store's format rules and its tooling ([b550f92](https://github.com/outcomesinsights/seeds/commit/b550f92b3c9c328e3195f3053d09dc24869767cf))
- Make the unconverted-repo message the migration UX (seeds-4co.18) ([e71aef0](https://github.com/outcomesinsights/seeds/commit/e71aef0fafdf44b8803287a2440971f40794174d))
- Stage the retired seeds.jsonl for deletion (seeds-4co.19) ([9c0fb46](https://github.com/outcomesinsights/seeds/commit/9c0fb462cb79456ce9ac10eaccfcb2c8f80fc739))
- Convert the design database to the seed-file tree ([6694f84](https://github.com/outcomesinsights/seeds/commit/6694f84259a8f266ac5792bd8b8f0d340a0de5f5))
- Add `seeds history`, a seed's evolution read out of git ([119c504](https://github.com/outcomesinsights/seeds/commit/119c5048edbf7d3a06628bdbb7b471c8791d3151))
- Point every command at the tree and delete the SQLite layer ([9ff40ed](https://github.com/outcomesinsights/seeds/commit/9ff40ed873768d3955fd0d5ab9e5feb192b20b7f))
- Add the tree-backed store and a read-only legacy SQLite reader ([e133fc7](https://github.com/outcomesinsights/seeds/commit/e133fc744da536b8edfbe4ac34a91d7ab072bb99))
- Add `seeds export --json`, a stdout pipe for the corpus ([0960c77](https://github.com/outcomesinsights/seeds/commit/0960c770cb23eb942ecd335b74dfc408bcdb2d10))
- Gate commits on seeds check, including the mass-rewrite shape ([cc1ee22](https://github.com/outcomesinsights/seeds/commit/cc1ee2285b762dc3fe6300e53b24abe7cd8c8b10))
- Add the smells tier and the comparison against git ([487d97d](https://github.com/outcomesinsights/seeds/commit/487d97db67fedd069299c995f61813651c0b1db4))
- Add seeds convert, the union-input converter ([2c4a4ed](https://github.com/outcomesinsights/seeds/commit/2c4a4ed186f215775dee828412dcbb8fb69693e1))
- Add seeds check, the violations tier ([a603938](https://github.com/outcomesinsights/seeds/commit/a603938f0cfdd09efc7197b5833274b25d1307b8))
- Add the seed-file reader/writer, the single door to .seeds/seeds/ ([a438564](https://github.com/outcomesinsights/seeds/commit/a438564eda1e0055484801c86c34a451fc4aefab))
- Delete the web UI ([8b760e2](https://github.com/outcomesinsights/seeds/commit/8b760e2458148f7674b4924ca102694c2efd74c6))
- Gate the CHANGELOG artifact, not just the generator ([a8ef784](https://github.com/outcomesinsights/seeds/commit/a8ef784604bc76a1647714b7d988f7843fadec86))

### Changed
- Declare ripgrep, which seeds search now needs at runtime ([3174b89](https://github.com/outcomesinsights/seeds/commit/3174b8972a6ad02e1c8e4a5f6ae1486053def1e7))

### Documentation
- A config above the store is shared state, and say so ([a03086b](https://github.com/outcomesinsights/seeds/commit/a03086b62d65d4d005e74be52d13a06e07acc680))
- List all seven shipped skills, and gate the list ([a110418](https://github.com/outcomesinsights/seeds/commit/a1104188a29369608df1ec15fe2686123080865f))
- Make seeds-to-beads write structured Source: lineage ([4328ca4](https://github.com/outcomesinsights/seeds/commit/4328ca42c2f76e4a6c8859fd7c97f48ae19b4433))
- Teach the cross-repo rg recipe, stop export over-claiming (seeds-4co.20) ([f28c596](https://github.com/outcomesinsights/seeds/commit/f28c59655724870ac3e33ef525207818814f901f))
- Mark the storage overhaul built and converted ([404a6b4](https://github.com/outcomesinsights/seeds/commit/404a6b493a6738104bfe2987b867b4fab7c312b5))
- Stop naming a function that no longer exists ([3468390](https://github.com/outcomesinsights/seeds/commit/34683904a74f77db4aaa72364f8a108845df57be))
- Point the command reference at the seed-file store ([2b17db5](https://github.com/outcomesinsights/seeds/commit/2b17db5be253371770e17642d62101f880a1f0b6))
- Drop the vestigial 'answers' relation type, and the six fixtures ([694b142](https://github.com/outcomesinsights/seeds/commit/694b1420f76b17aa744eeb341d50d901a4a66550))
- Rule empty bodies a smell, and give the prefix a home ([50b7646](https://github.com/outcomesinsights/seeds/commit/50b7646ca2386abf56b35c2dedf7f2058b84dc00))
- Freeze the on-disk storage format ([98a56ae](https://github.com/outcomesinsights/seeds/commit/98a56ae8e85bb1c5638aa8fbeee57ae55f6dbfb7))
- Settle ranked search, and fold three deletions into phase 5 ([861e6ac](https://github.com/outcomesinsights/seeds/commit/861e6ac08f3dc88602e64fb6f0d77b21cc7b2f7e))
- The storage overhaul plan, and settle the last five open items ([139847b](https://github.com/outcomesinsights/seeds/commit/139847b044fe8140649784199198eb48019b6411))

### Fixed
- Inherit formatter options from above the store ([0537b19](https://github.com/outcomesinsights/seeds/commit/0537b1992fe2513e4cbd03516fea938130a10251))
- Scalar quoting picks whichever form needs no escapes ([81fb86e](https://github.com/outcomesinsights/seeds/commit/81fb86ea400acc71a54f632e87b6faabc7c2bb3d))
- A body-less seed file ends at the closing delimiter ([5f5b36c](https://github.com/outcomesinsights/seeds/commit/5f5b36c20a41b1d46399ccae905142692d27ec97))
- Verify resolve-seeds-from-beads candidates against shipped code ([ade43d9](https://github.com/outcomesinsights/seeds/commit/ade43d9c507e85829368fee40d7213ffb0916066))
- Name the refusal cause instead of printing 0.6's traceback ([83b2265](https://github.com/outcomesinsights/seeds/commit/83b2265439119640b6c7d159d3e794a6dfbdb1f9))
- Read a legacy store missing an optional table as empty ([70e057a](https://github.com/outcomesinsights/seeds/commit/70e057a4e62722c7250b5726e5dd46228fa1df44))
- Bead the seed-lineage over-claim found in seeds-187's first real run ([e92a57b](https://github.com/outcomesinsights/seeds/commit/e92a57b698046868b6c566a165078896dfc62dee))
- Drop legacy 'answers' edges instead of crashing on them ([21a2b9e](https://github.com/outcomesinsights/seeds/commit/21a2b9e24228bd9109e4ac53f125fe391ea986fa))
- Confirm unknown bead refs with bd before rejecting them ([218c279](https://github.com/outcomesinsights/seeds/commit/218c27966f2dc459af1c20426db9a5b1ac3d3d9c))
- Exclude the seed store, which ruff started formatting on conversion ([56fcac6](https://github.com/outcomesinsights/seeds/commit/56fcac63868f11b3b8d6ea7723bea377ce2d7156))
- Make the converter assert it converted anything ([b2798fc](https://github.com/outcomesinsights/seeds/commit/b2798fc3988a983e01d60b6aabee0c5a8b545e26))
- Convert seeds-sdhc.1's floating supersede marker to a correction ([aeab343](https://github.com/outcomesinsights/seeds/commit/aeab3437b863a0ccb8645d78f587d2a4659fc6c7))
- Gate uv.lock against pyproject, and let Dependabot update it ([866086d](https://github.com/outcomesinsights/seeds/commit/866086dd9c2ccb5a4c66b7c4da78e2b397e21494))
- Restore the 83 titles clobbered by the attribution sweep ([1afc51c](https://github.com/outcomesinsights/seeds/commit/1afc51cdc59a5183e000308e1792ff44367f85b9))
- Regenerate uv.lock, stale since the mypy floor bump ([6b62a37](https://github.com/outcomesinsights/seeds/commit/6b62a37ae4b48c6c26fd50d03b3d423cdcec446a))

### Tooling
- Bump to 0.7.0a1 for the shakedown, and accept PEP 440 alphas ([c5d1628](https://github.com/outcomesinsights/seeds/commit/c5d162894717d60035b94e9c6cfd6ba765108c5f))
- One-off conversion-era audit of every store against its git history ([dfedd07](https://github.com/outcomesinsights/seeds/commit/dfedd07685b101da45b6c1fe43b762b4b87c12e9))
- Close seeds-4co.16, and correct my overclaim about canonical bytes ([0658fb9](https://github.com/outcomesinsights/seeds/commit/0658fb98b5af34c5cec0d1fd3d6fb39f4a6a4ad9))
- Resolve seeds-183 — cross-repo search is grep, and markdown serves it better ([43f173d](https://github.com/outcomesinsights/seeds/commit/43f173de52d4db94c4d709eb1a890d695d245c89))
- File the flake.nix dependency-mirror gap, resolve the web-UI seed ([1b292cf](https://github.com/outcomesinsights/seeds/commit/1b292cf480dfc4bebc0be139cda950f8db86bf7c))
- Update mypy requirement from >=2.3.0 to >=2.3.1 (#30) ([e789ac8](https://github.com/outcomesinsights/seeds/commit/e789ac8c1ab76d36911708e9f8f828ad6d0528ef))

## [0.6.0] - 2026-08-31

**This release is about failing loudly.** 0.5.0 stopped seeds destroying
deliberation silently; 0.6.0 stops it *losing* deliberation silently — and the
difference was found the hard way, by the project's first external bug report.

A user's sync had been broken for five weeks. An agent had written a seed type
the CLI does not accept directly into the JSONL, and the import aborted on that
line — so every record filed *below* it never reached the database, while every
record above it did. Nothing said so. `seeds doctor` reported healthy the entire
time, because its sync check compared file mtimes and never read the file. The
tool you run to ask "is my sync healthy?" was answering from a proxy that is
*anti-correlated* with this exact failure: a failed import leaves the JSONL
newer than the database, which is precisely the state it was calling clean.

Both halves are fixed. A record the import cannot read is now refused
**individually** and named — record number, id, failing field, reason — while
every other record lands, and the command exits non-zero so a script notices.
`doctor` no longer compares mtimes; it runs the same divergence check `sync`
does, so it is green exactly when `sync` would succeed rather than when a
timestamp happens to look right.

The type vocabulary that started it is open now. `seed_type` accepts any
string, `seeds update --type` fixes one, and `seeds retype` sweeps a typo across
the corpus. `SeedStatus` deliberately stays closed — status drives lifecycle
behaviour, so an unrecognised value there would break `ready`, `blocked` and the
resolve/defer/abandon transitions quietly rather than loudly.

### Breaking

- **Python 3.10 is no longer supported; the floor is 3.11.** 3.10 reaches
  end-of-life in October 2026, and seeds already required 3.11 in practice — it
  imports `enum.StrEnum`, so on 3.10 it had become an ImportError at startup for
  every command. ([6a70429](https://github.com/outcomesinsights/seeds/commit/6a7042910ff31c0f1b4983a5831199336b19fba2))
- **`seeds sync` refuses to flush** when it would change `.seeds/seeds.jsonl`
  while unrelated files are staged, rather than folding seed-database changes
  into whatever commit fires next. `--allow-mixed-stage` overrides.
  ([00ed416](https://github.com/outcomesinsights/seeds/commit/00ed4165ec26ce5edcfc22053e2ba119f886715e))
- **`seeds answer` refuses to overwrite a prior answer** instead of silently
  replacing it. ([89e6db0](https://github.com/outcomesinsights/seeds/commit/89e6db04590a19308f46ded9bc8594bcede20395))

### Upgrading

`seeds import` and `seeds sync` now **exit non-zero when any record was
refused**, where previously an unreadable record raised a traceback and stopped
the file. Scripts that treated a zero exit as "everything imported" were already
wrong — they just could not tell. If a sync starts reporting refusals, the
records it names have never been in your database; fix them in the JSONL and
re-run. `seeds doctor` now surfaces the same records before an import is run.

### Added

- Accept `seeds update` content from a file or stdin — `--content-file PATH` and
  `--content -` — so a long body no longer has to be quoted through argv
  ([d842efc](https://github.com/outcomesinsights/seeds/commit/d842efcaa02d7a991ece88a57305714186da68d4))
- `seeds retype --from X --to Y` bulk-remaps one seed type to another
  ([d21f7ba](https://github.com/outcomesinsights/seeds/commit/d21f7badc41aefe63db5551dc9a6f1cc5f18cb68))
- `seeds update --type` — a seed's type is no longer write-once
  ([c00bed0](https://github.com/outcomesinsights/seeds/commit/c00bed0b2ddc3ccdbaa9aff4da24c61693709dc2))
- The `seed_type` vocabulary accepts arbitrary strings
  ([15d3a6c](https://github.com/outcomesinsights/seeds/commit/15d3a6c3abf06469362f217490ac067e226dbdae))
- The bundled seeds-to-beads skill consults you before writing a bead;
  `--autonomous` opts out
  ([83e5f3c](https://github.com/outcomesinsights/seeds/commit/83e5f3c200f3c3f6e9ecbbf5fff4935a82acbb9f))
- `just changelog-coverage` gates a release on per-commit coverage rather
  than a count: every commit in the range must either render in the notes or
  match a deliberate skip rule in `cliff.toml`, and it names the ones that do
  neither. Replaces the count-based `changelog-audit`
  ([ac1cdc9](https://github.com/outcomesinsights/seeds/commit/ac1cdc9618f3258fdf1bc8fcbb6a4ee1fa6e6cad))

### Changed

- Python floor raised to 3.11 — see Breaking
  ([6a70429](https://github.com/outcomesinsights/seeds/commit/6a7042910ff31c0f1b4983a5831199336b19fba2))

### Fixed

- A malformed record is refused individually instead of aborting the import, so
  records below a bad line still land
  ([0c58123](https://github.com/outcomesinsights/seeds/commit/0c58123f006788a64daa9540d0a7d87748e8a265))
- `seeds doctor` agrees with `seeds sync` by construction, and names the record
  that breaks an import
  ([55bf114](https://github.com/outcomesinsights/seeds/commit/55bf1142d5e4a127060755bc0797c6501baff73d))
- `doctor` compares JSONL against the database instead of mtimes, and fails on
  divergence ([1600c37](https://github.com/outcomesinsights/seeds/commit/1600c372592dfd2a52b20c6d98d5ce6781033743))
- The divergence refusal no longer asks for a whole seed body through argv
  ([ccee855](https://github.com/outcomesinsights/seeds/commit/ccee8555fb2557b498b5d09779bfcc355e64a906))
- The divergence guard's guidance can now actually satisfy the guard
  ([54057b1](https://github.com/outcomesinsights/seeds/commit/54057b1546fa8b9c81b364cd97b3ab7823b86723))
- The content guard prints remediation for the command that raised it
  ([f6f010f](https://github.com/outcomesinsights/seeds/commit/f6f010f8e0eae581cb9ff6611e81483bd74c7cbf))
- A fresh clone is pointed at `seeds import` instead of being sent in a circle
  ([5589268](https://github.com/outcomesinsights/seeds/commit/5589268c02c7fd0045aeac25a8d1854bc02d0c29))
- Hyphenated queries search — FTS5 syntax characters are quoted
  ([46c63b8](https://github.com/outcomesinsights/seeds/commit/46c63b8883a7186b47474a03ceec9c56ece69159))
- `cliff.toml` no longer silently drops unhandled commit types
  ([e8320d2](https://github.com/outcomesinsights/seeds/commit/e8320d20c98d92a4bf413767d17f4732d79187f8))
- `cliff.toml` skips `docs(seeds…)` alongside `chore(seeds…)`, so edits to
  this repo's own seed database stop rendering as user documentation
  ([841a4dc](https://github.com/outcomesinsights/seeds/commit/841a4dc637f2e9cd9f95a43d0c34a1a149ee70c6))
- The release changelog uses an explicit tag range instead of
  `git-cliff --unreleased`, which dropped commits after a merge
  ([7cad77f](https://github.com/outcomesinsights/seeds/commit/7cad77f2bd4b6223ab52aa81042e487d30a614ee))
- Git test fixtures are sandboxed so they cannot poison the real repository
  ([3919c00](https://github.com/outcomesinsights/seeds/commit/3919c006760adbd72fdbccf40f73984acabaf096))
- The test sandbox has git, and two tests no longer assume a git checkout
  ([859aacd](https://github.com/outcomesinsights/seeds/commit/859aacd1882a7caaee4abb2001e98dd3efe8c300))

### Documentation

- Document the new content inputs and per-record import refusals; repair the
  changelog link references, which stopped at v0.3.3
  ([827a028](https://github.com/outcomesinsights/seeds/commit/827a0284d7b1f970d2d96a99daac310060fb70bf))
- Point the release checklist at `just bump-version`, which covers the two
  plugin manifests the old wording omitted
  ([161622b](https://github.com/outcomesinsights/seeds/commit/161622b9985998e4667e26b8c73746cf13351702))
- Split the global-CLI refresh by install method — `which seeds` decides
  between the nix profile and a `uv tool` install, since the nix profile
  precedes `~/.local/bin` on PATH and silently shadows the other
  ([260bc53](https://github.com/outcomesinsights/seeds/commit/260bc53c16f27e8fda73f48b70ed7f089224349e))
- Document `seeds import`, round-trip sync, and the fresh-clone path
  ([6336416](https://github.com/outcomesinsights/seeds/commit/6336416760a31d1af3138c8735643f2d46049c1c))
- Document the open type vocabulary, `update --type`, and `retype`
  ([a72ab29](https://github.com/outcomesinsights/seeds/commit/a72ab29fd1c41df645bc0f320e8db64ca8adc2a3))

<!-- Deliberate omissions from this section, so the release gate can tell them
     apart from work that went missing. See `just changelog-section`. Entries
     git-cliff put under Documentation or Tooling are pruned freely and need no
     marker; everything else does. -->
<!-- changelog-omit: 194cd3e superseded inside this release — 6a70429 raised the
     Python floor to 3.11, which retires the py310 ruff target-version that
     commit set, so it describes a state no released version was ever in -->

## [0.5.0] - 2026-08-10

This release is about one thing: **seeds now refuses to destroy deliberation
rather than doing it silently.** Four commands that previously succeeded can
now exit non-zero — every one of them at a moment where the old behaviour lost
work without saying so. That is why the minor version moves.

The headline is `seeds sync`. It imports, then rewrote the JSONL wholesale from
the database **without ever reading the file it was about to overwrite**. So a
routine sync could erase deliberation that was on disk and never in any
database — no clock skew required. The clearest case: machine B appends and
pushes; machine A appends later without pulling; a human resolves the git
conflict *in B's favour*; A runs `sync`; the import correctly skips B's line
and the export then overwrites the file with A's version. B's text is gone and
the human's explicit resolution is reverted, reported as `1 skipped` — which is
what every *unchanged* seed prints. The export now reads the file first and
refuses on divergence.

Timestamps were the second half. Records carried their `updated_at` verbatim
from the file, so a future-dated record became **permanently** authoritative:
every later local edit stamps `now`, which is *earlier*, so the poisoned record
out-ranked real work forever and each import destroyed whatever had been typed
since. Records dated beyond a small skew tolerance are now refused outright, and
a timezone-naive timestamp no longer aborts an import mid-file.

`seeds update -c` got the same treatment at a smaller scale: one character from
`-a`, it replaced a seed's whole body with no warning. It now refuses once a
seed has accumulated deliberation, unless you mean it.

### Breaking

- **`seeds sync` / `sync --flush-only` refuse to overwrite divergent JSONL.** Pass `--allow-divergence` to discard the on-disk content deliberately ([bfb518e](https://github.com/outcomesinsights/seeds/commit/bfb518ec98804e9af3d197ebef601fc985ba64cf))
- **`seeds import` refuses records dated more than 5 minutes in the future.** They are reported, and the database is left unchanged ([0a867dd](https://github.com/outcomesinsights/seeds/commit/0a867dd01ef44d43602b94353497d66b5db607e7))
- **`seeds update -c` refuses on a seed that has been edited.** Use `-a` to append, or `--replace` to discard on purpose. Note `--replace` does not erase anything — the old body survives in git history ([03f3af3](https://github.com/outcomesinsights/seeds/commit/03f3af324be5acbef88200edad0dc5b5e8102327))
- **`seeds create` / `update` now reject unknown base36 ID references.** Hash-shaped references like `seeds-zq4x` were previously invisible to the hallucinated-ID check, which is the scheme every new ID uses. `--allow-unknown-refs` still overrides ([fd778ed](https://github.com/outcomesinsights/seeds/commit/fd778edd3632d058ef3a4556aa3e20c9eaab7b8a))

### Added

- `--add-tag` / `--remove-tag` on `seeds update`, both repeatable. Removing a tag a seed does not carry is a silent no-op reporting the count, so a typo shows as "0 removed" rather than failing mid-batch. Wholesale `--tags` is unchanged ([d7d678b](https://github.com/outcomesinsights/seeds/commit/d7d678b3d41751f19d5268ae9f34d3b03ea08c2c))

### Fixed

- Bead IDs count as known references in seed bodies. Beads share the `seeds-` prefix, so every legitimate bead citation previously failed seed creation and had to be worked around with `--allow-unknown-refs` ([e2f7b64](https://github.com/outcomesinsights/seeds/commit/e2f7b6472feac64ee0df4471d6c94421bddaf075))

### Changed

- `seeds suggest --json` emits compact JSON. The flag's purpose is agent piping, where indentation is tokens the model pays for — 21% smaller on a live query. Pipe through `jq` to read it ([c20d7db](https://github.com/outcomesinsights/seeds/commit/c20d7db32e5a84e093cad24e9f34265c83feff0f))

## [0.4.0] - 2026-07-27

This release makes seeds installable with **Nix**, and finishes the base36 ID
transition that 0.3.5 began by removing the one command that could undo it.

The minor version moves for the first time since 0.3.0. The 0.x convention
here is that features ship as patch bumps, so `0.4.0` is a deliberate signal
rather than a routine increment: a command has been **removed**, and anyone
scripting against `seeds migrate-ids` will break.

`flake.nix` means `nix run github:outcomesinsights/seeds` works with no
install at all, and Nix users can pin seeds as a flake input instead of
hand-writing a derivation. It also exposes an `overlays.default` for
home-manager configs, a `devShells.default` giving contributors a pinned
Python + uv + ruff toolchain, and a `checks.default` that runs the test
suite. Tests deliberately live in `checks` rather than gating the package,
so consumers building from source don't pay for a full pytest run. A CI job
builds the flake on every push — an untested flake is a broken promise.

The headline fix is a data-integrity bug in `rename-prefix`. It decided which
IDs to rename with a numeric-only shape test written when every ID was
sequential. Base36 includes `0-9`, so a hash like `seeds-060` parsed as a
number and was renamed while `seeds-k3n7` was skipped — same scheme, opposite
outcome, decided by the random content of the hash. On a real database that
left a **split-prefix state**: some seeds renamed, hash-ID seeds stranded
under the old prefix, while the configured prefix reported the new one. Both
schemes are now renamed, and body references were taught base36 too.

**Breaking:** `seeds migrate-ids` is gone, with no deprecation shim. It
migrated hash IDs *to* sequential — backwards since 0.3.5 made base36 hash
IDs the standard. Because it detected work by testing whether an ID parsed
as a number, every base36 ID read as un-migrated, and a single one was enough
to renumber an **entire** database from 1. The migration was one-time, that
transition has concluded, and the command could now only do harm.

### Added

- Add flake so seeds is installable via Nix ([fa8dbb8](https://github.com/outcomesinsights/seeds/commit/fa8dbb872ed69bb177d523ba7d66634e110b087d))

### Fixed

- Rename-prefix must rename base36 hash IDs, not just numeric ones ([16b814d](https://github.com/outcomesinsights/seeds/commit/16b814d5bdcbde5592e894e59c181376020e5901))
- Drop x86_64-darwin, which nixpkgs 26.11 removed ([86790ae](https://github.com/outcomesinsights/seeds/commit/86790aee13806184dad6ff7a2f4f21ee4501eedd))

### Removed

- **Breaking:** remove migrate-ids and migrate_to_sequential_ids ([5cab711](https://github.com/outcomesinsights/seeds/commit/5cab7115832e2c100b458ea152aef9f0d8b8e75c))

### Tooling

- Add nix job so the flake can't silently rot ([1426a9f](https://github.com/outcomesinsights/seeds/commit/1426a9f5e173e90067043475f82130e7906f9232))
- Don't let `--all-systems` attempt cross-arch builds ([70151c7](https://github.com/outcomesinsights/seeds/commit/70151c74e078eaff1dc8ffc3496f45d65ade4587))

## [0.3.5] - 2026-07-17

This release changes how new seed IDs are minted: from a sequential counter
(`seeds-1`, `seeds-2`, …) to short, collision-resistant **base36 hash IDs**
(`seeds-k3n`), adopted whole-cloth from beads. The sequential scheme derived
each next number by scanning the local store, so the same git-backed repo
worked from two machines could mint the same ID on each and collide when the
JSONL merged; hash IDs need no shared counter, so that whole class of
collision is gone. Existing IDs are **grandfathered** — nothing is renumbered
and there is no migration. Suffix length scales with store size (3 characters
in a fresh store, 4 once it grows), keeping IDs as short and typeable as the
sequential ones they replace.

### Added

- Switch next_id() to base36 hash IDs (seeds-mlj) ([5a8346a](https://github.com/outcomesinsights/seeds/commit/5a8346a3587cd673e87ff58b0e7237e09a52e9e4))
- Add base36 hash-ID generator module ([9e5ca96](https://github.com/outcomesinsights/seeds/commit/9e5ca9669229016cde716fdcf6ed7001e2860dd2))

### Fixed

- Recover_prefix_from_id handles base36 hash IDs (fresh-clone bootstrap) ([ca89711](https://github.com/outcomesinsights/seeds/commit/ca89711b4eaefcc29ac2d7c057137e76beb0a25a))

## [0.3.4] - 2026-07-16

This release adds a new output mode: turning a matured seed into a *trellis*.

`seeds trellis <id> --to <file> --as "<principle>"` distills a resolved seed's
deliberation into one crisp, bounded principle and writes it — with a two-way
provenance link — into durable, always-on project context such as `CLAUDE.md`
or `README`, then resolves the seed. A trellis is a load-bearing principle
you want every future session steered by; it lives in the context the agent
runtime injects each session, not in anything seeds surfaces internally. A
companion `seeds:trellis` skill supplies the language judgment — distilling the
one-line principle and advising the target file — and fires when you say
"promote this" or "make this a trellis". The verb's bookkeeping stays
deterministic (a provenance bullet under a `## Principles` section, a
`trellis` tag, and resolution), and README and CLAUDE.md explain when to
reach for it.

This release also **drops Python 3.9** (end-of-life; `requires-python` is now
`>=3.10`) and refreshes the dev toolchain — mypy 2.3, pytest 9.1, ruff 0.15.22,
and pre-commit 4.6.

## [0.3.3] - 2026-06-24

This release rounds out the seeds↔beads workflow and makes JSONL import a
first-class, round-trippable operation.

On the workflow side, the bundled skills now carry intent in both directions.
`seeds-to-beads` records the *why* behind each bead — locked decisions and their
rationale, verbatim stakeholder voice on subjective calls, and seed lineage —
and suggests a short efficacy note to capture when the work is done. A new
`resolve-seeds-from-beads` skill closes the loop: after an implementation
session it reconciles what actually shipped back into the originating seeds,
captures that efficacy note, and resolves them.

On the data side, `seeds import` lands with last-write-wins upsert semantics, a
fresh-clone bootstrap, and prefix recovery, so a seeds database can be rebuilt
from its JSONL export and synced round-trip without drift.

### Added

- **`seeds import [PATH|-]` with round-trip `seeds sync`.** Import seeds from a
  JSONL file or stdin; export and re-import are now lossless, enabling
  backup/restore and cross-clone sync.
- **Fresh-clone bootstrap + prefix recovery on import.** A freshly cloned repo
  with only its JSONL export can reconstruct a working database, recovering the
  project's seed-ID prefix.
- **Last-write-wins upsert for import.** Re-importing reconciles by `updated_at`
  and reports an `ImportResult` summary instead of duplicating or clobbering.
- **Executor intent in the `seeds-to-beads` skill.** Converted beads now record
  locked decisions + their rationale, verbatim stakeholder voice, and seed
  lineage — separating motivation from constraints.
- **Efficacy note suggested at seed resolution.** `seeds-to-beads` now proposes
  a short qualitative note (tweaking needed? planning-miss vs inherent unknown?)
  to capture when the originating seed is resolved.
- **New `resolve-seeds-from-beads` skill.** The symmetric bookend to
  `seeds-to-beads`: reconcile deliberation against what shipped, capture the
  efficacy note, and resolve the seeds.

### Documentation

- Added the intent-debt investigation and feedback-response notes under `docs/`.

### Tooling

- Beads now exports `issues.jsonl` on commit via a hook.
- Relocked ruff (0.15.14 → 0.15.16); raised the requirement floor to >=0.15.15.

## [0.3.2] - 2026-06-04

A correctness release for the Claude Code skills installer. `seeds skills
install` now guarantees the plugin ends up *enabled*, so the bundled `seeds:*`
skills actually load in new Claude Code sessions — previously the plugin could
install but sit disabled, silently contributing nothing. Clean package builds
are restored, and the version is now single-sourced so the CLI and the plugin
manifests can no longer drift apart.

### Fixed

- **`seeds skills install` now enables the plugin.** The command registered the
  marketplace and installed the plugin but never enabled it, so it could remain
  `disabled` in `~/.claude/settings.json` and load none of its skills. It now
  runs `claude plugin enable` on every install/update. A new `--reinstall`
  (alias `--upgrade`) flag refreshes the marketplace from source and replaces a
  stale cached copy after the seeds CLI itself is upgraded.
- **Clean wheel builds.** A redundant hatchling `force-include` re-mapped the
  bundled plugin files to wheel paths already provided by `packages`, so any
  build from a clean cache failed with a "same path" collision. Removing it
  fixes `uv build` / `uv tool install`.
- **Beads pre-commit hook.** Set `BD_GIT_HOOK=1` in the pre-commit entry to
  avoid a `.git/index.lock` race during beads' auto-export.

### Tooling

- **Single-sourced the package version.** `pyproject.toml` now derives the
  version from `src/seeds/__init__.py` (hatchling dynamic version); the two
  plugin manifests are kept in lockstep by `just bump-version`, guarded by a
  test that fails the build on drift. Previously the version lived in four
  hand-edited places and had already drifted (plugin manifests at 0.2.0 while
  the CLI was 0.3.1).

## [0.3.1] - 2026-05-27

First Claude Code skills shipped with seeds. The new `seeds skills install`
command registers a bundled local marketplace and installs the `seeds` plugin
under the `seeds:*` namespace (mirroring the `beads:*` pattern). Two
prompt-macro skills ship in this release; see `seeds-152` and its sub-seeds in
the seed database for the deliberation that produced them.

### Added

- **`seeds skills install`** — registers the bundled Claude Code plugin
  marketplace and installs (or updates) the `seeds` plugin under the user
  scope. Idempotent; safe to re-run after `uv tool upgrade seeds`.
- **`seeds:feedback` skill** — prompt-macro that frames the next user message
  as feedback on the agent's prior turn, then has the agent invite further
  questions, comments, or criticisms exactly once. Per the deliberation that
  produced it, the closer's value comes from being user-initiated; the skill
  explicitly scopes the invitation to the single reply being generated rather
  than installing it as ongoing agent behavior.
- **`seeds:seeds-to-beads` skill** — prompt-macro for converting deliberated
  seeds into a set of beads suitable for execution by a Sonnet-based agent.
  Encodes principles for separating actionable scope from context, embedding
  content templates in bead descriptions, writing mechanical acceptance
  criteria, and setting explicit dependencies.
- **Claude Code plugin tree** under `src/seeds/plugin/` — `seeds-marketplace`
  + `seeds` plugin manifests for local distribution. Bundled with the Python
  package via Hatchling's `force-include`.

### Documentation

- README section describing the Claude Code skills and the install command.

## [0.3.0] - 2026-05-18

Discovery and dedup primitives aimed at the recurring transcript-incorporation
workflow (see `seeds-142` in the seed database for the use-case write-up).

### Added

- **`seeds prime` digest** — appends counts, recently-updated seeds, active
  exploration, open questions, and top tag clusters after the static workflow
  text. Bodies are intentionally omitted; agents `seeds show <id>` for detail.
  Flags: `--no-digest`, `--digest-limit=N`.
- **`seeds suggest "<text>"`** — natural-language dedup query. Ranks existing
  seeds by FTS5 BM25 over title/content/tags/resolution, with multiplicative
  tag-overlap and recency boosts and a dynamic noise floor (drops hits below
  half the top score). Includes resolved/abandoned by default — the question
  is "does this idea exist in our deliberation history?", not "what can I edit
  right now". Flags: `--limit=N`, `--open-only`, `--json`.
- **`seeds list --since=<date>` / `--sort=updated|created`** — surfaces "what
  changed since X" as a first-class CLI primitive instead of forcing agents to
  derive it from `updated_at` timestamps inside seed bodies. Accepts ISO dates
  (`2026-05-08`), relative shorthand (`7d`, `2w`, `3m`, `1y`), and
  `today`/`yesterday`.
- **`seeds recent`** — thin alias for `seeds list --since=7d --sort=updated`.
- **Cross-reference validation on `seeds create` / `seeds update`** —
  rejects bodies that reference unknown `<prefix>-N` IDs (catches the
  hallucinated-cross-reference failure mode). Pass `--allow-unknown-refs` to
  override.

### Changed

- `seeds prime` command help reorganised: `suggest`, `search`, `recent` now
  sit alongside `ready`/`questions`/`deferred`/`blocked` in "Finding Work".

### Tooling

- Pre-push hook wired via pre-commit framework: runs mypy, ruff check, ruff
  format --check, pytest, plus beads pre-push. Matches the GitHub Actions
  lint+test jobs so CI on remote becomes the last line of defense rather
  than the first.
- ruff-pre-commit pin bumped v0.4.0 → v0.15.13 to match the local `uv` ruff
  version (the older pin disagreed with current isort defaults).
- Dev deps migrated from the deprecated `[tool.uv] dev-dependencies` field
  to PEP 735 `[dependency-groups] dev`.
- 359 tests (was 300).

## [0.2.1] - 2026-05-14

Configurable project prefix for seed IDs and supporting `rename-prefix`
improvements. This version was bumped in code but not tagged as a GitHub
release; its features shipped to users as part of v0.3.0.

### Added

- **Configurable project prefix** (`seeds-5at`) — `seeds init --prefix` and
  `seeds rename-prefix <new>` to change the prefix used on seed IDs after
  the fact. `seeds prefix` prints the current value.
- **`seeds rename-prefix --dry-run`** (`seeds-d7o`) — preview ID renames
  and body-reference rewrites without writing.
- **Body-reference rewriting** during `rename-prefix` — IDs mentioned inside
  seed titles/content/resolution are updated alongside the structural rename.
  Use `--no-rewrite-bodies` to skip.

### Documentation

- Added `docs/working-with-seeds.md` — primer + blog workflow.
- Clarified the design-database protection rule in `CLAUDE.md`.

## [0.2.0] - 2026-04-28

### Added

- **Typed relationships** between seeds (Phases 1 + 2): infrastructure +
  CLI/export/web wiring.
- **Sequential IDs** replacing random hashes, with migration of existing
  seeds.
- **Resolution field** to capture what happened when a seed is resolved.
- **Full-text search (FTS5)** across seeds and questions.

### Removed

- Deprecated `Question` / `QuestionStatus` and legacy DB columns.

### Tooling

- ruff lint cleanup, pre-commit hook wiring, beads hook shims to v0.61.0.

### Dependencies

- `click>=8.1.8`
- `flask>=3.1.3`

## [0.1.0] - 2026-02-27

Initial public beta release.

### Added

- **Seed lifecycle**: captured → exploring → resolved/abandoned/deferred
- **Quick capture**: `seeds jot` for minimal-friction idea capture
- **Hierarchical seeds**: parent/child organization with dotted IDs (e.g., `seed-a1b2.1`)
- **Blocking semantics**: seeds with unresolved children cannot be resolved
- **Attached questions**: first-class question objects with open/answered/deferred lifecycle
- **Tagging**: comma-separated tags with filtering support
- **Relationships**: bidirectional `seeds link` for loose coupling between seeds
- **JSONL export**: git-trackable export via `seeds sync --flush-only`
- **AI context**: `seeds prime` command for agent workflow injection
- **Navigation commands**: `seeds ready`, `seeds blocked`, `seeds deferred`, `seeds questions`
- **Experimental web UI**: `seeds serve` for read-only browsing of seeds and questions
- **Doctor command**: `seeds doctor` for installation health checks

[Unreleased]: https://github.com/outcomesinsights/seeds/compare/v0.7.0a5...HEAD
[0.7.0a5]: https://github.com/outcomesinsights/seeds/compare/v0.7.0a4...v0.7.0a5
[0.7.0a4]: https://github.com/outcomesinsights/seeds/compare/v0.7.0a3...v0.7.0a4
[0.7.0a3]: https://github.com/outcomesinsights/seeds/compare/v0.7.0a2...v0.7.0a3
[0.7.0a2]: https://github.com/outcomesinsights/seeds/compare/v0.6.0...v0.7.0a2
[0.6.0]: https://github.com/outcomesinsights/seeds/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/outcomesinsights/seeds/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/outcomesinsights/seeds/compare/v0.3.5...v0.4.0
[0.3.5]: https://github.com/outcomesinsights/seeds/compare/v0.3.4...v0.3.5
[0.3.4]: https://github.com/outcomesinsights/seeds/compare/v0.3.3...v0.3.4
[0.3.3]: https://github.com/outcomesinsights/seeds/compare/v0.3.2...v0.3.3
[0.3.2]: https://github.com/outcomesinsights/seeds/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/outcomesinsights/seeds/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/outcomesinsights/seeds/compare/v0.2.0...v0.3.0
[0.2.1]: https://github.com/outcomesinsights/seeds/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/outcomesinsights/seeds/releases/tag/v0.2.0
[0.1.0]: https://github.com/outcomesinsights/seeds/releases/tag/v0.1.0
