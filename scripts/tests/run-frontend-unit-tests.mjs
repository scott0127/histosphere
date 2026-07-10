import assert from 'node:assert/strict';
import { access, readdir, readFile } from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import ts from 'typescript';

const root = process.cwd();
const tests = [];

globalThis.assert = assert;
globalThis.test = (name, fn) => {
  tests.push({ name, fn });
};

const moduleUrlCache = new Map();

const resolveLocalImport = async (specifier) => {
  const unresolvedPath = path.resolve(root, specifier.slice(2));
  const candidates = [
    unresolvedPath,
    `${unresolvedPath}.ts`,
    `${unresolvedPath}.js`,
    path.join(unresolvedPath, 'index.ts'),
    path.join(unresolvedPath, 'index.js'),
  ];

  for (const candidate of candidates) {
    try {
      await access(candidate);
      return candidate;
    } catch {
      // Try the next supported local module shape.
    }
  }

  throw new Error(`Unable to resolve local test import: ${specifier}`);
};

const compileLocalModule = async (absolutePath, importStack = []) => {
  if (importStack.includes(absolutePath)) {
    throw new Error(`Circular local test import: ${[...importStack, absolutePath].join(' -> ')}`);
  }

  if (moduleUrlCache.has(absolutePath)) {
    return moduleUrlCache.get(absolutePath);
  }

  const compilePromise = (async () => {
    const source = await readFile(absolutePath, 'utf8');
    const compiled = ts.transpileModule(source, {
      fileName: absolutePath,
      compilerOptions: {
        target: ts.ScriptTarget.ES2022,
        module: ts.ModuleKind.ES2022,
        moduleResolution: ts.ModuleResolutionKind.Bundler,
        isolatedModules: true,
        verbatimModuleSyntax: false,
      },
    });

    const nextImportStack = [...importStack, absolutePath];
    const localImportPattern = /((?:from|import)\s*['"])(~\/[^'"]+)(['"])/g;
    let rewrittenSource = '';
    let cursor = 0;

    for (const match of compiled.outputText.matchAll(localImportPattern)) {
      rewrittenSource += compiled.outputText.slice(cursor, match.index);
      const dependencyPath = await resolveLocalImport(match[2]);
      const dependencyUrl = await compileLocalModule(dependencyPath, nextImportStack);
      rewrittenSource += `${match[1]}${dependencyUrl}${match[3]}`;
      cursor = match.index + match[0].length;
    }
    rewrittenSource += compiled.outputText.slice(cursor);

    const encoded = Buffer.from(rewrittenSource, 'utf8').toString('base64');
    return `data:text/javascript;base64,${encoded}`;
  })();

  moduleUrlCache.set(absolutePath, compilePromise);

  try {
    return await compilePromise;
  } catch (error) {
    moduleUrlCache.delete(absolutePath);
    throw error;
  }
};

globalThis.loadTsModule = async (relativePath) => {
  const absolutePath = path.resolve(root, relativePath);
  const moduleUrl = await compileLocalModule(absolutePath);
  return import(moduleUrl);
};

const testDir = path.join(root, 'tests', 'frontend', 'unit');
const testFiles = (await readdir(testDir))
  .filter((file) => file.endsWith('.test.mjs'))
  .sort();

for (const file of testFiles) {
  await import(pathToFileURL(path.join(testDir, file)).href);
}

let failed = 0;
for (const item of tests) {
  try {
    await item.fn();
    console.log(`ok - ${item.name}`);
  } catch (error) {
    failed += 1;
    console.error(`not ok - ${item.name}`);
    console.error(error);
  }
}

if (failed > 0) {
  process.exitCode = 1;
}
