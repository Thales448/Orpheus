const express = require('express');
const router = express.Router();
const { getPaginationParams } = require('./helpers');
const { Pool } = require('pg');
const pool = new Pool({
  host: process.env.DB_HOST,
  port: process.env.DB_PORT,
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
  database: process.env.DB_NAME
});

const db = new Pool({
  host: process.env.DB_HOST,
  port: process.env.DB_PORT,
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
  database: process.env.DB_NAME
});


/** --- Pagination for contracts/quotes --- **/
router.get('/contracts', async (req, res) => {
  // Ex: /contracts?ticker=SPY&expiration=20240419&page=2&limit=50
  const { ticker, expiration, strike, side } = req.query;
  const { limit, offset, page } = getPaginationParams(req);
  let q = `SELECT * FROM options.contracts WHERE ticker=$1`;
  let params = [ticker];
  if (expiration) { q += ` AND expiration=$${params.length+1}`; params.push(expiration);}
  if (strike)     { q += ` AND strike=$${params.length+1}`; params.push(strike);}
  if (side)       { q += ` AND side=$${params.length+1}`; params.push(side);}
  q += ` ORDER BY expiration, strike, side LIMIT $${params.length+1} OFFSET $${params.length+2}`;
  params.push(limit, offset);
  const { rows } = await pool.query(q, params);
  // Get total count for pagination info
  const countRes = await pool.query(`SELECT COUNT(*) FROM options.contracts WHERE ticker=$1`, [ticker]);
  res.json({ results: rows, page, limit, total: parseInt(countRes.rows[0].count) });
});

router.get('/quotes', async (req, res) => {
  // /quotes?contract_id=12345&page=1&limit=500
  const { contract_id } = req.query;
  const { limit, offset, page } = getPaginationParams(req);
  const q = `
    SELECT * FROM quotes WHERE contract_id=$1
    ORDER BY time LIMIT $2 OFFSET $3
  `;
  const { rows } = await pool.query(q, [contract_id, limit, offset]);
  const countRes = await pool.query('SELECT COUNT(*) FROM quotes WHERE contract_id=$1', [contract_id]);
  res.json({ results: rows, page, limit, total: parseInt(countRes.rows[0].count) });
});


// --- DATABASE METADATA & HEALTH ---
router.get('/metadata', async (req, res) => {
  let result = {};
  try {
    // Connection/uptime
    const { rows: versionRows } = await db.query('SELECT version(), pg_postmaster_start_time() AS started_at');
    const serverInfo = versionRows[0];
    result.server_version = serverInfo.version;
    result.uptime_start = serverInfo.started_at;
    result.uptime_seconds = Math.floor((Date.now() - new Date(serverInfo.started_at).getTime()) / 1000);

    // Table count
    const { rows: tableRows } = await db.query(
      `SELECT count(*) FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog','information_schema')`
    );
    result.total_tables = Number(tableRows[0].count);

    // Database size (human readable + bytes)
    const { rows: sizeRows } = await db.query(
      `SELECT pg_size_pretty(pg_database_size(current_database())) AS size, pg_database_size(current_database()) AS size_bytes`
    );
    result.size_pretty = sizeRows[0].size;
    result.size_bytes = Number(sizeRows[0].size_bytes);

    // Optional: TimescaleDB compression & IO stats
    let timescaleInfo = {};
    try {
      // Check if TimescaleDB is available
      const { rows: extRows } = await db.query(`SELECT extname FROM pg_extension WHERE extname = 'timescaledb'`);
      if (extRows.length) {
        // Compressed chunks (TimescaleDB only)
        const { rows: compRows } = await db.query(`
          SELECT count(*) AS compressed_chunks
          FROM timescaledb_information.chunks
          WHERE compression_status = 'Compressed'
        `);
        timescaleInfo.compressed_chunks = Number(compRows[0].compressed_chunks);

        // IO (compressed/uncompressed)
        const { rows: ioRows } = await db.query(`
          SELECT
            sum(total_bytes) AS total_bytes,
            sum(compressed_bytes) AS compressed_bytes
          FROM timescaledb_information.hypertable_compression_stats
        `);
        timescaleInfo.compressed_bytes = Number(ioRows[0].compressed_bytes || 0);
        timescaleInfo.total_bytes = Number(ioRows[0].total_bytes || 0);
      }
    } catch (err) {
      // Timescale not installed or stats not available
      timescaleInfo = {};
    }
    result.timescale = timescaleInfo;

    // Connection is alive if we got here
    result.status = "healthy";
    res.json(result);

  } catch (e) {
    res.status(500).json({ status: "error", error: e.message, result });
  }
});
// 2. Get Expirations
router.get('/expirations', async (req, res) => {
  const { ticker } = req.query;
  try {
    const { rows } = await db.query(
      `SELECT DISTINCT c.expiration FROM options.contracts c
       JOIN options.tickers t ON c.ticker_id = t.id
       WHERE t.ticker = $1 ORDER BY c.expiration ASC`, [ticker]
    );
    res.json(rows.map(r => r.expiration));
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// 3. Get Strikes
router.get('/strikes', async (req, res) => {
  const { ticker, expiration } = req.query;
  let sql = `
    SELECT DISTINCT c.strike FROM options.contracts c
    JOIN options.tickers t ON c.ticker_id = t.id
    WHERE t.ticker = $1
  `;
  let params = [ticker];
  if (expiration) { sql += ` AND c.expiration = $2`; params.push(expiration); }
  try {
    const { rows } = await db.query(sql + " ORDER BY c.strike ASC", params);
    res.json(rows.map(r => Number(r.strike)));
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// 5. Plot Contract Quotes (as a PNG)
router.get('/plot', async (req, res) => {
  const { contract_id, start_time, end_time, granularity } = req.query;
  try {
    let sql = `SELECT time, bid, ask FROM options.quotes WHERE contract_id = $1`;
    let params = [contract_id];
    let idx = 2;
    if (start_time) { sql += ` AND time >= $${idx++}`; params.push(start_time); }
    if (end_time)   { sql += ` AND time <= $${idx++}`; params.push(end_time); }
    sql += " ORDER BY time ASC";
    const { rows } = await db.query(sql, params);

    if (!rows.length) return res.status(404).json({ error: "No quotes found" });

    const width = 1200, height = 400;
    const canvas = createCanvas(width, height);
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, width, height);

    // Normalize and plot bid/ask
    const bids = rows.map(r => parseFloat(r.bid));
    const asks = rows.map(r => parseFloat(r.ask));
    const min = Math.min(...bids, ...asks), max = Math.max(...bids, ...asks);
    ctx.strokeStyle = '#228be6'; ctx.beginPath();
    bids.forEach((b, i) => {
      if (i === 0) ctx.moveTo(i * width / bids.length, height - ((b-min)/(max-min))*height);
      else ctx.lineTo(i * width / bids.length, height - ((b-min)/(max-min))*height);
    }); ctx.stroke();
    ctx.strokeStyle = '#fa5252'; ctx.beginPath();
    asks.forEach((a, i) => {
      if (i === 0) ctx.moveTo(i * width / asks.length, height - ((a-min)/(max-min))*height);
      else ctx.lineTo(i * width / asks.length, height - ((a-min)/(max-min))*height);
    }); ctx.stroke();

    // Save to buffer and send file
    const filename = path.join(__dirname, `plot_contract_${contract_id}.png`);
    const buf = canvas.toBuffer('image/png');
    fs.writeFileSync(filename, buf);
    res.sendFile(filename);
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// 6. Random Contract ID
router.get('/contract/random', async (req, res) => {
  const { ticker, expiration } = req.query;
  let sql = `
    SELECT c.id FROM options.contracts c
    JOIN options.tickers t ON c.ticker_id = t.id
    WHERE t.ticker = $1
  `;
  let params = [ticker];
  if (expiration) { sql += " AND c.expiration = $2"; params.push(expiration); }
  try {
    const { rows } = await db.query(sql, params);
    if (!rows.length) return res.status(404).json({ error: "No contracts found" });
    const randRow = rows[Math.floor(Math.random() * rows.length)];
    res.json({ contract_id: randRow.id });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// 7. Window for Contract (first/last day or week)
router.get('/contract/window', async (req, res) => {
  const { contract_id, period, which } = req.query;
  try {
    const { rows } = await db.query(
      `SELECT time FROM options.quotes WHERE contract_id = $1 ORDER BY time ASC`, [contract_id]
    );
    if (!rows.length) return res.status(404).json({ error: "No quotes found" });
    const times = rows.map(r => new Date(r.time));
    let group = period === "week" ? 7*24*3600*1000 : 24*3600*1000;
    let timesSorted = times.sort((a, b) => a-b);
    let start = which === "last" ? timesSorted[timesSorted.length-1] : timesSorted[0];
    let end = new Date(start.getTime() + group);
    res.json({ start_time: start.toISOString(), end_time: end.toISOString() });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// 8. Contract Overview JSON
router.get('/contract/overview', async (req, res) => {
  const { contract_id } = req.query;
  try {
    const { rows } = await db.query(
      `SELECT time, bid, ask FROM options.quotes WHERE contract_id = $1`, [contract_id]
    );
    if (!rows.length) return res.status(404).json({ error: "No quotes found" });

    let n_quotes = rows.length;
    let n_zero_bid = rows.filter(r => parseFloat(r.bid) === 0).length;
    let n_zero_ask = rows.filter(r => parseFloat(r.ask) === 0).length;
    let n_zero_both = rows.filter(r => parseFloat(r.bid) === 0 && parseFloat(r.ask) === 0).length;
    let n_valid = rows.filter(r => parseFloat(r.bid) > 0 && parseFloat(r.ask) > 0).length;
    let first_tick = rows[0].time, last_tick = rows[rows.length-1].time;

    res.json({
      contract_id: Number(contract_id),
      n_quotes,
      first_tick,
      last_tick,
      n_valid,
      n_zero_bid,
      n_zero_ask,
      n_zero_both,
      valid_pct: n_valid / n_quotes
    });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

//10. High level stats of tables
router.get('/summary', async (req, res) => {
  // 1. Full database size (correct)
  const dbSizeRes = await db.query(`SELECT pg_database_size(current_database()) AS size_bytes`);
  const totalDbSizeBytes = parseInt(dbSizeRes.rows[0].size_bytes);

  // 2. Regular tables (options, public) using total_relation_size
  const tableRes = await db.query(`
    SELECT table_schema, table_name,
           pg_total_relation_size(quote_ident(table_schema) || '.' || quote_ident(table_name)) AS size_bytes
    FROM information_schema.tables
    WHERE table_schema IN ('options', 'public')
  `);

  // 3. Timescale hypertables (in your DB)
  const hypertableRes = await db.query(`
    SELECT hypertable_schema, hypertable_name
    FROM timescaledb_information.hypertables
    WHERE hypertable_schema IN ('options', 'public')
  `);

  // 4. Get chunk sizes for all hypertables (returns one row per chunk)
  const chunkSizesRes = await db.query(`
    SELECT hypertable_schema, hypertable_name,
           pg_total_relation_size(format('%I.%I', chunk_schema, chunk_name)::regclass) AS chunk_size_bytes
    FROM timescaledb_information.chunks
    WHERE hypertable_schema IN ('options', 'public')
  `);

  // 5. Sum chunk sizes for each hypertable
  const hypertableChunkMap = {};
  chunkSizesRes.rows.forEach(chunk => {
    const key = `${chunk.hypertable_schema}.${chunk.hypertable_name}`;
    if (!hypertableChunkMap[key]) hypertableChunkMap[key] = 0;
    hypertableChunkMap[key] += parseInt(chunk.chunk_size_bytes || 0);
  });

  // 6. Merge table sizes with hypertable chunk sizes (for hypertables, override with real size)
  let tableSizes = tableRes.rows.map(r => {
    const key = `${r.table_schema}.${r.table_name}`;
    // If this is a hypertable, add all its chunk sizes
    if (hypertableChunkMap[key]) {
      return {
        table: key,
        size_bytes: hypertableChunkMap[key]
      };
    }
    // Otherwise, just report regular table size
    return {
      table: key,
      size_bytes: parseInt(r.size_bytes)
    };
  });

  // 7. Sort and limit to top 10
  tableSizes = tableSizes.sort((a, b) => b.size_bytes - a.size_bytes).slice(0, 10);

  // 8. Row counts for summary tables
  const contractCountRes = await pool.query('SELECT COUNT(*) FROM options.contracts');
  const quoteCountRes = await pool.query('SELECT COUNT(*) FROM options.quotes');

  res.json({
    total_tables: tableSizes.length,
    total_db_size_bytes: totalDbSizeBytes,
    largest_tables: tableSizes,
    contract_count: parseInt(contractCountRes.rows[0].count),
    quote_count: parseInt(quoteCountRes.rows[0].count),
    updated_at: new Date().toISOString()
  });
});




//11.live-status
let lastQps = 0, lastInsert = 0, lastSelect = 0;

// Simulate with middleware (real prod: use pg_stat_statements or pg_stat_database)
router.get('/live-status', async (req, res) => {
  const started = Date.now();
  // Ping DB for latency
  await pool.query('SELECT 1');
  const latencyMs = Date.now() - started;

  // Get active connections, TPS, etc.
  const stat = (await pool.query(`
    SELECT sum(numbackends) as connections
    FROM pg_stat_database
  `)).rows[0];
  const qpsRow = (await pool.query(`
    SELECT sum(xact_commit + xact_rollback) as tps,
           sum(tup_inserted) as inserted,
           sum(tup_fetched) as selected
    FROM pg_stat_database
  `)).rows[0];

  // Optionally, compare with previous poll to get deltas (track these in-memory in app)
  const qps = parseInt(qpsRow.tps || 0) - lastQps;
  const inserts = parseInt(qpsRow.inserted || 0) - lastInsert;
  const selects = parseInt(qpsRow.selected || 0) - lastSelect;
  lastQps = parseInt(qpsRow.tps || 0);
  lastInsert = parseInt(qpsRow.inserted || 0);
  lastSelect = parseInt(qpsRow.selected || 0);

  res.json({
    connections: parseInt(stat.connections),
    latency_ms: latencyMs,
    qps: qps,         // transactions per second
    inserts_per_sec: inserts,
    selects_per_sec: selects,
    updated_at: new Date().toISOString()
  });
});


// 9.Ticker-summary
// Add to your db.js

router.get('/ticker-summary', async (req, res) => {
  try {
    const page = parseInt(req.query.page) || 1;
    const limit = parseInt(req.query.limit) || 100;
    const offset = (page - 1) * limit;

    // 1. Get paginated tickers
    const tickersRes = await pool.query(
      `SELECT id AS ticker_id, ticker FROM options.tickers
       ORDER BY ticker
       LIMIT $1 OFFSET $2`, [limit, offset]
    );
    const tickers = tickersRes.rows;
    const tickerIds = tickers.map(t => t.ticker_id);

    // 2. Get contract counts per ticker
    const contractCountsRes = await pool.query(
      `SELECT ticker_id, COUNT(*) AS contract_count
       FROM options.contracts
       WHERE ticker_id = ANY($1)
       GROUP BY ticker_id`, [tickerIds]
    );
    const contractCounts = Object.fromEntries(contractCountsRes.rows.map(r => [r.ticker_id, parseInt(r.contract_count)]));

    // 3. Get expiration stats per ticker
    const expStatsRes = await pool.query(
      `SELECT ticker_id, COUNT(*) AS expiration_count,
              MIN(expiration) AS earliest_exp, MAX(expiration) AS latest_exp
       FROM options.expirations
       WHERE ticker_id = ANY($1)
       GROUP BY ticker_id`, [tickerIds]
    );
    const expStats = Object.fromEntries(expStatsRes.rows.map(r => [
      r.ticker_id,
      {
        expiration_count: parseInt(r.expiration_count),
        earliest_exp: r.earliest_exp,
        latest_exp: r.latest_exp
      }
    ]));

    // 4. Build landscape summary
    let summary = tickers.map(row => ({
      ticker_id: row.ticker_id,
      ticker: row.ticker,
      contract_count: contractCounts[row.ticker_id] || 0,
      expiration_count: expStats[row.ticker_id]?.expiration_count || 0,
      earliest_expiration: expStats[row.ticker_id]?.earliest_exp || null,
      latest_expiration: expStats[row.ticker_id]?.latest_exp || null
    }));

    // 5. Aggregate stats for dashboard
    const total_contracts = summary.reduce((a, b) => a + b.contract_count, 0);
    const avg_contracts = summary.length ? total_contracts / summary.length : 0;
    const total_expirations = summary.reduce((a, b) => a + b.expiration_count, 0);
    const avg_expirations = summary.length ? total_expirations / summary.length : 0;

    res.json({
      tickers: summary,
      page, limit, total: summary.length,
      aggregates: {
        total_contracts,
        avg_contracts_per_ticker: avg_contracts,
        total_expirations,
        avg_expirations_per_ticker: avg_expirations
      }
    });

  } catch (err) {
    console.error('Error in /db/ticker-summary:', err);
    res.status(500).json({ error: err.message });
  }
});


module.exports = router;
