import { test, expect } from '@playwright/test';
import { spawn } from 'child_process';
import { writeFileSync, mkdirSync, existsSync } from 'fs';
import net from 'net';
import path from 'path';

function getRandomPort() {
  return new Promise((resolve) => {
    const srv = net.createServer();
    srv.listen(0, () => {
      const port = srv.address().port;
      srv.close(() => resolve(port));
    });
  });
}

const EXPECTED_ERROR_PATTERNS = [
  /Failed to load resource/i,
  /ERR_CONNECTION_REFUSED/i,
  /fonts\.googleapis/i,
];

function isExpectedError(msg) {
  return EXPECTED_ERROR_PATTERNS.some(p => p.test(msg));
}

test('noosphere loads without JS errors', async ({ page }) => {
  const __dirname = path.dirname(new URL(import.meta.url).pathname);
  const publicDir = path.resolve(__dirname, '../..', 'public');

  // Create mock API response so fetch('/api/feed') doesn't blow up
  const apiDir = path.join(publicDir, 'api');
  if (!existsSync(apiDir)) mkdirSync(apiDir, { recursive: true });
  writeFileSync(path.join(apiDir, 'feed'), JSON.stringify([
    { id: 'test-1', title: 'Test Item', url: 'https://example.com', source: 'test', date: new Date().toISOString(), summary: 'A test feed item.' }
  ]));

  const port = await getRandomPort();
  const server = spawn('python3', ['-m', 'http.server', String(port)], {
    cwd: publicDir,
    stdio: 'ignore',
  });

  try {
    await new Promise(r => setTimeout(r, 1000));

    const errors = [];
    const warnings = [];

    page.on('console', msg => {
      if (msg.type() === 'error') errors.push(msg.text());
      if (msg.type() === 'warning') warnings.push(msg.text());
    });
    page.on('pageerror', err => {
      errors.push(err.message);
    });

    await page.goto(`http://localhost:${port}/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2000);

    // Key elements
    await expect(page.locator('#feed')).toBeAttached();
    await expect(page.locator('#sidebar')).toBeAttached();
    await expect(page.locator('#menuBtn')).toBeAttached();

    const realErrors = errors.filter(e => !isExpectedError(e));

    if (warnings.length > 0) {
      console.log('Warnings:', warnings);
    }

    expect(realErrors).toEqual([]);
  } finally {
    server.kill();
    // Clean up mock API
    try {
      const { unlinkSync, rmdirSync } = await import('fs');
      unlinkSync(path.join(apiDir, 'feed'));
      rmdirSync(apiDir);
    } catch {}
  }
});
