import assert from 'node:assert/strict';
import { readdir, readFile } from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import ts from 'typescript';

const root = process.cwd();
const tests = [];

globalThis.assert = assert;
globalThis.test = (name, fn) => {
  tests.push({ name, fn });
};
globalThis.loadTsModule = async (relativePath) => {
  const absolutePath = path.resolve(root, relativePath);
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

  const encoded = Buffer.from(compiled.outputText, 'utf8').toString('base64');
  return import(`data:text/javascript;base64,${encoded}`);
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
