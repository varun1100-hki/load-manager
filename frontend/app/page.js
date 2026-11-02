"use client";
import { useCallback, useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const STATE_STYLE = {
  on: { background: "#d4f5d4", border: "2px solid #2e9e2e", label: "Running" },
  off: { background: "#eee", border: "2px solid #bbb", label: "Off" },
  shed: { background: "#fff1cc", border: "2px dashed #e09a00", label: "Shed (waiting to restart)" },
};

export default function Page() {
  const [data, setData] = useState({ capacity: 800, load: 0, remaining: 800, appliances: [] });
  const [notice, setNotice] = useState(null); // { type: "info" | "error", lines: [] }
  const [form, setForm] = useState({ name: "", wattage: "", priority: "" });

  const refresh = useCallback(async () => {
    try {
      const res = await fetch(`${API}/appliances`);
      setData(await res.json());
    } catch {
      setNotice({ type: "error", lines: ["Cannot reach the server."] });
    }
  }, []);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 3000);
    return () => clearInterval(t);
  }, [refresh]);

  // Every action goes through here so events and rejection reasons are always shown.
  async function act(path, method, body) {
    try {
      const res = await fetch(`${API}${path}`, {
        method,
        headers: { "Content-Type": "application/json" },
        body: body ? JSON.stringify(body) : undefined,
      });
      const json = await res.json();
      if (!res.ok) {
        const d = json.detail;
        const reason = Array.isArray(d)
          ? d.map((e) => `${e.loc.slice(1).join(".")}: ${e.msg}`).join("; ")
          : d?.reason || "Request failed";
        setNotice({ type: "error", lines: [reason] });
        refresh();
        return false;
      }
      setNotice({ type: "info", lines: json.events });
      setData(json);
      return true;
    } catch {
      setNotice({ type: "error", lines: ["Cannot reach the server."] });
      return false;
    }
  }

  async function submit(e) {
    e.preventDefault();
    const ok = await act("/appliances", "POST", {
      name: form.name,
      wattage: Number(form.wattage),
      priority: Number(form.priority),
    });
    if (ok) setForm({ name: "", wattage: "", priority: "" });
  }

  const pct = Math.min(100, (data.load / data.capacity) * 100);
  const input = { padding: 6, marginRight: 8 };

  return (
    <main style={{ maxWidth: 720, margin: "0 auto", padding: 24 }}>
      <h1>Inverter Load Manager</h1>

      <section>
        <div style={{ background: "#ddd", height: 24, borderRadius: 12, overflow: "hidden" }}>
          <div
            style={{
              width: `${pct}%`,
              height: "100%",
              background: pct > 90 ? "#d33" : pct > 70 ? "#e09a00" : "#2e9e2e",
              transition: "width 0.3s",
            }}
          />
        </div>
        <p>
          <b>{data.load}W used</b> / {data.capacity}W &middot; {data.remaining}W free
        </p>
      </section>

      {notice && (
        <div
          style={{
            padding: 12,
            margin: "12px 0",
            borderRadius: 6,
            background: notice.type === "error" ? "#fde0e0" : "#e0ecfd",
            border: `1px solid ${notice.type === "error" ? "#d33" : "#4a7fd4"}`,
          }}
        >
          {notice.type === "error" && <b>Request refused: </b>}
          {notice.lines.map((l, i) => (
            <div key={i}>{l}</div>
          ))}
        </div>
      )}

      <section>
        {data.appliances.length === 0 && <p>No appliances yet. Register one below.</p>}
        {data.appliances.map((a) => {
          const s = STATE_STYLE[a.state];
          return (
            <div
              key={a.id}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: 12,
                marginBottom: 8,
                borderRadius: 6,
                background: s.background,
                border: s.border,
              }}
            >
              <div>
                <b>{a.name}</b> &middot; {a.wattage}W &middot; priority {a.priority}
                <div style={{ fontSize: 13 }}>{s.label}</div>
              </div>
              <div>
                {a.state === "on" || a.state === "shed" ? (
                  <button onClick={() => act(`/appliances/${a.id}/off`, "POST")}>Turn OFF</button>
                ) : (
                  <button onClick={() => act(`/appliances/${a.id}/on`, "POST")}>Turn ON</button>
                )}{" "}
                <button onClick={() => act(`/appliances/${a.id}`, "DELETE")}>Delete</button>
              </div>
            </div>
          );
        })}
      </section>

      <form onSubmit={submit} style={{ marginTop: 24 }}>
        <h3>Register appliance</h3>
        <input style={input} placeholder="Name" required value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })} />
        <input style={{ ...input, width: 90 }} type="number" min="1" placeholder="Watts" required
          value={form.wattage} onChange={(e) => setForm({ ...form, wattage: e.target.value })} />
        <input style={{ ...input, width: 90 }} type="number" min="1" placeholder="Priority" required
          value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })} />
        <button type="submit">Add</button>
        <div style={{ fontSize: 12, color: "#666", marginTop: 4 }}>Priority 1 = most important.</div>
      </form>
    </main>
  );
}
