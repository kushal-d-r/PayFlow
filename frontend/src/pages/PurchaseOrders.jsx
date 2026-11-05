
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Plus,
  Search,
  RefreshCw,
  Eye,
  Send,
  X,
  ShoppingCart,
  Package,
  IndianRupee,
  AlertCircle,
  Trash2,
} from "lucide-react";

import api from "../services/api";
import "./PurchaseOrders.css";

function getList(data) {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.results)) return data.results;
  if (Array.isArray(data?.data)) return data.data;
  return [];
}

function formatMoney(value, currency = "INR") {
  try {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency,
      maximumFractionDigits: 2,
    }).format(Number(value || 0));
  } catch {
    return `${currency} ${Number(value || 0).toFixed(2)}`;
  }
}

function PurchaseOrders() {
  const [orders, setOrders] = useState([]);
  const [vendors, setVendors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");

  const [showCreate, setShowCreate] = useState(false);
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const [form, setForm] = useState({
    po_number: "",
    vendor: "",
    order_date: new Date().toISOString().slice(0, 10),
    expected_delivery_date: "",
    currency: "INR",
    notes: "",
    items: [
      {
        line_number: 1,
        item_code: "",
        description: "",
        unit_of_measure: "UNIT",
        quantity: "1",
        unit_price: "0",
        tax_rate: "18",
      },
    ],
  });

  const loadData = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const [poResponse, vendorResponse] = await Promise.all([
        api.get("/purchase-orders/"),
        api.get("/vendors/"),
      ]);

      setOrders(getList(poResponse.data));
      setVendors(getList(vendorResponse.data));
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          err.response?.data?.message ||
          "Unable to load purchase orders."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial loading: API state updates happen after asynchronous requests.
  useEffect(() => {
    let cancelled = false;

    async function fetchInitialData() {
      try {
        const [poResponse, vendorResponse] = await Promise.all([
          api.get("/purchase-orders/"),
          api.get("/vendors/"),
        ]);

        if (!cancelled) {
          setOrders(getList(poResponse.data));
          setVendors(getList(vendorResponse.data));
          setError("");
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err.response?.data?.detail ||
              err.response?.data?.message ||
              "Unable to load purchase orders."
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    fetchInitialData();

    return () => {
      cancelled = true;
    };
  }, []);

  const filteredOrders = useMemo(() => {
    return orders.filter((order) => {
      const vendorName =
        order.vendor_name ||
        order.vendor_details?.legal_name ||
        order.vendor_details?.display_name ||
        order.vendor?.legal_name ||
        order.vendor?.display_name ||
        "";

      const matchesSearch =
        String(order.po_number || "")
          .toLowerCase()
          .includes(search.toLowerCase()) ||
        String(vendorName).toLowerCase().includes(search.toLowerCase());

      const matchesStatus =
        statusFilter === "ALL" ||
        String(order.status || "").toUpperCase() === statusFilter;

      return matchesSearch && matchesStatus;
    });
  }, [orders, search, statusFilter]);

  const stats = useMemo(() => {
    return {
      total: orders.length,
      draft: orders.filter((o) => o.status === "DRAFT").length,
      issued: orders.filter((o) => o.status === "ISSUED").length,
      received: orders.filter((o) =>
        ["PARTIALLY_RECEIVED", "FULLY_RECEIVED"].includes(o.status)
      ).length,
    };
  }, [orders]);

  const updateForm = (field, value) => {
    setForm((previous) => ({
      ...previous,
      [field]: value,
    }));
  };

  const updateItem = (index, field, value) => {
    setForm((previous) => ({
      ...previous,
      items: previous.items.map((item, i) =>
        i === index ? { ...item, [field]: value } : item
      ),
    }));
  };

  const addItem = () => {
    setForm((previous) => ({
      ...previous,
      items: [
        ...previous.items,
        {
          line_number: previous.items.length + 1,
          item_code: "",
          description: "",
          unit_of_measure: "UNIT",
          quantity: "1",
          unit_price: "0",
          tax_rate: "18",
        },
      ],
    }));
  };

  const removeItem = (index) => {
    setForm((previous) => ({
      ...previous,
      items: previous.items
        .filter((_, i) => i !== index)
        .map((item, i) => ({
          ...item,
          line_number: i + 1,
        })),
    }));
  };

  const resetForm = () => {
    setForm({
      po_number: "",
      vendor: "",
      order_date: new Date().toISOString().slice(0, 10),
      expected_delivery_date: "",
      currency: "INR",
      notes: "",
      items: [
        {
          line_number: 1,
          item_code: "",
          description: "",
          unit_of_measure: "UNIT",
          quantity: "1",
          unit_price: "0",
          tax_rate: "18",
        },
      ],
    });
  };

  const createOrder = async (event) => {
    event.preventDefault();
    setError("");
    setNotice("");

    if (!form.vendor) {
      setError("Please select a vendor.");
      return;
    }

    if (!form.po_number.trim()) {
      setError("Please enter a purchase order number.");
      return;
    }

    if (form.items.length === 0) {
      setError("Add at least one purchase order item.");
      return;
    }

    for (const item of form.items) {
      if (!item.description.trim()) {
        setError("Every item must have a description.");
        return;
      }

      if (
        Number(item.quantity) <= 0 ||
        Number(item.unit_price) < 0 ||
        Number(item.tax_rate) < 0
      ) {
        setError("Enter valid quantity, price, and tax values.");
        return;
      }
    }

    const payload = {
      po_number: form.po_number.trim(),
      vendor: Number(form.vendor),
      order_date: form.order_date,
      expected_delivery_date: form.expected_delivery_date || null,
      currency: form.currency,
      notes: form.notes,
      items: form.items.map((item) => ({
        line_number: Number(item.line_number),
        item_code: item.item_code.trim(),
        description: item.description.trim(),
        unit_of_measure: item.unit_of_measure,
        quantity: Number(item.quantity),
        unit_price: Number(item.unit_price),
        tax_rate: Number(item.tax_rate),
      })),
    };

    setSubmitting(true);

    try {
      await api.post("/purchase-orders/", payload);

      setShowCreate(false);
      resetForm();
      setNotice("Purchase order created successfully.");
      await loadData();
    } catch (err) {
      const data = err.response?.data;
      setError(
        data?.detail ||
          data?.message ||
          (typeof data === "object"
            ? JSON.stringify(data)
            : "Unable to create purchase order.")
      );
    } finally {
      setSubmitting(false);
    }
  };

  const issueOrder = async (order) => {
    if (
      !window.confirm(
        `Are you sure you want to issue purchase order ${order.po_number}?`
      )
    ) {
      return;
    }

    setError("");
    setNotice("");

    try {
      await api.post(`/purchase-orders/${order.id}/issue/`);
      setNotice(`Purchase order ${order.po_number} issued successfully.`);
      await loadData();
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          err.response?.data?.message ||
          "Unable to issue purchase order."
      );
    }
  };

  const viewOrder = async (order) => {
    setError("");

    try {
      const response = await api.get(`/purchase-orders/${order.id}/`);
      setSelectedOrder(response.data);
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          "Unable to load purchase order details."
      );
    }
  };

  const getVendorName = (order) => {
    return (
      order.vendor_name ||
      order.vendor_details?.display_name ||
      order.vendor_details?.legal_name ||
      order.vendor?.display_name ||
      order.vendor?.legal_name ||
      vendors.find((v) => v.id === order.vendor)?.display_name ||
      vendors.find((v) => v.id === order.vendor)?.legal_name ||
      "Unknown vendor"
    );
  };

  const getOrderTotal = (order) => {
    if (order.total_amount != null) return Number(order.total_amount);

    const items = order.items || [];
    return items.reduce((total, item) => {
      const base = Number(item.quantity || 0) * Number(item.unit_price || 0);
      const tax = base * (Number(item.tax_rate || 0) / 100);
      return total + base + tax;
    }, 0);
  };

  return (
    <div className="purchase-orders-page">
      <div className="po-header">
        <div>
          <h1>Purchase Orders</h1>
          <p>Create, manage, and track vendor purchase orders.</p>
        </div>

        <div className="po-header-actions">
          <button
            className="po-refresh-btn"
            onClick={loadData}
            disabled={loading}
          >
            <RefreshCw size={16} />
            Refresh
          </button>

          <button
            className="po-primary-btn"
            onClick={() => {
              setError("");
              setNotice("");
              setShowCreate(true);
            }}
          >
            <Plus size={17} />
            Create Purchase Order
          </button>
        </div>
      </div>

      {error && (
        <div className="po-message po-error">
          <AlertCircle size={17} />
          <span>{error}</span>
          <button onClick={() => setError("")}>
            <X size={16} />
          </button>
        </div>
      )}

      {notice && (
        <div className="po-message po-success">
          <span>{notice}</span>
          <button onClick={() => setNotice("")}>
            <X size={16} />
          </button>
        </div>
      )}

      <div className="po-stats">
        <div className="po-stat-card">
          <div className="po-stat-icon blue">
            <ShoppingCart size={22} />
          </div>
          <div>
            <span>Total orders</span>
            <strong>{stats.total}</strong>
          </div>
        </div>

        <div className="po-stat-card">
          <div className="po-stat-icon orange">
            <Package size={22} />
          </div>
          <div>
            <span>Draft</span>
            <strong>{stats.draft}</strong>
          </div>
        </div>

        <div className="po-stat-card">
          <div className="po-stat-icon green">
            <Send size={22} />
          </div>
          <div>
            <span>Issued</span>
            <strong>{stats.issued}</strong>
          </div>
        </div>

        <div className="po-stat-card">
          <div className="po-stat-icon purple">
            <IndianRupee size={22} />
          </div>
          <div>
            <span>Received orders</span>
            <strong>{stats.received}</strong>
          </div>
        </div>
      </div>

      <div className="po-toolbar">
        <div className="po-search">
          <Search size={18} />
          <input
            type="text"
            placeholder="Search PO number or vendor..."
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
          <option value="ISSUED">Issued</option>
          <option value="PARTIALLY_RECEIVED">Partially received</option>
          <option value="FULLY_RECEIVED">Fully received</option>
          <option value="CANCELLED">Cancelled</option>
        </select>
      </div>

      <div className="po-table-container">
        <table className="po-table">
          <thead>
            <tr>
              <th>PO Number</th>
              <th>Vendor</th>
              <th>Order Date</th>
              <th>Expected Delivery</th>
              <th>Amount</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>

          <tbody>
            {loading ? (
              <tr>
                <td colSpan="7" className="po-empty">
                  Loading purchase orders...
                </td>
              </tr>
            ) : filteredOrders.length === 0 ? (
              <tr>
                <td colSpan="7" className="po-empty">
                  No purchase orders found.
                </td>
              </tr>
            ) : (
              filteredOrders.map((order) => (
                <tr key={order.id}>
                  <td>
                    <strong>{order.po_number}</strong>
                    <small>PO #{order.id}</small>
                  </td>

                  <td>{getVendorName(order)}</td>

                  <td>
                    {order.order_date
                      ? new Date(order.order_date).toLocaleDateString()
                      : "—"}
                  </td>

                  <td>
                    {order.expected_delivery_date
                      ? new Date(
                          order.expected_delivery_date
                        ).toLocaleDateString()
                      : "—"}
                  </td>

                  <td className="po-amount">
                    {formatMoney(
                      getOrderTotal(order),
                      order.currency || "INR"
                    )}
                  </td>

                  <td>
                    <span
                      className={`po-status ${String(
                        order.status || "DRAFT"
                      ).toLowerCase()}`}
                    >
                      {String(order.status || "DRAFT").replaceAll("_", " ")}
                    </span>
                  </td>

                  <td>
                    <div className="po-actions">
                      <button
                        className="po-icon-btn"
                        title="View details"
                        onClick={() => viewOrder(order)}
                      >
                        <Eye size={17} />
                      </button>

                      {order.status === "DRAFT" && (
                        <button
                          className="po-issue-btn"
                          onClick={() => issueOrder(order)}
                        >
                          <Send size={14} />
                          Issue
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {showCreate && (
        <div
          className="po-modal-backdrop"
          onClick={() => !submitting && setShowCreate(false)}
        >
          <div
            className="po-modal po-create-modal"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="po-modal-header">
              <div>
                <h2>Create Purchase Order</h2>
                <p>Enter vendor and order item details.</p>
              </div>

              <button
                className="po-close-btn"
                onClick={() => setShowCreate(false)}
                disabled={submitting}
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={createOrder}>
              <div className="po-form-grid">
                <label>
                  PO Number *
                  <input
                    required
                    value={form.po_number}
                    onChange={(e) => updateForm("po_number", e.target.value)}
                    placeholder="PO-2026-001"
                  />
                </label>

                <label>
                  Vendor *
                  <select
                    required
                    value={form.vendor}
                    onChange={(e) => updateForm("vendor", e.target.value)}
                  >
                    <option value="">Select vendor</option>
                    {vendors.map((vendor) => (
                      <option key={vendor.id} value={vendor.id}>
                        {vendor.display_name ||
                          vendor.legal_name ||
                          vendor.vendor_code}
                      </option>
                    ))}
                  </select>
                </label>

                <label>
                  Order Date *
                  <input
                    type="date"
                    required
                    value={form.order_date}
                    onChange={(e) => updateForm("order_date", e.target.value)}
                  />
                </label>

                <label>
                  Expected Delivery Date
                  <input
                    type="date"
                    value={form.expected_delivery_date}
                    min={form.order_date}
                    onChange={(e) =>
                      updateForm("expected_delivery_date", e.target.value)
                    }
                  />
                </label>

                <label>
                  Currency *
                  <select
                    value={form.currency}
                    onChange={(e) => updateForm("currency", e.target.value)}
                  >
                    <option value="INR">INR</option>
                    <option value="USD">USD</option>
                    <option value="EUR">EUR</option>
                    <option value="GBP">GBP</option>
                  </select>
                </label>

                <label className="po-full-width">
                  Notes
                  <textarea
                    rows="2"
                    value={form.notes}
                    onChange={(e) => updateForm("notes", e.target.value)}
                    placeholder="Additional order information..."
                  />
                </label>
              </div>

              <div className="po-items-heading">
                <h3>Purchase Order Items</h3>
                <button
                  type="button"
                  className="po-add-item-btn"
                  onClick={addItem}
                >
                  <Plus size={15} />
                  Add item
                </button>
              </div>

              {form.items.map((item, index) => (
                <div className="po-item-card" key={index}>
                  <div className="po-item-title">
                    <strong>Item {index + 1}</strong>

                    {form.items.length > 1 && (
                      <button
                        type="button"
                        className="po-remove-item-btn"
                        onClick={() => removeItem(index)}
                        title="Remove item"
                      >
                        <Trash2 size={15} />
                      </button>
                    )}
                  </div>

                  <div className="po-form-grid">
                    <label>
                      Item Code
                      <input
                        value={item.item_code}
                        onChange={(e) =>
                          updateItem(index, "item_code", e.target.value)
                        }
                        placeholder="ITEM-001"
                      />
                    </label>

                    <label>
                      Description *
                      <input
                        required
                        value={item.description}
                        onChange={(e) =>
                          updateItem(index, "description", e.target.value)
                        }
                        placeholder="Item description"
                      />
                    </label>

                    <label>
                      Unit
                      <input
                        value={item.unit_of_measure}
                        onChange={(e) =>
                          updateItem(index, "unit_of_measure", e.target.value)
                        }
                      />
                    </label>

                    <label>
                      Quantity *
                      <input
                        type="number"
                        min="0.001"
                        step="0.001"
                        required
                        value={item.quantity}
                        onChange={(e) =>
                          updateItem(index, "quantity", e.target.value)
                        }
                      />
                    </label>

                    <label>
                      Unit Price *
                      <input
                        type="number"
                        min="0"
                        step="0.01"
                        required
                        value={item.unit_price}
                        onChange={(e) =>
                          updateItem(index, "unit_price", e.target.value)
                        }
                      />
                    </label>

                    <label>
                      Tax Rate (%)
                      <input
                        type="number"
                        min="0"
                        step="0.01"
                        value={item.tax_rate}
                        onChange={(e) =>
                          updateItem(index, "tax_rate", e.target.value)
                        }
                      />
                    </label>
                  </div>
                </div>
              ))}

              <div className="po-modal-footer">
                <button
                  type="button"
                  className="po-cancel-btn"
                  onClick={() => setShowCreate(false)}
                  disabled={submitting}
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="po-primary-btn"
                  disabled={submitting}
                >
                  {submitting ? "Creating..." : "Create Purchase Order"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {selectedOrder && (
        <div
          className="po-modal-backdrop"
          onClick={() => setSelectedOrder(null)}
        >
          <div
            className="po-modal"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="po-modal-header">
              <div>
                <h2>{selectedOrder.po_number}</h2>
                <p>Purchase order details</p>
              </div>

              <button
                className="po-close-btn"
                onClick={() => setSelectedOrder(null)}
              >
                <X size={20} />
              </button>
            </div>

            <div className="po-detail-grid">
              <div>
                <span>Vendor</span>
                <strong>{getVendorName(selectedOrder)}</strong>
              </div>

              <div>
                <span>Status</span>
                <strong>
                  {String(selectedOrder.status || "").replaceAll("_", " ")}
                </strong>
              </div>

              <div>
                <span>Order Date</span>
                <strong>{selectedOrder.order_date || "—"}</strong>
              </div>

              <div>
                <span>Expected Delivery</span>
                <strong>{selectedOrder.expected_delivery_date || "—"}</strong>
              </div>

              <div>
                <span>Currency</span>
                <strong>{selectedOrder.currency || "INR"}</strong>
              </div>

              <div>
                <span>Total Amount</span>
                <strong>
                  {formatMoney(
                    getOrderTotal(selectedOrder),
                    selectedOrder.currency || "INR"
                  )}
                </strong>
              </div>
            </div>

            <h3 className="po-detail-items-heading">Order Items</h3>

            <div className="po-detail-items">
              {(selectedOrder.items || []).length === 0 ? (
                <p>No line items available.</p>
              ) : (
                <table>
                  <thead>
                    <tr>
                      <th>Item</th>
                      <th>Qty</th>
                      <th>Unit Price</th>
                      <th>Tax %</th>
                    </tr>
                  </thead>

                  <tbody>
                    {selectedOrder.items.map((item, index) => (
                      <tr key={item.id || index}>
                        <td>
                          {item.description || item.item_code || "Item"}
                        </td>
                        <td>{item.quantity}</td>
                        <td>
                          {formatMoney(
                            item.unit_price,
                            selectedOrder.currency || "INR"
                          )}
                        </td>
                        <td>{item.tax_rate}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            {selectedOrder.notes && (
              <div className="po-detail-notes">
                <strong>Notes</strong>
                <p>{selectedOrder.notes}</p>
              </div>
            )}

            <div className="po-modal-footer">
              <button
                className="po-cancel-btn"
                onClick={() => setSelectedOrder(null)}
              >
                Close
              </button>

              {selectedOrder.status === "DRAFT" && (
                <button
                  className="po-primary-btn"
                  onClick={async () => {
                    const order = selectedOrder;
                    setSelectedOrder(null);
                    await issueOrder(order);
                  }}
                >
                  <Send size={15} />
                  Issue Purchase Order
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default PurchaseOrders;
