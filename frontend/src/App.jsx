
import { useEffect, useState } from "react";
import "./App.css";

const API = "http://127.0.0.1:8000";

function formatSize(bytes = 0) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

async function readResponse(response) {
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      message = body.detail || message;
    } catch {
      // Keep the fallback message if the response isn't JSON.
    }
    throw new Error(message);
  }

  return response.status === 204 ? null : response.json();
}

function App() {
  const [token, setToken] = useState("");
  const [user, setUser] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [activeTab, setActiveTab] = useState("All Documents");
  const [search, setSearch] = useState("");
  const [showUpload, setShowUpload] = useState(false);
  const [file, setFile] = useState(null);
  const [category, setCategory] = useState("General");
  const [email, setEmail] = useState("owner.demo@example.com");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  async function loadDocuments(accessToken = token) {
    const response = await fetch(`${API}/documents`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    const data = await readResponse(response);
    setDocuments(data);
  }

  async function login(event) {
    event.preventDefault();
    setError("");
    setNotice("");
    setLoading(true);

    try {
      const response = await fetch(`${API}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const data = await readResponse(response);

      if (!data.access_token) {
        throw new Error("The server did not return an access token.");
      }

      const accessToken = data.access_token;
      const meResponse = await fetch(`${API}/auth/me`, {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      const currentUser = await readResponse(meResponse);

      setToken(accessToken);
      setUser(currentUser);
      await loadDocuments(accessToken);
      setPassword("");
      setNotice("Successfully connected to TrustVault.");
    } catch (err) {
      setError(
        err instanceof TypeError
          ? "Cannot reach the backend. Check that FastAPI is running at 127.0.0.1:8000."
          : err.message
      );
    } finally {
      setLoading(false);
    }
  }

  async function refreshDocuments() {
    setError("");
    try {
      await loadDocuments();
    } catch (err) {
      setError(err.message);
    }
  }

  async function uploadDocument(event) {
    event.preventDefault();
    if (!file || uploading) return;

    setError("");
    setNotice("");

    if (file.size > 5 * 1024 * 1024) {
      setError("The maximum file size is 5 MB.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    setUploading(true);
    try {
      const response = await fetch(
        `${API}/documents/upload?category=${encodeURIComponent(category)}`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
          body: formData,
        }
      );

      await readResponse(response);
      await loadDocuments();

      setFile(null);
      setCategory("General");
      setShowUpload(false);
      setNotice("Document uploaded successfully.");
    } catch (err) {
      setError(
        err instanceof TypeError
          ? "Could not connect to the backend. Check that it is running."
          : err.message
      );
    } finally {
      setUploading(false);
    }
  }

  async function downloadDocument(doc) {
    setError("");
    setNotice("");

    try {
      const response = await fetch(
        `${API}/documents/${doc.id}/download`,
        { headers: { Authorization: `Bearer ${token}` } }
      );

      if (!response.ok) {
        let message = `Download failed (${response.status})`;
        try {
          const body = await response.json();
          message = body.detail || message;
        } catch {
          // Use the fallback message.
        }
        throw new Error(message);
      }

      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = objectUrl;
      link.download = doc.filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(objectUrl);
      setNotice(`Download started: ${doc.filename}`);
    } catch (err) {
      setError(
        err instanceof TypeError
          ? "Could not connect to the backend."
          : err.message
      );
    }
  }

  function logout() {
    setToken("");
    setUser(null);
    setDocuments([]);
    setPassword("");
    setSearch("");
    setActiveTab("All Documents");
    setError("");
    setNotice("");
    setShowUpload(false);
  }

  const visibleDocuments = documents.filter((doc) => {
    const name = (doc.filename || "").toLowerCase();
    const matchesSearch = name.includes(search.toLowerCase());
    const matchesTab =
      activeTab === "All Documents" ||
      (activeTab === "Shared with me" && doc.access === "shared") ||
      (activeTab === "My Documents" && doc.access === "owner");

    return matchesSearch && matchesTab;
  });

  useEffect(() => {
    // Authentication is intentionally held in component state for this MVP.
    // Refreshing the page returns to the login screen.
  }, []);

  if (!token || !user) {
    return (
      <div className="auth-screen">
        <form className="auth-card" onSubmit={login}>
          <a className="brand auth-brand" href="#" onClick={(e) => e.preventDefault()}>
            <span className="brand-icon">⬡</span>
            <span>Trust<span className="brand-light">Vault</span></span>
          </a>
          <div className="eyebrow">SECURE DOCUMENT WORKSPACE</div>
          <h1>Welcome back</h1>
          <p className="subtitle">
            Sign in to access your protected documents.
          </p>

          {error && <div className="app-message error-message">{error}</div>}

          <label className="field-label">
            Email address
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="username"
              required
            />
          </label>

          <label className="field-label">
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </label>

          <button className="primary-button auth-submit" type="submit" disabled={loading}>
            {loading ? "Connecting..." : "Sign in securely"}
          </button>

          <p className="auth-footnote">
            TrustVault · Private by default. Shared with control.
          </p>
        </form>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#" onClick={(e) => e.preventDefault()}>
          <span className="brand-icon">⬡</span>
          <span>Trust<span className="brand-light">Vault</span></span>
        </a>

        <div className="workspace-label">WORKSPACE</div>
        <nav className="navigation">
          {[
            ["All Documents", "▤"],
            ["My Documents", "▣"],
            ["Shared with me", "⇄"],
          ].map(([label, icon]) => (
            <button
              type="button"
              key={label}
              className={`nav-item ${activeTab === label ? "active" : ""}`}
              onClick={() => setActiveTab(label)}
            >
              <span>{icon}</span>{label}
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="secure-card">
            <span className="secure-icon">♢</span>
            <strong>Your files, protected.</strong>
            <p>Private by default. Shared with control.</p>
          </div>
          <div className="profile">
            <div className="avatar">
              {(user.full_name || user.email || "TV").slice(0, 2).toUpperCase()}
            </div>
            <div>
              <strong>{user.full_name || user.email}</strong>
              <small>{user.role || "Secure workspace"}</small>
            </div>
            <button className="logout-button" onClick={logout}>Log out</button>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="breadcrumb">Workspace <span>/</span> {activeTab}</div>
          <div className="security-status">
            <span className="status-dot" /> Connected to API
          </div>
        </header>

        <section className="page-content">
          <div className="welcome-row">
            <div>
              <div className="eyebrow">YOUR PRIVATE WORKSPACE</div>
              <h1>{activeTab}</h1>
              <p className="subtitle">
                Keep your important files organized, private, and under your control.
              </p>
            </div>
            <button className="primary-button" onClick={() => { setError(""); setShowUpload(true); }}>
              <span>＋</span> Upload document
            </button>
          </div>

          {error && (
            <div className="app-message error-message">
              {error}
              <button onClick={() => setError("")} aria-label="Dismiss error">×</button>
            </div>
          )}
          {notice && (
            <div className="app-message success-message">
              {notice}
              <button onClick={() => setNotice("")} aria-label="Dismiss message">×</button>
            </div>
          )}

          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-top"><span>Total documents</span><span className="stat-icon blue">▤</span></div>
              <strong>{documents.length}</strong>
              <small>Available to this account</small>
            </div>
            <div className="stat-card">
              <div className="stat-top"><span>My documents</span><span className="stat-icon purple">▣</span></div>
              <strong>{documents.filter((d) => d.access === "owner").length}</strong>
              <small>Owned by you</small>
            </div>
            <div className="stat-card">
              <div className="stat-top"><span>Shared documents</span><span className="stat-icon green">⇄</span></div>
              <strong>{documents.filter((d) => d.access === "shared").length}</strong>
              <small>Shared with this account</small>
            </div>
          </div>

          <section className="documents-panel">
            <div className="panel-heading">
              <div>
                <h2>Documents</h2>
                <p>Live data from your TrustVault backend</p>
              </div>
              <div className="document-controls">
                <label className="search-box">
                  <span>⌕</span>
                  <input
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="Search documents..."
                  />
                </label>
                <button className="secondary-button" onClick={refreshDocuments}>Refresh</button>
              </div>
            </div>

            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>DOCUMENT NAME</th>
                    <th>CATEGORY</th>
                    <th>SIZE</th>
                    <th>ACCESS</th>
                    <th>ACTION</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleDocuments.map((doc) => (
                    <tr key={doc.id}>
                      <td>
                        <div className="file-cell">
                          <span className="pdf-icon">FILE</span>
                          <div>
                            <strong>{doc.filename}</strong>
                            <small>
                              {doc.created_at
                                ? new Date(doc.created_at).toLocaleDateString()
                                : "Document file"}
                            </small>
                          </div>
                        </div>
                      </td>
                      <td><span className="category-tag">{doc.category}</span></td>
                      <td>{formatSize(doc.size_bytes)}</td>
                      <td>
                        <span className={`access-tag ${doc.access === "owner" ? "owner" : "shared"}`}>
                          <span />{doc.access === "owner" ? "Owner" : "Shared"}
                        </span>
                      </td>
                      <td>
                        <button className="secondary-button" onClick={() => downloadDocument(doc)}>
                          Download
                        </button>
                      </td>
                    </tr>
                  ))}
                  {visibleDocuments.length === 0 && (
                    <tr>
                      <td colSpan="5" className="empty-state">
                        {search
                          ? "No matching documents. Try another search."
                          : activeTab === "Shared with me"
                            ? "No documents have been shared with this account."
                            : "No documents yet. Upload your first file to get started."}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            <div className="table-footer">
              Showing {visibleDocuments.length} of {documents.length} documents
              <span>Protected workspace <span className="footer-lock">♢</span></span>
            </div>
          </section>

          <div className="bottom-note">
            <span>♢</span>
            <div>
              <strong>Security comes first</strong>
              <p>Access is checked by the backend for each document request.</p>
            </div>
          </div>
        </section>
      </main>

      {showUpload && (
        <div className="modal-backdrop" onClick={() => !uploading && setShowUpload(false)}>
          <section className="upload-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-heading">
              <div>
                <h2>Upload a document</h2>
                <p>Add a file to your secure workspace</p>
              </div>
              <button
                className="close-button"
                onClick={() => setShowUpload(false)}
                disabled={uploading}
              >×</button>
            </div>

            <form onSubmit={uploadDocument}>
              <label className="upload-dropzone">
                <span className="upload-cloud">↑</span>
                <strong>{file ? file.name : "Choose a file to upload"}</strong>
                <small>PDF, TXT, PNG or JPEG · Maximum 5 MB</small>
                <input
                  type="file"
                  accept=".pdf,.txt,.png,.jpg,.jpeg"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                  required
                />
              </label>

              <label className="field-label">
                Category
                <select value={category} onChange={(e) => setCategory(e.target.value)}>
                  <option>General</option>
                  <option>Reports</option>
                  <option>Strategy</option>
                  <option>Security</option>
                  <option>Finance</option>
                </select>
              </label>

              <div className="modal-actions">
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => setShowUpload(false)}
                  disabled={uploading}
                >Cancel</button>
                <button className="primary-button" type="submit" disabled={uploading || !file}>
                  {uploading ? "Uploading..." : "Upload document"}
                </button>
              </div>
            </form>
          </section>
        </div>
      )}
    </div>
  );
}

export default App;