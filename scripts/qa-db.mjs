#!/usr/bin/env node
/**
 * Query the QA database, for smoke-testing when the UI cannot be reached.
 *
 * Credentials come from ~/.claude/devflow/qa-db.env, which lives OUTSIDE any git repo.
 * Nothing in this file is a secret and nothing here may become one.
 *
 *   node scripts/qa-db.mjs "select id, name from teams"
 *   echo "select ..." | node scripts/qa-db.mjs
 *
 * Read-only by default: anything that is not SELECT / WITH / EXPLAIN / SHOW is refused unless
 * --write is passed. QA is shared — an accidental UPDATE there costs someone else their afternoon.
 */
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { homedir } from 'node:os';
import { join } from 'node:path';

const ENV_FILE = process.env.QA_DB_ENV ?? join(homedir(), '.claude', 'devflow', 'qa-db.env');

function loadEnv(path) {
  let raw;
  try {
    raw = readFileSync(path, 'utf8');
  } catch {
    throw new Error(
      `No QA credentials at ${path}.\n` +
        'Create it with QA_DB_HOST / QA_DB_PORT / QA_DB_NAME / QA_DB_USER / QA_DB_PASSWORD, chmod 600.\n' +
        'Set QA_DB_SSL_INSECURE=true only if your QA database uses a self-signed certificate.',
    );
  }
  const out = {};
  for (const line of raw.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const eq = trimmed.indexOf('=');
    if (eq === -1) continue;
    out[trimmed.slice(0, eq).trim()] = trimmed.slice(eq + 1).trim();
  }
  return out;
}

// `pg` is not a dependency of this repo — borrow it from whichever project is being tested.
function loadPg() {
  const candidates = [
    process.env.PG_FROM,
    join(process.cwd(), 'node_modules', 'pg'),
  ].filter(Boolean);
  const require = createRequire(import.meta.url);
  for (const path of candidates) {
    try {
      return require(path);
    } catch {
      /* try the next one */
    }
  }
  throw new Error(`Could not resolve the "pg" driver. Tried:\n  ${candidates.join('\n  ')}`);
}

const readSql = async () => {
  const args = process.argv.slice(2).filter((a) => a !== '--write');
  if (args.length) return args.join(' ');
  const chunks = [];
  for await (const chunk of process.stdin) chunks.push(chunk);
  return Buffer.concat(chunks).toString('utf8');
};

const sql = (await readSql()).trim();
if (!sql) {
  console.error('No SQL given. Pass it as an argument or on stdin.');
  process.exit(2);
}

const allowWrite = process.argv.includes('--write');
if (!allowWrite && !/^\s*(select|with|explain|show)\b/i.test(sql)) {
  console.error('Refusing a non-read statement without --write. QA is a shared database.');
  process.exit(2);
}

const env = loadEnv(ENV_FILE);
const { Client } = loadPg();
const client = new Client({
  host: env.QA_DB_HOST,
  port: Number(env.QA_DB_PORT ?? 5432),
  database: env.QA_DB_NAME,
  user: env.QA_DB_USER,
  password: env.QA_DB_PASSWORD,
  ssl: { rejectUnauthorized: env.QA_DB_SSL_INSECURE !== 'true' },
  statement_timeout: 30_000,
  connectionTimeoutMillis: 15_000,
});

try {
  await client.connect();
  const result = await client.query(sql);
  const rows = Array.isArray(result) ? result.flatMap((r) => r.rows ?? []) : result.rows;
  console.log(JSON.stringify(rows, null, 2));
  console.error(`(${rows.length} row${rows.length === 1 ? '' : 's'})`);
} catch (error) {
  console.error(`Query failed: ${error.message}`);
  process.exitCode = 1;
} finally {
  await client.end().catch(() => {});
}
