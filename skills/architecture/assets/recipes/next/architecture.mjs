// Architecture lint from docs/architecture.md: where code lives and which way imports flow.
// Spread `architectureBlocks` into eslint.config.mjs after eslint-config-next. Every message names
// the fix and the guide, so an agent corrects itself on the write.
import boundaries from 'eslint-plugin-boundaries';

const GUIDE = 'docs/architecture.md';
const MODULE_FOLDERS = ['use-cases', 'domain', 'infra', 'components'];
const MODULE_PARTS = MODULE_FOLDERS.map((folder) => `module-${folder}`);
const MODULE_TYPES = ['module', ...MODULE_PARTS];
const SHARED_TYPES = ['components', 'platform', 'lib'];
const SOURCE_FILES = ['src/**/*.{ts,tsx}'];
const ENV_FOLDERS = ['src/platform/**', 'src/modules/*/infra/**'];

const ENTRY_MESSAGE = `Outside module "{{to.captured.name}}", import it only through "@/modules/{{to.captured.name}}" (index.ts) or "@/modules/{{to.captured.name}}/server"; its other files are internal. See ${GUIDE}.`;
const ENV_MESSAGE = `Only src/platform/ and a module's infra/ may read process.env; expose what callers need from there. See ${GUIDE}.`;
const USE_CLIENT_FILE = 'Program:has(> ExpressionStatement[directive="use client"])';
const SERVER_SOURCE = String.raw`/^(@\/modules\/[^/]+|\.{1,2}(\/[^/]+)*)\/server(\.ts)?$|^@\/platform(\/|$)/`;

const otherModule = { captured: { name: '!{{ from.element.captured.name }}' } };
const ownModule = { captured: { name: '{{ from.element.captured.name }}' } };

function policy(from, to, message) {
  return { from: { element: from }, disallow: { to: { element: to } }, message };
}

const POLICIES = [
  // Between homes: app → modules → components | platform → lib.
  policy(
    { types: { anyOf: SHARED_TYPES } },
    { types: { anyOf: ['app', ...MODULE_TYPES] } },
    `Shared code (src/components, src/platform, src/lib) knows no business: it must not import a module or a route. See ${GUIDE}.`,
  ),
  policy(
    { type: 'lib' },
    { types: { anyOf: ['components', 'platform'] } },
    `src/lib is pure helpers: it must not import UI (src/components) or I/O (src/platform). See ${GUIDE}.`,
  ),
  policy(
    { type: 'components' },
    { type: 'platform' },
    `Shared UI renders what it's given; it must not reach src/platform. Pass data in as props. See ${GUIDE}.`,
  ),
  policy(
    { type: 'platform' },
    { type: 'components' },
    `src/platform is server infrastructure; it must not import UI. See ${GUIDE}.`,
  ),
  policy(
    { types: { anyOf: MODULE_TYPES } },
    { type: 'app' },
    `Modules must not import routes in src/app; routes compose modules. See ${GUIDE}.`,
  ),
  // A module from outside: only index.ts (client-safe) and server.ts (server-only).
  policy({ types: { noneOf: MODULE_TYPES } }, { types: { anyOf: MODULE_PARTS } }, ENTRY_MESSAGE),
  policy({ types: { noneOf: MODULE_TYPES } }, { type: 'module', fileInternalPath: '!{index,server}.ts' }, ENTRY_MESSAGE),
  policy({ types: { anyOf: MODULE_TYPES } }, { types: { anyOf: MODULE_PARTS }, ...otherModule }, ENTRY_MESSAGE),
  policy(
    { types: { anyOf: MODULE_TYPES } },
    { type: 'module', fileInternalPath: '!{index,server}.ts', ...otherModule },
    ENTRY_MESSAGE,
  ),
  // Inside a module, imports point inward: components and use cases → domain; use cases → infra.
  policy(
    { type: 'module-domain' },
    { types: { anyOf: ['module', 'module-use-cases', 'module-infra', 'module-components'] }, ...ownModule },
    `domain/ holds the rules and depends on nothing else in its module; move what it needs into domain/. See ${GUIDE}.`,
  ),
  policy(
    { type: 'module-domain' },
    { types: { anyOf: ['platform', 'components'] } },
    `domain/ is pure: no I/O (src/platform) and no UI (src/components). Do the I/O in a use case or infra/. See ${GUIDE}.`,
  ),
  policy(
    { type: 'module-infra' },
    { types: { anyOf: ['module', 'module-use-cases', 'module-components'] }, ...ownModule },
    `infra/ stores and sends; it may import domain/ and src/platform, not use cases or UI. See ${GUIDE}.`,
  ),
  policy(
    { type: 'module-use-cases' },
    { type: 'module-components' },
    `Use cases return data; they don't render. Components take it as props. See ${GUIDE}.`,
  ),
  policy(
    { type: 'module-components' },
    { types: { anyOf: ['module-use-cases', 'module-infra'] } },
    `Components render what they're given: pages call use cases and pass props; changes go through actions.ts. See ${GUIDE}.`,
  ),
  policy(
    { type: 'module-components' },
    { types: { anyOf: MODULE_TYPES }, ...otherModule },
    `A module's components don't use another module's; the page composes both, passing one into the other as children. See ${GUIDE}.`,
  ),
];

const PURE_IMPORTS = {
  patterns: [
    {
      group: ['react', 'react/*', 'react-dom', 'react-dom/*', 'next', 'next/*', 'server-only', 'drizzle-orm', 'drizzle-orm/*', 'pg', 'process', 'node:*'],
      message: `domain/ and src/lib are pure: no React, framework, database, or Node I/O imports. Do the I/O in a use case or infra/. See ${GUIDE}.`,
    },
  ],
};

function qualifiedEnvSelectors() {
  const key = (path, name) => `:matches([${path}.name="${name}"], [${path}.value="${name}"])`;
  return [
    `MemberExpression${key('property', 'env')}[object.type="MemberExpression"]${key('object.property', 'process')}`,
    `VariableDeclarator[id.type="ObjectPattern"][init.type="MemberExpression"]${key('init.property', 'process')} > ObjectPattern > Property${key('key', 'env')}`,
  ].map((selector) => ({ selector, message: ENV_MESSAGE }));
}

/**
 * `no-restricted-syntax` entries: browser code importing server code, and env reads like
 * `globalThis.process.env`. A later block's `no-restricted-syntax` replaces earlier ones for the
 * same files, so any other block setting it (like the design drift lint) spreads these in too.
 */
export function architectureSyntax({ envAllowed = false } = {}) {
  const message = `A "use client" file must not import server code (a module's server.ts or src/platform); it would reach the browser bundle. Call a "use server" action from the module's actions.ts. See ${GUIDE}.`;
  const clientImports = [
    `ImportDeclaration[importKind!="type"][source.value=${SERVER_SOURCE}]`,
    `ExportNamedDeclaration[exportKind!="type"][source.value=${SERVER_SOURCE}]`,
    `ExportAllDeclaration[exportKind!="type"][source.value=${SERVER_SOURCE}]`,
    `ImportExpression[source.value=${SERVER_SOURCE}]`,
  ].map((node) => ({ selector: `${USE_CLIENT_FILE} ${node}`, message }));
  return envAllowed ? clientImports : [...clientImports, ...qualifiedEnvSelectors()];
}

export const architectureBlocks = [
  {
    files: SOURCE_FILES,
    plugins: { boundaries },
    settings: {
      'boundaries/elements': [
        { type: 'app', pattern: 'src/app' },
        // Module folders come before the module itself: the first pattern a file matches wins.
        ...MODULE_FOLDERS.map((folder) => ({ type: `module-${folder}`, pattern: `src/modules/*/${folder}`, capture: ['name'] })),
        { type: 'module', pattern: 'src/modules/*', capture: ['name'] },
        { type: 'components', pattern: 'src/components' },
        { type: 'platform', pattern: 'src/platform' },
        { type: 'lib', pattern: 'src/lib' },
      ],
    },
    rules: { 'boundaries/dependencies': ['error', { default: 'allow', policies: POLICIES }] },
  },
  {
    // Suppressions can't hide a violation: the boundaries are the architecture.
    files: SOURCE_FILES,
    linterOptions: { noInlineConfig: true },
    rules: {
      // disableScc: the precompute crashes on files linted before they're on disk.
      'import/no-cycle': ['error', { ignoreExternal: true, disableScc: true }],
    },
  },
  {
    files: SOURCE_FILES,
    ignores: ENV_FOLDERS,
    rules: {
      'no-restricted-properties': ['error', { object: 'process', property: 'env', message: ENV_MESSAGE }],
      'no-restricted-imports': [
        'error',
        { paths: ['process', 'node:process'].map((name) => ({ name, importNames: ['env'], message: ENV_MESSAGE })) },
      ],
      'no-restricted-syntax': ['error', ...architectureSyntax()],
    },
  },
  {
    files: ENV_FOLDERS.map((folder) => `${folder}/*.{ts,tsx}`),
    rules: { 'no-restricted-syntax': ['error', ...architectureSyntax({ envAllowed: true })] },
  },
  {
    files: ['src/modules/*/domain/**/*.ts', 'src/lib/**/*.ts'],
    rules: { 'no-restricted-imports': ['error', PURE_IMPORTS] },
  },
];

/**
 * For an app that had code before the architecture: these files keep their lint findings as
 * warnings, so the check stays green while each move spec takes its files off the list.
 */
export function architectureLegacy(files) {
  if (files.length === 0) return [];
  const rules = ['boundaries/dependencies', 'import/no-cycle', 'no-restricted-properties', 'no-restricted-imports', 'no-restricted-syntax'];
  return [{ files, rules: Object.fromEntries(rules.map((rule) => [rule, 'warn'])) }];
}
