const express = require('express');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = 7701;
const FEED_DIR = path.join(__dirname, 'feed');
const PUBLIC_DIR = path.join(__dirname, 'public');

// Ensure feed directory exists
if (!fs.existsSync(FEED_DIR)) fs.mkdirSync(FEED_DIR, { recursive: true });
if (!fs.existsSync(PUBLIC_DIR)) fs.mkdirSync(PUBLIC_DIR, { recursive: true });

// Serve static files (the PWA frontend)
app.use(express.static(PUBLIC_DIR));

// API: Get feed items, newest first
// Optional query params: ?limit=20&before=2026-02-16T12:00:00Z&type=weather
app.get('/api/feed', (req, res) => {
  try {
    const limit = parseInt(req.query.limit) || 200;
    const beforeDate = req.query.before ? new Date(req.query.before) : null;
    const typeFilter = req.query.type || null;

    // Read all JSON files from feed directory
    const files = fs.readdirSync(FEED_DIR)
      .filter(f => f.endsWith('.json'))
      .sort()
      .reverse(); // newest first

    let items = [];
    for (const file of files) {
      try {
        const data = JSON.parse(fs.readFileSync(path.join(FEED_DIR, file), 'utf8'));
        // Support single items or arrays
        const entries = Array.isArray(data) ? data : [data];
        items.push(...entries);
      } catch (e) {
        // Skip malformed files
      }
    }

    // Sort by timestamp, newest first
    items.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

    // Apply filters
    if (beforeDate) {
      items = items.filter(i => new Date(i.timestamp) < beforeDate);
    }
    if (typeFilter) {
      items = items.filter(i => i.type === typeFilter);
    }

    // Apply limit
    items = items.slice(0, limit);

    res.json({ items, count: items.length });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// API: Get available content types
app.get('/api/types', (req, res) => {
  try {
    const files = fs.readdirSync(FEED_DIR).filter(f => f.endsWith('.json'));
    const types = new Set();
    for (const file of files) {
      try {
        const data = JSON.parse(fs.readFileSync(path.join(FEED_DIR, file), 'utf8'));
        const entries = Array.isArray(data) ? data : [data];
        entries.forEach(e => types.add(e.type));
      } catch (e) {}
    }
    res.json({ types: [...types].sort() });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`Noosphere running on http://localhost:${PORT}`);
});
