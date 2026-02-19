#!/usr/bin/env node

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const printUsage = () => {
  process.stdout.write(
    [
      'Usage: trash.ts [--allow-missing] <path> [path ...]',
      '',
      'Move files/directories to OS Trash (does not permanently delete).',
      '',
      'Options:',
      '  -f, --allow-missing   Ignore missing paths',
      '  -h, --help            Show this help',
      '',
    ].join('\n')
  );
};

const getTrashDir = () => {
  const home = os.homedir();
  if (process.platform === 'darwin') {
    return path.join(home, '.Trash');
  }
  return path.join(home, '.local', 'share', 'Trash', 'files');
};

const ensureDirSync = (dirPath) => {
  fs.mkdirSync(dirPath, { recursive: true });
};

const uniqueDestPathSync = (trashDir, originalName) => {
  const base = path.basename(originalName);
  const ext = path.extname(base);
  const stem = ext ? base.slice(0, -ext.length) : base;

  let candidate = path.join(trashDir, base);
  if (!fs.existsSync(candidate)) {
    return candidate;
  }

  const nonce = Date.now();
  for (let attempt = 1; attempt < 10_000; attempt += 1) {
    candidate = path.join(trashDir, `${stem}-${nonce}-${attempt}${ext}`);
    if (!fs.existsSync(candidate)) {
      return candidate;
    }
  }

  throw new Error(`Unable to find free Trash destination for ${base}`);
};

const moveSync = (sourcePath, destinationPath) => {
  try {
    fs.renameSync(sourcePath, destinationPath);
  } catch {
    const stats = fs.lstatSync(sourcePath);
    fs.cpSync(sourcePath, destinationPath, {
      recursive: stats.isDirectory(),
      errorOnExist: true,
    });
    fs.rmSync(sourcePath, { recursive: stats.isDirectory(), force: true });
  }
};

const movePathsToTrash = (targets, cwd, options = {}) => {
  const result = {
    moved: [],
    missing: [],
    errors: [],
  };

  const trashDir = getTrashDir();
  ensureDirSync(trashDir);

  for (const target of targets) {
    const trimmed = String(target).trim();
    if (!trimmed) {
      continue;
    }

    const absolutePath = path.isAbsolute(trimmed)
      ? trimmed
      : path.resolve(cwd, trimmed);
    if (!fs.existsSync(absolutePath)) {
      if (!options.allowMissing) {
        result.missing.push(trimmed);
      }
      continue;
    }

    try {
      const destinationPath = uniqueDestPathSync(trashDir, absolutePath);
      moveSync(absolutePath, destinationPath);
      result.moved.push(trimmed);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      result.errors.push(`rm: ${trimmed}: ${message}`);
    }
  }

  return result;
};

const parseArgs = (argv) => {
  const args = argv.slice(2);
  let allowMissing = false;
  const targets = [];

  for (const arg of args) {
    if (arg === '-h' || arg === '--help') {
      return { help: true, allowMissing, targets: [] };
    }
    if (arg === '-f' || arg === '--allow-missing') {
      allowMissing = true;
      continue;
    }
    targets.push(arg);
  }

  return { help: false, allowMissing, targets };
};

const main = () => {
  const parsed = parseArgs(process.argv);
  if (parsed.help) {
    printUsage();
    return 0;
  }
  if (parsed.targets.length === 0) {
    printUsage();
    return 2;
  }

  const result = movePathsToTrash(parsed.targets, process.cwd(), {
    allowMissing: parsed.allowMissing,
  });

  for (const missing of result.missing) {
    process.stderr.write(`rm: ${missing}: No such file or directory\n`);
  }
  for (const error of result.errors) {
    process.stderr.write(`${error}\n`);
  }

  if (result.missing.length > 0 || result.errors.length > 0) {
    return 1;
  }
  return 0;
};

if (require.main === module) {
  process.exit(main());
}

module.exports = {
  movePathsToTrash,
};
