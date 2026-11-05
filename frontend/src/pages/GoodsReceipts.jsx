
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Plus,
  RefreshCw,
  Search,
  X,
  Eye,
  PackageCheck,
  CheckCircle,
  AlertCircle,
} from "lucide-react";

import api from "../services/api";
import "./GoodsReceipts.css";

const today = () => {
  const date = new Date();
  const offset = date.getTimezoneOffset();

  return new Date(date.getTime() - offset * 60000)
    .toISOString()
    .slice(0, 10);
};

const emptyForm = () => ({
  grn_number: "",
  purchase_order: "",
  received_date: today(),
  notes: "",
  items: [],
});

const getList = (data) => {
  if (Array.isArray(data)) return data;
  return data?.results || [];
};

// Fetch data separately so the initial effect only updates state
// after the asynchronous request has completed.
const fetchGoodsReceiptData = async () => {
  const [grnResponse, poResponse] = await Promise.all([
    api.get("/goods-receipts/"),
    api.get("/purchase-orders/"),
  ]);

  return {
    receipts: getList(grnResponse.data),
    purchaseOrders: getList(poResponse.data),
  };
};

function GoodsReceipts() {
  const [receipts, setReceipts] = useState([]);
  const [purchaseOrders, setPurchaseOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [selectedGRN, setSelectedGRN] = useState(null);
  const [form, setForm] = useState(emptyForm());
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // Load GRNs and purchase orders (used by Refresh and after actions)
  const loadData = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const data = await fetchGoodsReceiptData();
      setReceipts(data.receipts);
      setPurchaseOrders(data.purchaseOrders);
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          "Unable to load goods receipts."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial load: state updates happen in async callbacks after the request.
  useEffect(() => {
    let cancelled = false;

    fetchGoodsReceiptData()
      .then((data) => {
        if (cancelled) return;
        setReceipts(data.receipts);
        setPurchaseOrders(data.purchaseOrders);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(
          err.response?.data?.detail ||
            "Unable to load goods receipts."
        );
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  // Purchase orders eligible for receiving goods
  const eligiblePOs = useMemo(() => {
    return purchaseOrders.filter((po) =>
      ["ISSUED", "PARTIALLY_RECEIVED"].includes(po.status)
    );
  }, [purchaseOrders]);

  // Search and filter GRNs
  const filteredReceipts = useMemo(() => {
    return receipts.filter((grn) => {
      const searchText = search.toLowerCase();

      const matchesSearch =
        grn.grn_number?.toLowerCase().includes(searchText) ||
        grn.po_number?.toLowerCase().includes(searchText);

      const matchesStatus =
        statusFilter === "ALL" || grn.status === statusFilter;

      return matchesSearch && matchesStatus;
    });
  }, [receipts, search, statusFilter]);

  // Select PO and load its items
  const selectPO = async (poId) => {
    setForm((previous) => ({
      ...previous,
      purchase_order: poId,
      items: [],
    }));

    setError("");

    if (!poId) return;

    try {
      const response = await api.get(`/purchase-orders/${poId}/`);
      const po = response.data;

      setForm((previous) => ({
        ...previous,
        items: (po.items || []).map((item) => ({
          purchase_order_item: item.id,
          po_item_description: item.description,
          received_quantity: "0",
          accepted_quantity: "0",
          rejected_quantity: "0",
          notes: "",
        })),
      }));
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          "Unable to load purchase order items."
      );
    }
  };

  // Update item quantity or notes
  const updateItem = (index, field, value) => {
    setForm((previous) => ({
      ...previous,
      items: previous.items.map((item, i) =>
        i === index ? { ...item, [field]: value } : item
      ),
    }));
  };

  // Create goods receipt
  const createGRN = async (event) => {
    event.preventDefault();

    setSaving(true);
    setError("");
    setSuccess("");

    if (!form.purchase_order) {
      setError("Please select a purchase order.");
      setSaving(false);
      return;
    }

    if (!form.items.length) {
      setError("Select a purchase order with items first.");
      setSaving(false);
      return;
    }

    const invalidItem = form.items.find((item) => {
      const received = Number(item.received_quantity);
      const accepted = Number(item.accepted_quantity);
      const rejected = Number(item.rejected_quantity);

      return (
        received <= 0 ||
        accepted < 0 ||
        rejected < 0 ||
        accepted + rejected > received
      );
    });

    if (invalidItem) {
      setError(
        "Check item quantities. Received quantity must be greater than zero, and accepted plus rejected cannot exceed received quantity."
      );
      setSaving(false);
      return;
    }

    try {
      const payload = {
        grn_number: form.grn_number.trim(),
        purchase_order: Number(form.purchase_order),
        received_date: form.received_date,
        notes: form.notes,
        items: form.items.map((item) => ({
          purchase_order_item: Number(item.purchase_order_item),
          received_quantity: Number(item.received_quantity),
          accepted_quantity: Number(item.accepted_quantity),
          rejected_quantity: Number(item.rejected_quantity),
          notes: item.notes,
        })),
      };

      const response = await api.post(
        "/goods-receipts/",
        payload
      );

      setSuccess(
        `Goods receipt ${response.data.grn_number} created successfully.`
      );

      setShowForm(false);
      setForm(emptyForm());

      await loadData();
    } catch (err) {
      const data = err.response?.data;

      setError(
        typeof data === "string"
          ? data
          : JSON.stringify(
              data || "Unable to create goods receipt."
            )
      );
    } finally {
      setSaving(false);
    }
  };

  // Accept a goods receipt
  const acceptGRN = async (id) => {
    if (!window.confirm("Accept this goods receipt?")) return;

    setError("");
    setSuccess("");

    try {
      await api.post(`/goods-receipts/${id}/accept/`, {});

      setSuccess("Goods receipt accepted successfully.");

      await loadData();

      if (selectedGRN?.id === id) {
        const response = await api.get(`/goods-receipts/${id}/`);
        setSelectedGRN(response.data);
      }
    } catch (err) {
      setError(
        err.response?.data?.error ||
          err.response?.data?.detail ||
          "Unable to accept goods receipt."
      );
    }
  };

  // View GRN details
  const viewGRN = async (id) => {
    try {
      const response = await api.get(`/goods-receipts/${id}/`);
      setSelectedGRN(response.data);
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          "Unable to load goods receipt details."
      );
    }
  };

  const statusClass = (status) =>
    `grn-status grn-status-${(status || "").toLowerCase()}`;

  return (
    <div className="grn-page">
      {/* Header */}
      <div className="grn-heading">
        <div>
          <h1>Goods Receipts</h1>
          <p>
            Record deliveries and verify received quantities against
            purchase orders.
          </p>
        </div>

        <div className="grn-heading-actions">
          <button
            className="grn-btn grn-btn-secondary"
            onClick={loadData}
            type="button"
          >
            <RefreshCw size={16} /> Refresh
          </button>

          <button
            className="grn-btn grn-btn-primary"
            onClick={() => {
              setError("");
              setForm(emptyForm());
              setShowForm(true);
            }}
            type="button"
          >
            <Plus size={17} /> Create GRN
          </button>
        </div>
      </div>

      {/* Error message */}
      {error && (
        <div className="grn-alert grn-alert-error">
          <AlertCircle size={18} />
          <span>{error}</span>
          <button onClick={() => setError("")} type="button">
            <X size={16} />
          </button>
        </div>
      )}

      {/* Success message */}
      {success && (
        <div className="grn-alert grn-alert-success">
          <CheckCircle size={18} />
          <span>{success}</span>
          <button onClick={() => setSuccess("")} type="button">
            <X size={16} />
          </button>
        </div>
      )}

      {/* Statistics */}
      <div className="grn-stats">
        <div className="grn-stat-card">
          <PackageCheck />
          <div>
            <span>Total GRNs</span>
            <strong>{receipts.length}</strong>
          </div>
        </div>

        <div className="grn-stat-card">
          <span className="grn-dot grn-dot-draft" />
          <div>
            <span>Draft</span>
            <strong>
              {receipts.filter((g) => g.status === "DRAFT").length}
            </strong>
          </div>
        </div>

        <div className="grn-stat-card">
          <span className="grn-dot grn-dot-accepted" />
          <div>
            <span>Accepted</span>
            <strong>
              {receipts.filter((g) => g.status === "ACCEPTED").length}
            </strong>
          </div>
        </div>

        <div className="grn-stat-card">
          <span className="grn-dot grn-dot-rejected" />
          <div>
            <span>Rejected</span>
            <strong>
              {receipts.filter((g) => g.status === "REJECTED").length}
            </strong>
          </div>
        </div>
      </div>

      {/* Search and filters */}
      <div className="grn-toolbar">
        <div className="grn-search">
          <Search size={18} />
          <input
            placeholder="Search GRN or PO number..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="ALL">All statuses</option>
          <option value="DRAFT">Draft</option>
          <option value="RECEIVED">Received</option>
          <option value="ACCEPTED">Accepted</option>
          <option value="REJECTED">Rejected</option>
        </select>
      </div>

      {/* GRN table */}
      <div className="grn-table-wrap">
        {loading ? (
          <div className="grn-empty">
            Loading goods receipts...
          </div>
        ) : filteredReceipts.length === 0 ? (
          <div className="grn-empty">
            No goods receipts found.
          </div>
        ) : (
          <table className="grn-table">
            <thead>
              <tr>
                <th>GRN Number</th>
                <th>Purchase Order</th>
                <th>Received Date</th>
                <th>Items</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>

            <tbody>
              {filteredReceipts.map((grn) => (
                <tr key={grn.id}>
                  <td>
                    <strong>{grn.grn_number}</strong>
                  </td>

                  <td>
                    {grn.po_number || `PO #${grn.purchase_order}`}
                  </td>

                  <td>{grn.received_date}</td>

                  <td>{grn.items?.length ?? 0}</td>

                  <td>
                    <span className={statusClass(grn.status)}>
                      {grn.status}
                    </span>
                  </td>

                  <td>
                    <div className="grn-row-actions">
                      <button
                        title="View details"
                        onClick={() => viewGRN(grn.id)}
                        type="button"
                      >
                        <Eye size={17} />
                      </button>

                      {grn.status === "DRAFT" && (
                        <button
                          title="Accept GRN"
                          onClick={() => acceptGRN(grn.id)}
                          type="button"
                        >
                          <CheckCircle size={17} />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Create GRN modal */}
      {showForm && (
        <div className="grn-modal-backdrop">
          <form className="grn-modal" onSubmit={createGRN}>
            <div className="grn-modal-heading">
              <div>
                <h2>Create Goods Receipt</h2>
                <p>
                  Record items delivered against a purchase order.
                </p>
              </div>

              <button
                type="button"
                onClick={() => setShowForm(false)}
              >
                <X />
              </button>
            </div>

            <div className="grn-form-grid">
              <label>
                GRN Number *
                <input
                  required
                  maxLength="50"
                  value={form.grn_number}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      grn_number: e.target.value.toUpperCase(),
                    })
                  }
                  placeholder="GRN-2026-001"
                />
              </label>

              <label>
                Purchase Order *
                <select
                  required
                  value={form.purchase_order}
                  onChange={(e) => selectPO(e.target.value)}
                >
                  <option value="">Select issued PO</option>

                  {eligiblePOs.map((po) => (
                    <option key={po.id} value={po.id}>
                      {po.po_number} —{" "}
                      {po.vendor_name || `Vendor #${po.vendor}`}
                    </option>
                  ))}
                </select>
              </label>

              <label>
                Received Date *
                <input
                  required
                  type="date"
                  value={form.received_date}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      received_date: e.target.value,
                    })
                  }
                />
              </label>

              <label>
                Notes
                <input
                  value={form.notes}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      notes: e.target.value,
                    })
                  }
                  placeholder="Delivery notes"
                />
              </label>
            </div>

            <div className="grn-items-heading">
              <h3>Received Items</h3>
              <span>{form.items.length} PO items</span>
            </div>

            {!form.purchase_order && (
              <div className="grn-empty-inline">
                Select a purchase order to load its items.
              </div>
            )}

            {form.purchase_order && form.items.length === 0 && (
              <div className="grn-empty-inline">
                No items found for this purchase order.
              </div>
            )}

            {form.items.map((item, index) => (
              <div
                className="grn-item-form"
                key={item.purchase_order_item}
              >
                <strong>{item.po_item_description}</strong>

                <div className="grn-item-grid">
                  <label>
                    Received Qty *
                    <input
                      type="number"
                      min="0.001"
                      step="0.001"
                      required
                      value={item.received_quantity}
                      onChange={(e) =>
                        updateItem(
                          index,
                          "received_quantity",
                          e.target.value
                        )
                      }
                    />
                  </label>

                  <label>
                    Accepted Qty *
                    <input
                      type="number"
                      min="0"
                      step="0.001"
                      required
                      value={item.accepted_quantity}
                      onChange={(e) =>
                        updateItem(
                          index,
                          "accepted_quantity",
                          e.target.value
                        )
                      }
                    />
                  </label>

                  <label>
                    Rejected Qty *
                    <input
                      type="number"
                      min="0"
                      step="0.001"
                      required
                      value={item.rejected_quantity}
                      onChange={(e) =>
                        updateItem(
                          index,
                          "rejected_quantity",
                          e.target.value
                        )
                      }
                    />
                  </label>

                  <label>
                    Item Notes
                    <input
                      value={item.notes}
                      onChange={(e) =>
                        updateItem(index, "notes", e.target.value)
                      }
                    />
                  </label>
                </div>

                <small>
                  Accepted + rejected quantity must not exceed
                  received quantity.
                </small>
              </div>
            ))}

            <div className="grn-modal-actions">
              <button
                type="button"
                className="grn-btn grn-btn-secondary"
                onClick={() => setShowForm(false)}
              >
                Cancel
              </button>

              <button
                type="submit"
                className="grn-btn grn-btn-primary"
                disabled={saving || !form.items.length}
              >
                {saving ? "Creating..." : "Create Draft GRN"}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* GRN details modal */}
      {selectedGRN && (
        <div
          className="grn-modal-backdrop"
          onClick={() => setSelectedGRN(null)}
        >
          <div
            className="grn-modal grn-detail-modal"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="grn-modal-heading">
              <div>
                <h2>{selectedGRN.grn_number}</h2>
                <p>
                  Purchase Order:{" "}
                  {selectedGRN.po_number ||
                    selectedGRN.purchase_order}
                </p>
              </div>

              <button
                type="button"
                onClick={() => setSelectedGRN(null)}
              >
                <X />
              </button>
            </div>

            <p>
              <strong>Status:</strong>{" "}
              <span className={statusClass(selectedGRN.status)}>
                {selectedGRN.status}
              </span>
            </p>

            <p>
              <strong>Received Date:</strong>{" "}
              {selectedGRN.received_date}
            </p>

            <h3>Received Items</h3>

            <div className="grn-table-wrap">
              <table className="grn-table">
                <thead>
                  <tr>
                    <th>Item</th>
                    <th>Received</th>
                    <th>Accepted</th>
                    <th>Rejected</th>
                  </tr>
                </thead>

                <tbody>
                  {(selectedGRN.items || []).map((item) => (
                    <tr key={item.id}>
                      <td>
                        {item.po_item_description ||
                          item.purchase_order_item}
                      </td>
                      <td>{item.received_quantity}</td>
                      <td>{item.accepted_quantity}</td>
                      <td>{item.rejected_quantity}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {selectedGRN.status === "DRAFT" && (
              <button
                className="grn-btn grn-btn-primary"
                onClick={() => acceptGRN(selectedGRN.id)}
                type="button"
              >
                <CheckCircle size={16} />
                Accept Goods Receipt
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default GoodsReceipts;
