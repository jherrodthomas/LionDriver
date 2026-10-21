// TE-03 step P3: render FRET's own Kind 2 realizability contract (support/RealizabilityTemplates/kind2/Complete.ejs)
// with FRET's EJS engine, from a JSON contract on stdin; the Lustre goes to stdout.
// Usage: node render_contract.js <FRET_DIR> < contract.json > contract.lus
// The templates use the legacy `<%- include ./path %>` form, which EJS 3 no longer accepts, so it is rewritten to
// `include("<FRET_DIR>/path")` before rendering. Nothing else is changed.
'use strict';
const fs = require('fs');
const path = require('path');

const fretDir = path.resolve(process.argv[2]);
const ejs = require(path.join(fretDir, 'node_modules', 'ejs'));

function load(file) {
  return fs.readFileSync(file, 'utf8').replace(/<%-\s*include\s+\.\/(\S+)\s*%>/g,
    (_, rel) => `<%- include(${JSON.stringify(path.join(fretDir, rel))}) %>`);
}

const contract = JSON.parse(fs.readFileSync(0, 'utf8'));
const complete = path.join(fretDir, 'support', 'RealizabilityTemplates', 'kind2', 'Complete.ejs');
const out = ejs.render(load(complete), contract, {
  filename: complete,
  includer: (original, parsed) => ({template: load(parsed || original)}),
});
process.stdout.write(out);
