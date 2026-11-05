import { useCallback, useEffect, useState } from "react";
import { CreditCard, RefreshCw, History, Plus } from "lucide-react";
import { Link } from "react-router-dom";
import api, { fetchAllPages } from "../services/api";
import "./Operations.css";

const METHODS = ["BANK_TRANSFER", "NEFT", "RTGS", "IMPS", "UPI", "CHEQUE", "OTHER"];
const listOf = (data) => Array.isArray(data) ? data : data?.results || [];

function Payments() {
  const [payments, setPayments] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [summary, setSummary] = useState({});
  const [history, setHistory] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [form, setForm] = useState({ invoice: "", payment_reference: "", amount: "", payment_method: "BANK_TRANSFER", payment_date: new Date().toISOString().slice(0, 10), transaction_id: "", notes: "" });

  const load = useCallback(async () => {
    setLoading(true); setError("");
    const results = await Promise.allSettled([
      api.get("/payments/"), fetchAllPages("/invoices/", { page_size: 100 }), api.get("/payments/summary/"),
    ]);
    if (results[0].status === "fulfilled") setPayments(listOf(results[0].value.data));
    else setError(results[0].reason.response?.data?.detail || "Could not load payments.");
    if (results[1].status === "fulfilled") setInvoices(results[1].value);
    else setError((current) => current || "Could not load eligible invoices for payment.");
    if (results[2].status === "fulfilled") setSummary(results[2].value.data);
    else setError((current) => current || "Could not load payment summary.");
    setLoading(false);
  }, []);

  useEffect(() => {
    const timerId = setTimeout(() => { load(); }, 0);
    return () => clearTimeout(timerId);
  }, [load]);

  const submit = async (event) => {
    event.preventDefault(); setBusy(true); setError(""); setMessage("");
    try {
      await api.post("/payments/", { ...form, invoice: Number(form.invoice) });
      setMessage("Payment request recorded.");
      setForm((old) => ({ ...old, invoice: "", payment_reference: "", amount: "", transaction_id: "", notes: "" }));
      await load();
    } catch (err) {
      setError(err.response?.data?.detail || JSON.stringify(err.response?.data || {}) || "Could not record payment.");
    } finally { setBusy(false); }
  };

  const updateStatus = async (payment, new_status) => {
    setError(""); setMessage("");
    try {
      await api.post(`/payments/${payment.id}/update_status/`, { new_status });
      setMessage(`Payment ${payment.payment_reference} updated to ${new_status}.`);
      await load();
    } catch (err) { setError(err.response?.data?.detail || JSON.stringify(err.response?.data || {}) || "Could not update payment status."); }
  };

  const showHistory = async (payment) => {
    try { const response = await api.get(`/payments/${payment.id}/history/`); setHistory({ reference: payment.payment_reference, entries: listOf(response.data) }); }
    catch (err) { setError(err.response?.data?.detail || "Could not load payment history."); }
  };

  const money = (value) => new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(Number(value || 0));
  const eligibleInvoices = invoices.filter((invoice) => ["APPROVED", "PAYMENT_PENDING"].includes(invoice.status));

  return <main className="operations-page">
    <header className="operations-header"><div><Link to="/dashboard">← Dashboard</Link><h1><CreditCard size={25} /> Payments</h1><p>Record payment requests and track their status and audit history.</p></div><button className="ops-button secondary" onClick={load} disabled={loading}><RefreshCw size={16} /> Refresh</button></header>
    {error && <div className="ops-alert error">{error}</div>}{message && <div className="ops-alert success">{message}</div>}
    <section className="ops-metrics">
      {(summary.currency_summary || []).flatMap((currencySummary) => [
        ["Completed", currencySummary.completed_payment_total],
        ["Pending", currencySummary.pending_payment_total],
        ["Outstanding", currencySummary.outstanding_total],
      ].map(([label, value]) => <article className="ops-card" key={`${label}-${currencySummary.currency}`}><span>{label} ({currencySummary.currency})</span><strong>{money(value, currencySummary.currency)}</strong></article>))}
      {!loading && !summary.currency_summary?.length && <p className="ops-muted">No payment totals are available.</p>}
    </section>
    <section className="ops-card ops-form-card"><h2><Plus size={19} /> Record payment</h2><p>Available to finance managers and administrators.</p>
      <form className="ops-form" onSubmit={submit}>
        <label>Approved invoice<select required value={form.invoice} onChange={(e) => { const selectedInvoice = eligibleInvoices.find((invoice) => invoice.id === Number(e.target.value)); setForm({ ...form, invoice: e.target.value, currency: selectedInvoice?.currency || "INR" }); }}><option value="">Choose invoice</option>{eligibleInvoices.map((invoice) => <option key={invoice.id} value={invoice.id}>{invoice.invoice_number} · {invoice.vendor_name} · {money(invoice.total_amount, invoice.currency)}</option>)}</select></label>
        <label>Payment reference<input required value={form.payment_reference} onChange={(e) => setForm({ ...form, payment_reference: e.target.value })} /></label>
        <label>Amount<input required type="number" min="0.01" step="0.01" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} /></label>
        <label>Method<select value={form.payment_method} onChange={(e) => setForm({ ...form, payment_method: e.target.value })}>{METHODS.map((method) => <option key={method}>{method}</option>)}</select></label>
        <label>Payment date<input required type="date" value={form.payment_date} onChange={(e) => setForm({ ...form, payment_date: e.target.value })} /></label>
        <label>Transaction ID<input value={form.transaction_id} onChange={(e) => setForm({ ...form, transaction_id: e.target.value })} /></label>
        <label className="ops-wide">Notes<input value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></label>
        <button className="ops-button primary" disabled={busy || !eligibleInvoices.length}>{busy ? "Saving…" : "Record payment"}</button>
      </form>
      {!eligibleInvoices.length && <p className="ops-muted">No approved invoices are currently available for payment.</p>}
    </section>
    <section className="ops-card"><h2>Payment register</h2>{loading ? <p>Loading…</p> : payments.length === 0 ? <p className="ops-muted">No payments recorded yet.</p> : <div className="ops-table-wrap"><table className="ops-table"><thead><tr><th>Reference</th><th>Invoice</th><th>Vendor</th><th>Amount</th><th>Payment date</th><th>Due date</th><th>Status</th><th>Actions</th></tr></thead><tbody>{payments.map((payment) => { const nextStatuses = payment.status === "PENDING" ? ["PROCESSING", "FAILED", "CANCELLED"] : payment.status === "PROCESSING" ? ["COMPLETED", "FAILED", "CANCELLED"] : []; return <tr key={payment.id}><td>{payment.payment_reference}</td><td>{payment.invoice_number}</td><td>{payment.vendor_name}</td><td>{money(payment.amount, payment.currency)}</td><td>{payment.payment_date}</td><td>{payment.due_date}{payment.is_overdue && <strong className="payment-overdue"> Overdue</strong>}</td><td><select aria-label={`Status for ${payment.payment_reference}`} value={payment.status} disabled={!nextStatuses.length} onChange={(e) => updateStatus(payment, e.target.value)}><option value={payment.status}>{payment.status}</option>{nextStatuses.map((nextStatus) => <option key={nextStatus}>{nextStatus}</option>)}</select></td><td><button className="ops-icon-button" onClick={() => showHistory(payment)} title="View audit history"><History size={17} /></button></td></tr>; })}</tbody></table></div>}</section>
    {history && <div className="ops-dialog-backdrop" onClick={() => setHistory(null)}><section className="ops-dialog" onClick={(e) => e.stopPropagation()}><button className="ops-close" onClick={() => setHistory(null)}>Close</button><h2>History · {history.reference}</h2>{history.entries.length ? <ul>{history.entries.map((entry) => <li key={entry.id}><strong>{entry.action}</strong> · {entry.previous_status || "Created"} → {entry.new_status}<br />{entry.actor_username} · {new Date(entry.created_at).toLocaleString()} {entry.comments && `· ${entry.comments}`}</li>)}</ul> : <p>No history entries.</p>}</section></div>}
  </main>;
}

export default Payments;
