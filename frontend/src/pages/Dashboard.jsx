
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  LayoutDashboard,
  FileText,
  Users,
  ShoppingCart,
  ClipboardCheck,
  CreditCard,
  BarChart3,
  LogOut,
  Bell,
  Search,
  RefreshCw,
  TrendingUp,
  Clock3,
  CircleCheck,
  Wallet,
  AlertCircle,
  Upload,
} from "lucide-react";

import { useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/useAuth";
import api from "../services/api";
import "./Dashboard.css";

const menuItems = [
  { label: "Overview", icon: LayoutDashboard, path: "/dashboard" },
  { label: "Invoices", icon: FileText, path: "/invoices" },
  { label: "Vendors", icon: Users, path: "/vendors" },
  { label: "Purchase Orders", icon: ShoppingCart, path: "/purchase-orders" },
  { label: "Goods Receipts", icon: FileText, path: "/goods-receipts" },
  { label: "Approvals", icon: ClipboardCheck, path: "/approvals" },
  { label: "Payments", icon: CreditCard, path: "/payments" },
  { label: "Reports", icon: BarChart3, path: "/reports" },
];

const formatCurrency = (amount, currency = "INR") => {
  const value = Number(amount ?? 0);

  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(Number.isFinite(value) ? value : 0);
};

const formatDate = (date) => {
  if (!date) return "—";

  const parsedDate = new Date(date);

  if (Number.isNaN(parsedDate.getTime())) return "—";

  return parsedDate.toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
};

const statusClass = (status) =>
  String(status || "unknown")
    .toLowerCase()
    .replaceAll("_", "-")
    .replaceAll(" ", "-");

function Dashboard() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [invoices, setInvoices] = useState([]);
  const [invoiceCount, setInvoiceCount] = useState(0);
  const [approvalCount, setApprovalCount] = useState(0);
  const [reportSummary, setReportSummary] = useState(null);
  const [paymentSummary, setPaymentSummary] = useState([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchTerm, setSearchTerm] = useState("");

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setError("");

    const results = await Promise.allSettled([
      api.get("/reports/summary/"),
      api.get("/payments/summary/"),
    ]);

    const [reportResult, paymentResult] = results;

    if (reportResult.status === "fulfilled") {
      const data = reportResult.value.data;
      setReportSummary(data);
      setInvoices((data.recent_invoices || []).map((invoice) => ({
        ...invoice,
        vendor_name: invoice.vendor__legal_name,
      })));
      setInvoiceCount(data.invoice_count || 0);
      setApprovalCount(data.pending_approval_count || 0);
    } else {
      setError("Could not load the dashboard report. Please retry.");
    }

    if (paymentResult.status === "fulfilled") {
      setPaymentSummary(paymentResult.value.data?.currency_summary || []);
    } else {
      setError((current) => current || "Could not load payment totals.");
    }

    setLoading(false);
  }, []);

  useEffect(() => {
    const timerId = setTimeout(() => {
      loadDashboard();
    }, 0);

    return () => clearTimeout(timerId);
  }, [loadDashboard]);

  const countStatus = (status) => (reportSummary?.invoice_status || [])
    .filter((row) => row.status === status)
    .reduce((total, row) => total + row.count, 0);
  const pendingReview = countStatus("PENDING_REVIEW");
  const overdueInvoices = (reportSummary?.overdue_by_currency || [])
    .reduce((total, row) => total + row.count, 0);
  const exceptionCount = reportSummary?.exception_count || 0;
  const paidInvoices = reportSummary?.paid_invoice_count || 0;

  const stats = [
    {
      title: "Total Invoices",
      value: invoiceCount,
      icon: FileText,
      color: "blue",
      trend: "All invoices",
    },
    {
      title: "Pending Review",
      value: pendingReview,
      icon: Clock3,
      color: "orange",
      trend: "Awaiting review",
    },
    {
      title: "Awaiting Approval",
      value: approvalCount,
      icon: ClipboardCheck,
      color: "purple",
      trend: "Your approval inbox",
    },
    {
      title: "Paid Invoices",
      value: paidInvoices,
      icon: CircleCheck,
      color: "green",
      trend: "Successfully paid",
    },
    {
      title: "Overdue Invoices",
      value: overdueInvoices,
      icon: Clock3,
      color: "orange",
      trend: "Open past-due invoices",
    },
    {
      title: "Exceptions",
      value: exceptionCount,
      icon: AlertCircle,
      color: "purple",
      trend: "Require review",
    },
  ];

  const paymentCards = paymentSummary.flatMap((currencySummary) => [
    { title: `Completed (${currencySummary.currency})`, amount: currencySummary.completed_payment_total, currency: currencySummary.currency, icon: CircleCheck, color: "green" },
    { title: `Pending (${currencySummary.currency})`, amount: currencySummary.pending_payment_total, currency: currencySummary.currency, icon: Clock3, color: "orange" },
    { title: `Outstanding (${currencySummary.currency})`, amount: currencySummary.outstanding_total, currency: currencySummary.currency, icon: Wallet, color: "blue" },
  ]);

  const filteredInvoices = useMemo(() => {
    const query = searchTerm.trim().toLowerCase();

    if (!query) return invoices;

    return invoices.filter((invoice) => {
      const invoiceNumber = String(invoice.invoice_number || "").toLowerCase();
      const vendorName = String(
        invoice.vendor_name ||
        invoice.vendor?.legal_name ||
        invoice.vendor?.name ||
        ""
      ).toLowerCase();
      const status = String(invoice.status || "").toLowerCase();

      return (
        invoiceNumber.includes(query) ||
        vendorName.includes(query) ||
        status.includes(query)
      );
    });
  }, [invoices, searchTerm]);

  const handleNavigation = (item) => {
    navigate(item.path);
  };

  const handleLogout = () => {
    logout();
    navigate("/", { replace: true });
  };

  return (
    <div className="dashboard-layout">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="sidebar-logo">P</div>
          <div>
            <h2>PayFlow</h2>
            <span>Accounts Payable</span>
          </div>
        </div>

        <div className="sidebar-section-title">WORKSPACE</div>

        <nav className="sidebar-nav" aria-label="Main navigation">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = item.path
              ? location.pathname === item.path
              : false;

            return (
              <button
                type="button"
                className={`nav-item ${isActive ? "active" : ""}`}
                key={item.label}
                title={item.label}
                onClick={() => handleNavigation(item)}
              >
                <Icon size={19} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        <div className="sidebar-bottom">
          <div className="sidebar-help">
            <AlertCircle size={18} className="help-icon" />
            <div>
              <strong>Need help?</strong>
              <span>Contact support</span>
            </div>
          </div>

          <button
            className="logout-button"
            onClick={handleLogout}
            type="button"
          >
            <LogOut size={18} />
            <span>Logout</span>
          </button>
        </div>
      </aside>

      <main className="dashboard-main">
        <header className="dashboard-header">
          <div>
            <h1>Dashboard</h1>
            <p>Welcome back! Here's your accounts payable overview.</p>
          </div>

          <div className="header-actions">
            <div className="header-search">
              <Search size={17} />
              <input
                type="search"
                placeholder="Search invoices..."
                value={searchTerm}
                onChange={(event) => setSearchTerm(event.target.value)}
                aria-label="Search invoices"
              />
            </div>

            <button
              className="icon-button"
              type="button"
              aria-label="Notifications"
              title={`Pending approvals: ${approvalCount}`}
              onClick={() => navigate("/approvals")}
            >
              <Bell size={19} />
            </button>

          </div>
        </header>

        <section className="welcome-section">
          <div>
            <h2>Good to see you!</h2>
            <p>Here's what's happening with your invoices today.</p>
          </div>

          <div className="today-date">
            {new Date().toLocaleDateString("en-IN", {
              weekday: "long",
              day: "numeric",
              month: "long",
              year: "numeric",
            })}
          </div>
        </section>

        {error && (
          <div className="dashboard-error">
            <AlertCircle size={18} />
            <span>{error}</span>
            <button type="button" onClick={loadDashboard}>
              Retry
            </button>
          </div>
        )}

        <section className="stats-grid">
          {stats.map((stat) => {
            const Icon = stat.icon;

            return (
              <div className="stat-card" key={stat.title}>
                <div className={`stat-icon ${stat.color}`}>
                  <Icon size={22} />
                </div>

                <div className="stat-content">
                  <p>{stat.title}</p>
                  <h2>{loading ? "—" : stat.value}</h2>
                  <span className="stat-trend">
                    <TrendingUp size={14} />
                    {stat.trend}
                  </span>
                </div>
              </div>
            );
          })}
        </section>

        <section className="payment-section">
          <div className="section-heading">
            <div>
              <h2>Payment Overview</h2>
              <p>Summary of your payment activity</p>
            </div>

            <button
              className="refresh-button"
              type="button"
              onClick={loadDashboard}
              disabled={loading}
            >
              <RefreshCw
                size={16}
                className={loading ? "spinning" : ""}
              />
              Refresh
            </button>
          </div>

          <div className="payment-grid">
            {paymentCards.map((card) => {
              const Icon = card.icon;

              return (
                <div className="payment-card" key={card.title}>
                  <div className={`payment-card-icon ${card.color}`}>
                    <Icon size={21} />
                  </div>

                  <div>
                    <p>{card.title}</p>
                    <h2>
                      {loading ? "—" : formatCurrency(card.amount, card.currency)}
                    </h2>
                  </div>
                </div>
              );
            })}
            {!loading && paymentCards.length === 0 && (
              <p className="table-message">No payment totals are available yet.</p>
            )}
          </div>
        </section>

        <section className="recent-section">
          <div className="section-heading recent-heading">
            <div>
              <h2>Recent Invoices</h2>
              <p>Latest invoices received by your organization</p>
            </div>

            <div className="recent-actions">
              <span className="record-count">
                {invoiceCount} invoices
              </span>

              <button
                type="button"
                className="upload-button"
                onClick={() => navigate("/invoices/upload")}
              >
                <Upload size={16} />
                Upload Invoice
              </button>
            </div>
          </div>

          {loading ? (
            <div className="table-message">Loading invoices...</div>
          ) : filteredInvoices.length === 0 ? (
            <div className="table-message">
              {searchTerm
                ? "No invoices match your search."
                : "No invoices found. Upload your first invoice."}
            </div>
          ) : (
            <div className="table-container">
              <table className="invoice-table">
                <thead>
                  <tr>
                    <th>Invoice Number</th>
                    <th>Vendor</th>
                    <th>Invoice Date</th>
                    <th>Amount</th>
                    <th>Status</th>
                  </tr>
                </thead>

                <tbody>
                  {filteredInvoices.slice(0, 5).map((invoice) => (
                    <tr key={invoice.id}>
                      <td className="invoice-number">
                        {invoice.invoice_number || "—"}
                      </td>

                      <td>
                        {invoice.vendor_name || invoice.vendor__legal_name || "—"}
                      </td>

                      <td>{formatDate(invoice.invoice_date)}</td>

                      <td className="invoice-amount">
                          {formatCurrency(invoice.total_amount, invoice.currency)}
                      </td>

                      <td>
                        <span
                          className={`status-badge ${statusClass(
                            invoice.status
                          )}`}
                        >
                          {String(invoice.status || "Unknown").replaceAll(
                            "_",
                            " "
                          )}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <footer className="dashboard-footer">
          PayFlow Accounts Payable Automation
          <span>Dashboard</span>
        </footer>
      </main>
    </div>
  );
}

export default Dashboard;
