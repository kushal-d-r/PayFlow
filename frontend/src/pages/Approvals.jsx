import { useCallback, useEffect, useState } from "react";

import {
  CheckCircle,
  XCircle,
  RefreshCw,
  Search,
  ClipboardCheck,
  Clock,
  FileText,
  MessageSquare,
  X,
  AlertCircle,
} from "lucide-react";

import api from "../services/api";
import "./Approvals.css";

function getList(data) {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.results)) return data.results;
  if (Array.isArray(data?.data)) return data.data;
  return [];
}

function formatCurrency(value, currency = "INR") {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(Number(value || 0));
}

function formatDate(value) {
  if (!value) return "—";

  return new Date(value).toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function getInvoice(approval) {
  return approval?.invoice_details || approval?.invoice || {};
}

function getVendorName(approval) {
  const invoice = getInvoice(approval);

  return (
    invoice?.vendor_details?.name ||
    invoice?.vendor_name ||
    invoice?.vendor?.name ||
    (typeof invoice?.vendor === "string" ? invoice.vendor : null) ||
    approval?.vendor_name ||
    "Unknown vendor"
  );
}

function getApprovalStatus(approval) {
  return (
    approval?.status ||
    approval?.approval_status ||
    approval?.current_status ||
    "PENDING"
  ).toUpperCase();
}

function Approvals() {
  const [approvals, setApprovals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");

  const [selectedApproval, setSelectedApproval] = useState(null);
  const [actionType, setActionType] = useState("");
  const [comments, setComments] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const loadApprovals = useCallback(async (showRefresh = false) => {
    if (showRefresh) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }

    setError("");

    try {
      const response = await api.get("/approvals/inbox/");
      setApprovals(getList(response.data));
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          err.response?.data?.message ||
          "Unable to load approval requests."
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function fetchInitialApprovals() {
      try {
        const response = await api.get("/approvals/inbox/");

        if (!cancelled) {
          setApprovals(getList(response.data));
          setError("");
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err.response?.data?.detail ||
              err.response?.data?.message ||
              "Unable to load approval requests."
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    fetchInitialApprovals();

    return () => {
      cancelled = true;
    };
  }, []);

  const filteredApprovals = approvals.filter((approval) => {
    const invoice = getInvoice(approval);
    const vendorName = getVendorName(approval);
    const status = getApprovalStatus(approval);

    const invoiceNumber =
      invoice?.invoice_number ||
      approval?.invoice_number ||
      "";

    const matchesSearch =
      invoiceNumber.toLowerCase().includes(search.toLowerCase()) ||
      vendorName.toLowerCase().includes(search.toLowerCase());

    const matchesStatus =
      statusFilter === "ALL" || status === statusFilter;

    return matchesSearch && matchesStatus;
  });

  const pendingCount = approvals.filter(
    (item) => getApprovalStatus(item) === "PENDING"
  ).length;

  const approvedCount = approvals.filter(
    (item) => getApprovalStatus(item) === "APPROVED"
  ).length;

  const rejectedCount = approvals.filter(
    (item) => getApprovalStatus(item) === "REJECTED"
  ).length;

  const openActionModal = (approval, type) => {
    setSelectedApproval(approval);
    setActionType(type);
    setComments("");
    setNotice("");
    setError("");
  };

  const closeActionModal = () => {
    if (submitting) return;

    setSelectedApproval(null);
    setActionType("");
    setComments("");
  };

  const submitDecision = async () => {
    if (!selectedApproval) return;

    const approvalId = selectedApproval.id;

    if (!approvalId) {
      setError("Approval ID is missing.");
      return;
    }

    setSubmitting(true);
    setError("");

    try {
      const endpoint =
        actionType === "approve"
          ? `/approvals/${approvalId}/approve/`
          : `/approvals/${approvalId}/reject/`;

      await api.post(endpoint, {
        comments: comments.trim(),
      });

      setNotice(
        actionType === "approve"
          ? "Approval completed successfully."
          : "Approval request rejected successfully."
      );

      setSelectedApproval(null);
      setActionType("");
      setComments("");

      await loadApprovals(true);
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          err.response?.data?.message ||
          JSON.stringify(err.response?.data || {}) ||
          "Unable to process this approval."
      );
    } finally {
      setSubmitting(false);
    }
  };

  const selectedInvoice = selectedApproval
    ? getInvoice(selectedApproval)
    : {};

  return (
    <div className="approvals-page">
      <div className="approvals-header">
        <div>
          <h1>Approvals</h1>
          <p>Review and manage invoice approval requests.</p>
        </div>

        <button
          className="approval-refresh-btn"
          onClick={() => loadApprovals(true)}
          disabled={refreshing}
        >
          <RefreshCw size={16} className={refreshing ? "spinning" : ""} />
          {refreshing ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      {notice && (
        <div className="approval-notice">
          <CheckCircle size={17} />
          {notice}
          <button onClick={() => setNotice("")} aria-label="Dismiss">
            <X size={16} />
          </button>
        </div>
      )}

      {error && (
        <div className="approval-error">
          <AlertCircle size={17} />
          <span>{error}</span>
          <button onClick={() => setError("")} aria-label="Dismiss">
            <X size={16} />
          </button>
        </div>
      )}

      <div className="approval-stats">
        <div className="approval-stat-card">
          <div className="approval-stat-icon pending-icon">
            <Clock size={21} />
          </div>
          <div>
            <span>Pending</span>
            <h2>{pendingCount}</h2>
          </div>
        </div>

        <div className="approval-stat-card">
          <div className="approval-stat-icon approved-icon">
            <CheckCircle size={21} />
          </div>
          <div>
            <span>Approved</span>
            <h2>{approvedCount}</h2>
          </div>
        </div>

        <div className="approval-stat-card">
          <div className="approval-stat-icon rejected-icon">
            <XCircle size={21} />
          </div>
          <div>
            <span>Rejected</span>
            <h2>{rejectedCount}</h2>
          </div>
        </div>

        <div className="approval-stat-card">
          <div className="approval-stat-icon total-icon">
            <ClipboardCheck size={21} />
          </div>
          <div>
            <span>Total Requests</span>
            <h2>{approvals.length}</h2>
          </div>
        </div>
      </div>

      <div className="approval-toolbar">
        <div className="approval-search">
          <Search size={18} />
          <input
            type="text"
            placeholder="Search invoice number or vendor..."
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>

        <select
          value={statusFilter}
          onChange={(event) => setStatusFilter(event.target.value)}
        >
          <option value="ALL">All statuses</option>
          <option value="PENDING">Pending</option>
          <option value="APPROVED">Approved</option>
          <option value="REJECTED">Rejected</option>
        </select>
      </div>

      <div className="approval-table-container">
        <div className="approval-table-heading">
          <h2>Approval Requests</h2>
          <span>{filteredApprovals.length} records</span>
        </div>

        {loading ? (
          <div className="approval-loading">
            <RefreshCw size={24} className="spinning" />
            <p>Loading approval requests...</p>
          </div>
        ) : filteredApprovals.length === 0 ? (
          <div className="approval-empty">
            <ClipboardCheck size={42} />
            <h3>No approval requests found</h3>
            <p>
              Approval requests will appear here when invoices enter the
              approval workflow.
            </p>
          </div>
        ) : (
          <div className="approval-table-scroll">
            <table className="approval-table">
              <thead>
                <tr>
                  <th>Invoice</th>
                  <th>Vendor</th>
                  <th>Amount</th>
                  <th>Due Date</th>
                  <th>Approval Step</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>

              <tbody>
                {filteredApprovals.map((approval) => {
                  const invoice = getInvoice(approval);
                  const status = getApprovalStatus(approval);

                  const invoiceNumber =
                    invoice?.invoice_number ||
                    approval?.invoice_number ||
                    `#${approval.id}`;

                  const amount =
                    invoice?.total_amount ??
                    approval?.total_amount ??
                    0;

                  const currency =
                    invoice?.currency ||
                    approval?.currency ||
                    "INR";

                  const step =
                    approval?.step_number ||
                    approval?.approval_step ||
                    approval?.step ||
                    "—";

                  return (
                    <tr key={approval.id}>
                      <td>
                        <div className="approval-invoice-cell">
                          <FileText size={18} />
                          <strong>{invoiceNumber}</strong>
                        </div>
                      </td>

                      <td>{getVendorName(approval)}</td>

                      <td className="approval-amount">
                        {formatCurrency(amount, currency)}
                      </td>

                      <td>{formatDate(invoice?.due_date)}</td>

                      <td>{step}</td>

                      <td>
                        <span
                          className={`approval-status status-${status.toLowerCase()}`}
                        >
                          {status.replaceAll("_", " ")}
                        </span>
                      </td>

                      <td>
                        <div className="approval-actions">
                          <button
                            className="approval-view-btn"
                            onClick={() => setSelectedApproval(approval)}
                            title="View details"
                          >
                            View
                          </button>

                          {status === "PENDING" && (
                            <>
                              <button
                                className="approval-approve-btn"
                                onClick={() =>
                                  openActionModal(approval, "approve")
                                }
                                title="Approve"
                              >
                                <CheckCircle size={16} />
                              </button>

                              <button
                                className="approval-reject-btn"
                                onClick={() =>
                                  openActionModal(approval, "reject")
                                }
                                title="Reject"
                              >
                                <XCircle size={16} />
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {selectedApproval && !actionType && (
        <div className="approval-modal-overlay" onClick={closeActionModal}>
          <div
            className="approval-modal"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="approval-modal-header">
              <div>
                <h2>Approval Details</h2>
                <p>Invoice information and workflow details</p>
              </div>
              <button onClick={closeActionModal} aria-label="Close">
                <X size={20} />
              </button>
            </div>

            <div className="approval-detail-grid">
              <div className="approval-detail-item">
                <span>Invoice Number</span>
                <strong>
                  {selectedInvoice?.invoice_number ||
                    selectedApproval?.invoice_number ||
                    "—"}
                </strong>
              </div>

              <div className="approval-detail-item">
                <span>Vendor</span>
                <strong>{getVendorName(selectedApproval)}</strong>
              </div>

              <div className="approval-detail-item">
                <span>Invoice Date</span>
                <strong>{formatDate(selectedInvoice?.invoice_date)}</strong>
              </div>

              <div className="approval-detail-item">
                <span>Due Date</span>
                <strong>{formatDate(selectedInvoice?.due_date)}</strong>
              </div>

              <div className="approval-detail-item">
                <span>Total Amount</span>
                <strong>
                  {formatCurrency(
                    selectedInvoice?.total_amount ||
                      selectedApproval?.total_amount,
                    selectedInvoice?.currency || "INR"
                  )}
                </strong>
              </div>

              <div className="approval-detail-item">
                <span>Status</span>
                <strong>
                  {getApprovalStatus(selectedApproval).replaceAll("_", " ")}
                </strong>
              </div>

              <div className="approval-detail-item">
                <span>Approval Step</span>
                <strong>
                  {selectedApproval?.step_number ||
                    selectedApproval?.approval_step ||
                    selectedApproval?.step ||
                    "—"}
                </strong>
              </div>

              <div className="approval-detail-item">
                <span>Assigned To</span>
                <strong>
                  {selectedApproval?.assigned_to_username ||
                    selectedApproval?.assigned_to?.username ||
                    selectedApproval?.approver_username ||
                    "—"}
                </strong>
              </div>
            </div>

            {selectedApproval?.history?.length > 0 && (
              <div className="approval-history">
                <h3>Approval history</h3>
                {selectedApproval.history.map((entry) => (
                  <div className="approval-history-item" key={entry.id}>
                    <div><strong>{entry.action.replaceAll("_", " ")}</strong><span>{formatDate(entry.created_at)}</span></div>
                    <p>{entry.actor_name || "User"}{entry.comments ? ` · ${entry.comments}` : ""}</p>
                  </div>
                ))}
              </div>
            )}

            {selectedApproval?.comments && (
              <div className="approval-comments-display">
                <MessageSquare size={17} />
                <div>
                  <strong>Comments</strong>
                  <p>{selectedApproval.comments}</p>
                </div>
              </div>
            )}

            {getApprovalStatus(selectedApproval) === "PENDING" && (
              <div className="approval-modal-actions">
                <button
                  className="approval-approve-btn large"
                  onClick={() =>
                    openActionModal(selectedApproval, "approve")
                  }
                >
                  <CheckCircle size={17} />
                  Approve
                </button>

                <button
                  className="approval-reject-btn large"
                  onClick={() =>
                    openActionModal(selectedApproval, "reject")
                  }
                >
                  <XCircle size={17} />
                  Reject
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {selectedApproval && actionType && (
        <div
          className="approval-modal-overlay"
          onClick={closeActionModal}
        >
          <div
            className="approval-modal approval-decision-modal"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="approval-modal-header">
              <div>
                <h2>
                  {actionType === "approve"
                    ? "Approve Invoice"
                    : "Reject Invoice"}
                </h2>
                <p>
                  {selectedInvoice?.invoice_number ||
                    selectedApproval?.invoice_number ||
                    `Approval #${selectedApproval.id}`}
                </p>
              </div>

              <button onClick={closeActionModal} aria-label="Close">
                <X size={20} />
              </button>
            </div>

            <div
              className={`approval-decision-banner ${actionType}`}
            >
              {actionType === "approve" ? (
                <CheckCircle size={22} />
              ) : (
                <XCircle size={22} />
              )}

              <span>
                {actionType === "approve"
                  ? "You are about to approve this invoice."
                  : "You are about to reject this invoice."}
              </span>
            </div>

            <label className="approval-comment-label">
              Comments
              {actionType === "reject" && <span> (recommended)</span>}
            </label>

            <textarea
              value={comments}
              onChange={(event) => setComments(event.target.value)}
              placeholder="Enter your comments..."
              rows={4}
            />

            <div className="approval-modal-actions">
              <button
                className="approval-cancel-btn"
                onClick={closeActionModal}
                disabled={submitting}
              >
                Cancel
              </button>

              <button
                className={
                  actionType === "approve"
                    ? "approval-approve-btn large"
                    : "approval-reject-btn large"
                }
                onClick={submitDecision}
                disabled={submitting}
              >
                {submitting
                  ? "Processing..."
                  : actionType === "approve"
                    ? "Confirm Approval"
                    : "Confirm Rejection"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Approvals;
