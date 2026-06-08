import { useState } from "react";

const API_URL = "http://localhost:8000/api/screen";

/* ─── helpers ─── */
function fmt(n, d = 2) {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return Number(n).toFixed(d);
}

function fmtNumber(n) {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function getVerdictColor(verdict) {
  const v = (verdict || "").toLowerCase();
  if (v.includes("strong buy")) return "#22c55e";
  if (v.includes("buy")) return "#10b981";
  if (v.includes("watch")) return "#f59e0b";
  if (v.includes("hold")) return "#94a3b8";
  if (v.includes("avoid")) return "#ef4444";
  return "#64748b";
}

function getTypeIcon(type) {
  return type === "crypto" ? "💎" : "📈";
}

function getScoreColor(score) {
  if (score >= 80) return "#22c55e";
  if (score >= 60) return "#fbbf24";
  if (score >= 40) return "#f97316";
  return "#ef4444";
}

function getScoreBg(score) {
  if (score >= 80) return "rgba(34,197,94,0.12)";
  if (score >= 60) return "rgba(251,191,36,0.12)";
  if (score >= 40) return "rgba(249,115,22,0.12)";
  return "rgba(239,68,68,0.12)";
}

/* ─── components ─── */

function StatBadge({ label, value, unit = "" }) {
  return (
    <div className="stat-badge">
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}{unit}</div>
    </div>
  );
}

function ResultCard({ item, rank }) {
  const color = getScoreColor(item.total_score);
  const bg = getScoreBg(item.total_score);

  return (
    <div className="result-card" style={{ borderLeft: `4px solid ${color}` }}>
      {/* Header row */}
      <div className="card-header">
        <div className="rank">#{rank}</div>
        <div className="ticker-info">
          <span className="type-icon">{getTypeIcon(item.type)}</span>
          <span className="ticker">{item.ticker}</span>
          <span className="type-tag">{item.type.toUpperCase()}</span>
        </div>
        <div className="score-pill" style={{ background: bg, color }}>
          {fmt(item.total_score, 1)}/100
        </div>
      </div>

      {/* Company & Sector */}
      <div className="company-row">
        <span className="company-name">{item.company}</span>
        <span className="sector-tag">{item.sector}</span>
      </div>

      {/* Stats grid */}
      <div className="stats-grid">
        <StatBadge label="Price" value={`$${fmt(item.current_price)}`} />
        <StatBadge label="P/E Ratio" value={fmt(item.pe)} />
        <StatBadge label="RSI" value={fmt(item.rsi, 1)} />
        <StatBadge label="Score" value={fmt(item.total_score, 1)} />
      </div>

      {/* Signals */}
      <div className="signal-row">
        <div className="signal"><span className="signal-dot">★</span> {item.ma_signal}</div>
        <div className="signal"><span className="signal-dot">●</span> {item.volume_signal}</div>
      </div>

      {/* Verdict */}
      <div className="verdict" style={{ color: getVerdictColor(item.verdict) }}>
        {item.verdict}
      </div>

      {/* Layman Summary */}
      <div className="summary-box">
        <div className="summary-title">📖 What this means</div>
        <p className="summary-text">{item.layman_summary}</p>
      </div>

      {/* Investment Projection */}
      <div className="projection-box">
        <div className="projection-title">💡 If you had invested $1,000 today</div>
        <div className="projection-grid">
          <div className="projection-item">
            <div className="projection-days">30 Days</div>
            <div className="projection-value">
              ${fmtNumber(item.investment_30d?.projected_value, 2)}
              <span className="projection-pct" style={{ color: (item.investment_30d?.projected_return_pct || 0) >= 0 ? "#22c55e" : "#ef4444" }}>
                {fmt(item.investment_30d?.projected_return_pct, 1)}%
              </span>
            </div>
          </div>
          <div className="projection-item">
            <div className="projection-days">90 Days</div>
            <div className="projection-value">
              ${fmtNumber(item.investment_90d?.projected_value, 2)}
              <span className="projection-pct" style={{ color: (item.investment_90d?.projected_return_pct || 0) >= 0 ? "#22c55e" : "#ef4444" }}>
                {fmt(item.investment_90d?.projected_return_pct, 1)}%
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function LoadingSkeleton() {
  const items = [1, 2, 3];
  return (
    <div className="skeleton-container">
      {items.map((i) => (
        <div key={i} className="skeleton-card">
          <div className="skeleton-line long" style={{ width: "60%" }} />
          <div className="skeleton-line" />
          <div className="skeleton-line" style={{ width: "80%" }} />
          <div className="skeleton-line" style={{ width: "40%" }} />
        </div>
      ))}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="empty-state">
      <div className="empty-icon">🔭</div>
      <h3>No results found</h3>
      <p>Try adjusting your filters or running the screener again.</p>
    </div>
  );
}

function ErrorState({ message, onRetry }) {
  return (
    <div className="error-box">
      <div className="error-icon">⚠️</div>
      <h3>Something went wrong</h3>
      <p className="error-message">{message}</p>
      <button onClick={onRetry} className="retry-btn">Try Again</button>
    </div>
  );
}

/* ─── main app ─── */
function App() {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [watchlist, setWatchlist] = useState("default");
  const [topN, setTopN] = useState(5);
  const [includeCrypto, setIncludeCrypto] = useState(true);

  const runScreen = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ watchlist, top: Number(topN), include_crypto: includeCrypto }),
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();

      if (!Array.isArray(data)) {
        throw new Error("Invalid response format from server");
      }

      setResults(data);
    } catch (err) {
      setError(err.message || "Failed to fetch results. Is the backend running on port 8000?");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      {/* Header */}
      <header className="app-header">
        <div className="logo">
          <span className="logo-icon">📊</span>
          <h1>StockRadar</h1>
        </div>
        <p className="subtitle">Stock &amp; Crypto Screening, Scoring &amp; Insights</p>
      </header>

      {/* Controls */}
      <div className="controls">
        <div className="control-group">
          <label className="control-label">Watchlist</label>
          <select value={watchlist} onChange={(e) => setWatchlist(e.target.value)} className="control-select">
            <option value="default">Default (Top Stocks)</option>
            <option value="sp500">S&amp;P 500</option>
            <option value="crypto">Crypto Only</option>
          </select>
        </div>

        <div className="control-group">
          <label className="control-label">Top N</label>
          <select value={topN} onChange={(e) => setTopN(Number(e.target.value))} className="control-select wide">
            {Array.from({ length: 20 }, (_, i) => i + 1).map((n) => (
              <option key={n} value={n}>Top {n}</option>
            ))}
          </select>
        </div>

        <div className="control-group checkbox-group">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={includeCrypto}
              onChange={(e) => setIncludeCrypto(e.target.checked)}
            />
            <span className="check-indicator" />
            <span>Include Crypto</span>
          </label>
        </div>

        <button onClick={runScreen} disabled={loading} className="run-btn">
          {loading ? (
            <>
              <span className="spinner" /> Analyzing…
            </>
          ) : (
            <>🔍 Run Screener</>
          )}
        </button>
      </div>

      {/* Status */}
      {results.length > 0 && !loading && (
        <div className="results-count">
          Showing <strong>{results.length}</strong> ranked result{results.length !== 1 ? "s" : ""}
        </div>
      )}

      {/* Content */}
      <main>
        {error && <ErrorState message={error} onRetry={runScreen} />}

        {loading && <LoadingSkeleton />}

        {!loading && !error && results.length === 0 && results.length !== undefined && <EmptyState />}

        {!loading && !error && results.length > 0 && (
          <div className="results-list">
            {results.map((item, index) => (
              <ResultCard key={`${item.ticker}-${index}`} item={item} rank={index + 1} />
            ))}
          </div>
        )}
      </main>

      {/* Disclaimer */}
      {(results.length > 0 || loading) && !error && (
        <footer className="disclaimer">
          ⚠️ <strong>NOT FINANCIAL ADVICE.</strong> Past performance does not guarantee future results.
          This tool is for <strong>educational purposes only</strong>. Always conduct your own research.
        </footer>
      )}
    </div>
  );
}

export default App;
