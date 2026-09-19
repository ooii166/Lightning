// Reproducible build: compile ArcFlow.sol with solc 0.8.20 and emit artifact JSON.
// Run:  node deploy/compile.js
const fs = require('fs');
const path = require('path');

const solc = require('solc');
const ROOT = path.resolve(__dirname, '..');
const SRC = path.join(ROOT, 'contracts', 'ArcFlow.sol');
const OUT = path.join(__dirname, 'arcflow_artifact.json');

const source = fs.readFileSync(SRC, 'utf8');

const input = {
  language: 'Solidity',
  sources: { 'ArcFlow.sol': { content: source } },
  settings: {
    optimizer: { enabled: true, runs: 200 },
    outputSelection: { '*': { '*': ['abi', 'evm.bytecode.object', 'evm.deployedBytecode.object'] } },
  },
};

const output = JSON.parse(solc.compile(JSON.stringify(input)));

let hadError = false;
if (output.errors) {
  for (const e of output.errors) {
    const msg = e.formattedMessage || e.message;
    if (e.severity === 'error') { hadError = true; console.error('ERROR:', msg); }
    else console.warn('WARN:', msg);
  }
}

if (hadError) { console.error('Compilation failed.'); process.exit(1); }

const contracts = output.contracts['ArcFlow.sol'];
const name = Object.keys(contracts)[0];
const c = contracts[name];
const artifact = {
  contractName: name,
  compiler: 'solc 0.8.20+commit.a1b79de6',
  bytecode: '0x' + c.evm.bytecode.object,
  deployedBytecode: '0x' + c.evm.deployedBytecode.object,
  abi: c.abi,
  bytecodeSize: c.evm.bytecode.object.length / 2,
  generatedAt: new Date().toISOString(),
};
fs.writeFileSync(OUT, JSON.stringify(artifact, null, 2));
console.log('Compiled', name);
console.log('  bytecode size:', artifact.bytecodeSize, 'bytes');
console.log('  abi functions:', c.abi.filter(x => x.type === 'function').map(x => x.name).join(', '));
console.log('  artifact ->', OUT);
