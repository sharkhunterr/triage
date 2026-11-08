/** standard-version updater for `backend/uv.lock`: the project's own entry (keeps `uv sync --locked`
 * happy after a bump). */
const versionRegex = /(\[\[package\]\]\nname = "triage"\nversion = ")([^"]+)(")/;

module.exports.readVersion = (contents) => {
  const match = contents.match(versionRegex);
  if (!match) throw new Error('No triage package in uv.lock');
  return match[2];
};

module.exports.writeVersion = (contents, version) => contents.replace(versionRegex, `$1${version}$3`);
