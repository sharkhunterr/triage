#!/usr/bin/env node
/**
 * Triage release script (same flow as the sibling projects).
 *
 * - Checks that GITHUB_RELEASES.md opens with the notes of the version about to be released (`# vX.Y.Z`):
 *   those notes are the GitLab and GitHub release pages — write them first, with their « Closed issues »
 *   (`npm run release:issues` lists them by kind; the first release, with no earlier tag, has none).
 * - Bumps the version with standard-version (package.json, the frontend's package.json + lock, the
 *   backend's pyproject.toml + uv.lock + openapi.json), writes CHANGELOG.md, commits, tags `vX.Y.Z`.
 * - Pushes to GitLab with the tag: the tag pipeline validates, tests and builds; with --deploy it also
 *   publishes the image to Docker Hub, mirrors to GitHub and creates the releases.
 *
 * Usage:
 *   npm run release              # bump + tag + push to GitLab (pipeline: validate, test, build, GitLab release)
 *                                # the version is the one GITHUB_RELEASES.md announces when it is above the
 *                                # current one (v0.1.0 first); otherwise the commits decide (feat → minor…)
 *   npm run release:full         # + Docker Hub, GitHub mirror and GitHub release; on a version already
 *                                # released (HEAD is its tag), publishes it without a new version
 *   npm run release:minor        # force the bump (patch | minor | major)
 *   npm run release:dry          # what would happen, nothing changed
 *   npm run release:notes        # print the notes the release pages will show
 *   npm run release:issues       # the issues closed since the last tag, by kind, for the notes
 *
 * Options: --github --deploy --dry-run --skip-push --skip-notes-check --no-gitlab, patch|minor|major
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const NOTES_FILE = path.join(ROOT, 'GITHUB_RELEASES.md');

const args = process.argv.slice(2);
const options = {
  github: args.includes('--github'),
  gitlab: !args.includes('--no-gitlab'),
  deploy: args.includes('--deploy'),
  dryRun: args.includes('--dry-run'),
  skipPush: args.includes('--skip-push'),
  skipNotesCheck: args.includes('--skip-notes-check'),
  notesOnly: args.includes('--notes'),
  releaseType: args.find((arg) => ['patch', 'minor', 'major'].includes(arg)) || null,
};

function run(command, description) {
  console.log(`\n> ${description}`);
  if (options.dryRun) {
    console.log(`  [dry run] ${command}`);
    return '';
  }
  try {
    return execSync(command, { encoding: 'utf8', stdio: 'inherit', cwd: ROOT });
  } catch {
    console.error(`x Failed: ${description}`);
    process.exit(1);
  }
}

function remoteUrl(remote) {
  try {
    return execSync(`git remote get-url ${remote}`, { encoding: 'utf8', cwd: ROOT }).trim();
  } catch {
    return null;
  }
}

/** The first `# vX.Y.Z` block of GITHUB_RELEASES.md — what the CI posts — and its version. */
function latestNotes() {
  if (!fs.existsSync(NOTES_FILE)) return { version: null, notes: '' };
  const lines = fs.readFileSync(NOTES_FILE, 'utf8').split('\n');
  let version = null;
  const body = [];
  for (const line of lines) {
    const heading = line.match(/^# v(\d+\.\d+\.\d+)\s*$/);
    if (heading) {
      if (version) break;
      version = heading[1];
      continue;
    }
    if (version) body.push(line === '---' ? '' : line);
  }
  return { version, notes: body.join('\n').replace(/\n{3,}/g, '\n\n').trim() };
}

/** No release tag yet: the first release has no « Closed issues » to list. */
function firstRelease() {
  try {
    execSync('git describe --tags --abbrev=0 --match "v[0-9]*"', { cwd: ROOT, stdio: 'ignore' });
    return false;
  } catch {
    return true;
  }
}

/** The release tag on HEAD (`vX.Y.Z`), if HEAD is a release. */
function tagAtHead() {
  try {
    return execSync('git describe --tags --exact-match --match "v[0-9]*" HEAD', {
      encoding: 'utf8',
      cwd: ROOT,
      stdio: ['ignore', 'pipe', 'ignore'],
    }).trim();
  } catch {
    return null;
  }
}

/** A version already released (`npm run release`) but not published yet: its tag's pipeline runs again
 * with DEPLOY=true — Docker Hub, GitHub mirror and release —, no new version. The release jobs are
 * idempotent: the GitLab release is kept, the GitHub one created or updated. */
function publishTag(tag) {
  const pushed = execSync(`git ls-remote --tags origin ${tag}`, { encoding: 'utf8', cwd: ROOT }).trim();
  if (!pushed && !options.dryRun) {
    run(`git push origin ${tag}`, `Pushing ${tag} to GitLab`);
  }
  let glab = true;
  try {
    execSync('glab version', { cwd: ROOT, stdio: 'ignore' });
  } catch {
    glab = false;
  }
  if (!glab) {
    console.error(
      `\nx glab is not installed: run the ${tag} pipeline by hand (GitLab › Build › Pipelines › Run pipeline,\n` +
        `  ref ${tag}, variable DEPLOY = true).`,
    );
    process.exit(1);
  }
  run(`glab ci run --branch ${tag} --variables DEPLOY:true`, `Publishing ${tag} (its pipeline with DEPLOY=true)`);
  console.log(`\nPublishing ${tag}: Docker Hub, GitHub mirror and release.`);
}

/** a > b, both `X.Y.Z`. */
function above(a, b) {
  const [x, y] = [a, b].map((v) => v.split('.').map(Number));
  for (let i = 0; i < 3; i += 1) if (x[i] !== y[i]) return x[i] > y[i];
  return false;
}

/** What standard-version is told: the bump asked for, else the version the notes announce when it is above
 * the current one (the notes are written first: they say which release this is), else nothing — the
 * commits decide. */
function releaseAs(notesVersion) {
  if (options.releaseType) return options.releaseType;
  const current = JSON.parse(fs.readFileSync(path.join(ROOT, 'package.json'), 'utf8')).version;
  return notesVersion && above(notesVersion, current) ? notesVersion : null;
}

/** The version standard-version is about to write (from its dry run). */
function nextVersion(as) {
  let command = 'npx --no-install standard-version --dry-run 2>&1';
  if (as) command = command.replace(' 2>&1', ` --release-as ${as} 2>&1`);
  const output = execSync(command, { encoding: 'utf8', cwd: ROOT, stdio: ['ignore', 'pipe', 'pipe'] });
  const match = output.match(/bumping version in \S+ from \S+ to (\d+\.\d+\.\d+)/);
  if (!match) throw new Error('could not tell the next version from standard-version');
  return match[1];
}

function main() {
  const { version: notesVersion, notes } = latestNotes();
  if (options.notesOnly) {
    console.log(notesVersion ? `# v${notesVersion}\n\n${notes}` : 'GITHUB_RELEASES.md has no `# vX.Y.Z` block.');
    return;
  }

  console.log('Triage release');
  console.log('Options:', options);

  const status = execSync('git status --porcelain', { encoding: 'utf8', cwd: ROOT });
  if (status && !options.dryRun) {
    console.error('x The working tree is not clean: commit or stash first.');
    process.exit(1);
  }
  const branch = execSync('git rev-parse --abbrev-ref HEAD', { encoding: 'utf8', cwd: ROOT }).trim();
  const gitlab = remoteUrl('origin');
  console.log(`\nBranch: ${branch}`);
  console.log(`GitLab: ${gitlab || 'not configured'}`);
  if (options.gitlab && !gitlab) {
    console.error('x The GitLab remote (origin) is not configured.');
    process.exit(1);
  }

  // 0. HEAD is already a release (`npm run release` then `npm run release:full`): publish it, no new version
  const released = tagAtHead();
  if (released && !options.releaseType) {
    if (options.deploy && options.gitlab) {
      console.log(`\n${released} is already released: publishing it.`);
      publishTag(released);
      if (gitlab) console.log(`Pipeline: ${gitlab.replace(/\.git$/, '')}/-/pipelines`);
      return;
    }
    console.error(
      `\nx HEAD is already ${released}: nothing to release.\n` +
        '  `npm run release:full` publishes it (Docker Hub, GitHub); commit something new for the next version.',
    );
    process.exit(1);
  }

  // 1. the release notes come first
  const as = releaseAs(notesVersion);
  const next = nextVersion(as);
  console.log(`\nNext version: v${next}`);
  if (!options.skipNotesCheck) {
    if (notesVersion !== next || !notes) {
      console.error(
        `\nx GITHUB_RELEASES.md must open with the notes of v${next} (found: ${notesVersion ? `v${notesVersion}` : 'none'}).\n` +
          `  Add a "# v${next}" block at the top (English, see the template in the file), commit it, then release again.`,
      );
      process.exit(1);
    }
    if (!firstRelease() && !/^### Closed issues\s*$/m.test(notes)) {
      console.error(
        `\nx The notes of v${next} have no "### Closed issues" part.\n` +
          '  Run `npm run release:issues`, rewrite its lines in English in the notes, commit, then release again.',
      );
      process.exit(1);
    }
    console.log(`Release notes: v${next} (${notes.split('\n').length} lines)`);
  }

  // 2. bump, changelog, commit, tag
  let bump = 'npx --no-install standard-version';
  if (as) bump += ` --release-as ${as}`;
  if (options.dryRun) bump += ' --dry-run';
  run(bump, 'Bumping the version (standard-version)');
  if (options.dryRun) {
    console.log('\nDry run: nothing changed.');
    return;
  }
  const tag = `v${JSON.parse(fs.readFileSync(path.join(ROOT, 'package.json'), 'utf8')).version}`;

  // 3. push with the tag: the tag pipeline does the rest
  if (!options.skipPush && options.gitlab) {
    const ci = options.deploy ? ' -o ci.variable="DEPLOY=true"' : '';
    run(`git push origin ${branch} --follow-tags${ci}`, `Pushing ${branch} and ${tag} to GitLab`);
    if (options.github && !options.deploy) {
      console.log('\nNote: the GitHub mirror and release are made by the pipeline with --deploy (release:full).');
    }
  }

  console.log(`\nReleased ${tag}.`);
  if (gitlab) console.log(`Pipeline: ${gitlab.replace(/\.git$/, '')}/-/pipelines`);
}

try {
  main();
} catch (error) {
  console.error(`\nx Release failed: ${error.message}`);
  process.exit(1);
}
