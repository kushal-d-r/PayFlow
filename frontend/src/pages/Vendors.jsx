
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Plus,
  Search,
  RefreshCw,
  Eye,
  Edit,
  X,
  Building2,
  Users,
  CheckCircle,
  AlertCircle,
  Mail,
  Phone,
  MapPin,
} from "lucide-react";

import api from "../services/api";
import "./Vendors.css";

function getList(data) {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.results)) return data.results;
  if (Array.isArray(data?.data)) return data.data;
  return [];
}

function Vendors() {
  const [vendors, setVendors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");

  const [showForm, setShowForm] = useState(false);
  const [editingVendor, setEditingVendor] = useState(null);
  const [selectedVendor, setSelectedVendor] = useState(null);

  const emptyForm = {
    vendor_code: "",
    legal_name: "",
    display_name: "",
    gstin: "",
    email: "",
    phone: "",
    address_line1: "",
    address_line2: "",
    city: "",
    state: "",
    postal_code: "",
    country: "India",
    payment_terms: 30,
    currency: "INR",
    is_active: true,
  };

  const [form, setForm] = useState(emptyForm);

  const loadVendors = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const response = await api.get("/vendors/");
      setVendors(getList(response.data));
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          err.response?.data?.message ||
          "Unable to load vendors."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial fetch is asynchronous and guarded against updates after unmount.
  useEffect(() => {
    let cancelled = false;

    async function fetchVendors() {
      try {
        const response = await api.get("/vendors/");

        if (!cancelled) {
          setVendors(getList(response.data));
          setError("");
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err.response?.data?.detail ||
              err.response?.data?.message ||
              "Unable to load vendors."
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    fetchVendors();

    return () => {
      cancelled = true;
    };
  }, []);

  const filteredVendors = useMemo(() => {
    return vendors.filter((vendor) => {
      const searchText = search.toLowerCase();

      const matchesSearch = [
        vendor.vendor_code,
        vendor.legal_name,
        vendor.display_name,
        vendor.email,
        vendor.gstin,
        vendor.phone,
      ].some((value) =>
        String(value || "").toLowerCase().includes(searchText)
      );

      const active = vendor.is_active !== false;
      const matchesStatus =
        statusFilter === "ALL" ||
        (statusFilter === "ACTIVE" && active) ||
        (statusFilter === "INACTIVE" && !active);

      return matchesSearch && matchesStatus;
    });
  }, [vendors, search, statusFilter]);

  const stats = useMemo(() => ({
    total: vendors.length,
    active: vendors.filter((v) => v.is_active !== false).length,
    inactive: vendors.filter((v) => v.is_active === false).length,
  }), [vendors]);

  const updateForm = (field, value) => {
    setForm((previous) => ({
      ...previous,
      [field]: value,
    }));
  };

  const openCreateForm = () => {
    setEditingVendor(null);
    setForm(emptyForm);
    setError("");
    setNotice("");
    setShowForm(true);
  };

  const openEditForm = (vendor) => {
    setEditingVendor(vendor);

    setForm({
      ...emptyForm,
      ...vendor,
      payment_terms: vendor.payment_terms ?? 30,
      country: vendor.country || "India",
      currency: vendor.currency || "INR",
      is_active: vendor.is_active !== false,
    });

    setError("");
    setNotice("");
    setShowForm(true);
  };

  const saveVendor = async (event) => {
    event.preventDefault();
    setError("");
    setNotice("");

    if (!form.vendor_code.trim()) {
      setError("Vendor code is required.");
      return;
    }

    if (!form.legal_name.trim()) {
      setError("Legal name is required.");
      return;
    }

    if (form.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
      setError("Enter a valid email address.");
      return;
    }

    const payload = {
      ...form,
      vendor_code: form.vendor_code.trim(),
      legal_name: form.legal_name.trim(),
      display_name: form.display_name.trim(),
      email: form.email.trim(),
      phone: form.phone.trim(),
      gstin: form.gstin.trim().toUpperCase(),
      payment_terms: Number(form.payment_terms),
    };

    setSubmitting(true);

    try {
      if (editingVendor) {
        await api.patch(`/vendors/${editingVendor.id}/`, payload);
        setNotice("Vendor updated successfully.");
      } else {
        await api.post("/vendors/", payload);
        setNotice("Vendor created successfully.");
      }

      setShowForm(false);
      setEditingVendor(null);
      setForm(emptyForm);
      await loadVendors();
    } catch (err) {
      const data = err.response?.data;

      setError(
        data?.detail ||
          data?.message ||
          (typeof data === "object"
            ? JSON.stringify(data)
            : "Unable to save vendor.")
      );
    } finally {
      setSubmitting(false);
    }
  };

  const toggleVendorStatus = async (vendor) => {
    const newStatus = !vendor.is_active;

    const confirmed = window.confirm(
      `Are you sure you want to ${
        newStatus ? "activate" : "deactivate"
      } ${vendor.display_name || vendor.legal_name}?`
    );

    if (!confirmed) return;

    setError("");
    setNotice("");

    try {
      await api.patch(`/vendors/${vendor.id}/`, {
        is_active: newStatus,
      });

      setNotice(
        `Vendor ${newStatus ? "activated" : "deactivated"} successfully.`
      );

      await loadVendors();

      if (selectedVendor?.id === vendor.id) {
        setSelectedVendor((previous) =>
          previous ? { ...previous, is_active: newStatus } : previous
        );
      }
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          err.response?.data?.message ||
          "Unable to update vendor status."
      );
    }
  };

  const viewVendor = async (vendor) => {
    setError("");

    try {
      const response = await api.get(`/vendors/${vendor.id}/`);
      setSelectedVendor(response.data);
    } catch {
      // Use the list record if the detail endpoint is unavailable.
      setSelectedVendor(vendor);
    }
  };

  const getVendorName = (vendor) =>
    vendor.display_name || vendor.legal_name || vendor.vendor_code || "Vendor";

  return (
    <div className="vendors-page">
      <div className="vendors-header">
        <div>
          <h1>Vendor Management</h1>
          <p>Manage vendor information and payment details.</p>
        </div>

        <div className="vendors-header-actions">
          <button
            className="vendors-refresh-btn"
            onClick={loadVendors}
            disabled={loading}
          >
            <RefreshCw size={16} />
            Refresh
          </button>

          <button className="vendors-primary-btn" onClick={openCreateForm}>
            <Plus size={17} />
            Add Vendor
          </button>
        </div>
      </div>

      {error && (
        <div className="vendors-message vendors-error">
          <AlertCircle size={17} />
          <span>{error}</span>
          <button onClick={() => setError("")}>
            <X size={16} />
          </button>
        </div>
      )}

      {notice && (
        <div className="vendors-message vendors-success">
          <CheckCircle size={17} />
          <span>{notice}</span>
          <button onClick={() => setNotice("")}>
            <X size={16} />
          </button>
        </div>
      )}

      <div className="vendors-stats">
        <div className="vendors-stat-card">
          <div className="vendors-stat-icon blue">
            <Building2 size={22} />
          </div>
          <div>
            <span>Total Vendors</span>
            <strong>{stats.total}</strong>
          </div>
        </div>

        <div className="vendors-stat-card">
          <div className="vendors-stat-icon green">
            <CheckCircle size={22} />
          </div>
          <div>
            <span>Active Vendors</span>
            <strong>{stats.active}</strong>
          </div>
        </div>

        <div className="vendors-stat-card">
          <div className="vendors-stat-icon orange">
            <Users size={22} />
          </div>
          <div>
            <span>Inactive Vendors</span>
            <strong>{stats.inactive}</strong>
          </div>
        </div>
      </div>

      <div className="vendors-toolbar">
        <div className="vendors-search">
          <Search size={18} />
          <input
            type="text"
            placeholder="Search vendor name, code, GSTIN or email..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="ALL">All vendors</option>
          <option value="ACTIVE">Active</option>
          <option value="INACTIVE">Inactive</option>
        </select>
      </div>

      <div className="vendors-table-container">
        <table className="vendors-table">
          <thead>
            <tr>
              <th>Vendor</th>
              <th>Vendor Code</th>
              <th>GSTIN</th>
              <th>Contact</th>
              <th>Payment Terms</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>

          <tbody>
            {loading ? (
              <tr>
                <td colSpan="7" className="vendors-empty">
                  Loading vendors...
                </td>
              </tr>
            ) : filteredVendors.length === 0 ? (
              <tr>
                <td colSpan="7" className="vendors-empty">
                  No vendors found.
                </td>
              </tr>
            ) : (
              filteredVendors.map((vendor) => (
                <tr key={vendor.id}>
                  <td>
                    <div className="vendor-name-cell">
                      <div className="vendor-avatar">
                        {getVendorName(vendor).charAt(0).toUpperCase()}
                      </div>

                      <div>
                        <strong>{getVendorName(vendor)}</strong>
                        <small>{vendor.email || "No email provided"}</small>
                      </div>
                    </div>
                  </td>

                  <td>{vendor.vendor_code || "—"}</td>
                  <td>{vendor.gstin || "—"}</td>

                  <td>{vendor.phone || "—"}</td>

                  <td>
                    {vendor.payment_terms ?? 30} days
                  </td>

                  <td>
                    <span
                      className={`vendor-status ${
                        vendor.is_active === false ? "inactive" : "active"
                      }`}
                    >
                      {vendor.is_active === false ? "Inactive" : "Active"}
                    </span>
                  </td>

                  <td>
                    <div className="vendors-actions">
                      <button
                        className="vendors-icon-btn"
                        title="View vendor"
                        onClick={() => viewVendor(vendor)}
                      >
                        <Eye size={17} />
                      </button>

                      <button
                        className="vendors-icon-btn"
                        title="Edit vendor"
                        onClick={() => openEditForm(vendor)}
                      >
                        <Edit size={16} />
                      </button>

                      <button
                        className={`vendor-toggle-btn ${
                          vendor.is_active === false ? "activate" : "deactivate"
                        }`}
                        onClick={() => toggleVendorStatus(vendor)}
                      >
                        {vendor.is_active === false ? "Activate" : "Deactivate"}
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {showForm && (
        <div
          className="vendors-modal-backdrop"
          onClick={() => !submitting && setShowForm(false)}
        >
          <div
            className="vendors-modal vendors-form-modal"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="vendors-modal-header">
              <div>
                <h2>{editingVendor ? "Edit Vendor" : "Add New Vendor"}</h2>
                <p>Enter vendor details below.</p>
              </div>

              <button
                className="vendors-close-btn"
                onClick={() => setShowForm(false)}
                disabled={submitting}
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={saveVendor}>
              <h3 className="vendors-section-heading">Basic Information</h3>

              <div className="vendors-form-grid">
                <label>
                  Vendor Code *
                  <input
                    required
                    value={form.vendor_code}
                    onChange={(e) =>
                      updateForm("vendor_code", e.target.value)
                    }
                    placeholder="VEN-001"
                  />
                </label>

                <label>
                  Legal Name *
                  <input
                    required
                    value={form.legal_name}
                    onChange={(e) =>
                      updateForm("legal_name", e.target.value)
                    }
                    placeholder="Company legal name"
                  />
                </label>

                <label>
                  Display Name
                  <input
                    value={form.display_name}
                    onChange={(e) =>
                      updateForm("display_name", e.target.value)
                    }
                    placeholder="Vendor display name"
                  />
                </label>

                <label>
                  GSTIN
                  <input
                    value={form.gstin}
                    onChange={(e) => updateForm("gstin", e.target.value)}
                    placeholder="29ABCDE1234F1Z5"
                    maxLength={15}
                  />
                </label>
              </div>

              <h3 className="vendors-section-heading">Contact Information</h3>

              <div className="vendors-form-grid">
                <label>
                  Email
                  <input
                    type="email"
                    value={form.email}
                    onChange={(e) => updateForm("email", e.target.value)}
                    placeholder="vendor@example.com"
                  />
                </label>

                <label>
                  Phone
                  <input
                    type="tel"
                    value={form.phone}
                    onChange={(e) => updateForm("phone", e.target.value)}
                    placeholder="+91 9876543210"
                  />
                </label>

                <label>
                  Address Line 1
                  <input
                    value={form.address_line1}
                    onChange={(e) =>
                      updateForm("address_line1", e.target.value)
                    }
                  />
                </label>

                <label>
                  Address Line 2
                  <input
                    value={form.address_line2}
                    onChange={(e) =>
                      updateForm("address_line2", e.target.value)
                    }
                  />
                </label>

                <label>
                  City
                  <input
                    value={form.city}
                    onChange={(e) => updateForm("city", e.target.value)}
                  />
                </label>

                <label>
                  State
                  <input
                    value={form.state}
                    onChange={(e) => updateForm("state", e.target.value)}
                  />
                </label>

                <label>
                  Postal Code
                  <input
                    value={form.postal_code}
                    onChange={(e) =>
                      updateForm("postal_code", e.target.value)
                    }
                  />
                </label>

                <label>
                  Country
                  <input
                    value={form.country}
                    onChange={(e) => updateForm("country", e.target.value)}
                  />
                </label>
              </div>

              <h3 className="vendors-section-heading">Payment Information</h3>

              <div className="vendors-form-grid">
                <label>
                  Payment Terms (Days)
                  <input
                    type="number"
                    min="0"
                    value={form.payment_terms}
                    onChange={(e) =>
                      updateForm("payment_terms", e.target.value)
                    }
                  />
                </label>

                <label>
                  Currency
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

                <label className="vendors-checkbox-label">
                  <input
                    type="checkbox"
                    checked={form.is_active}
                    onChange={(e) =>
                      updateForm("is_active", e.target.checked)
                    }
                  />
                  Vendor is active
                </label>
              </div>

              <div className="vendors-modal-footer">
                <button
                  type="button"
                  className="vendors-cancel-btn"
                  onClick={() => setShowForm(false)}
                  disabled={submitting}
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="vendors-primary-btn"
                  disabled={submitting}
                >
                  {submitting
                    ? "Saving..."
                    : editingVendor
                      ? "Save Changes"
                      : "Create Vendor"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {selectedVendor && (
        <div
          className="vendors-modal-backdrop"
          onClick={() => setSelectedVendor(null)}
        >
          <div
            className="vendors-modal"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="vendors-modal-header">
              <div>
                <h2>{getVendorName(selectedVendor)}</h2>
                <p>Vendor details</p>
              </div>

              <button
                className="vendors-close-btn"
                onClick={() => setSelectedVendor(null)}
              >
                <X size={20} />
              </button>
            </div>

            <div className="vendor-detail-content">
              <div className="vendor-detail-status">
                <span
                  className={`vendor-status ${
                    selectedVendor.is_active === false
                      ? "inactive"
                      : "active"
                  }`}
                >
                  {selectedVendor.is_active === false ? "Inactive" : "Active"}
                </span>
              </div>

              <div className="vendor-detail-grid">
                <div>
                  <span>Vendor Code</span>
                  <strong>{selectedVendor.vendor_code || "—"}</strong>
                </div>

                <div>
                  <span>Legal Name</span>
                  <strong>{selectedVendor.legal_name || "—"}</strong>
                </div>

                <div>
                  <span>GSTIN</span>
                  <strong>{selectedVendor.gstin || "—"}</strong>
                </div>

                <div>
                  <span>Currency</span>
                  <strong>{selectedVendor.currency || "INR"}</strong>
                </div>

                <div>
                  <span>Payment Terms</span>
                  <strong>{selectedVendor.payment_terms ?? 30} days</strong>
                </div>

                <div>
                  <span>Email</span>
                  <strong>
                    <Mail size={14} />
                    {selectedVendor.email || "—"}
                  </strong>
                </div>

                <div>
                  <span>Phone</span>
                  <strong>
                    <Phone size={14} />
                    {selectedVendor.phone || "—"}
                  </strong>
                </div>

                <div>
                  <span>Address</span>
                  <strong>
                    <MapPin size={14} />
                    {[
                      selectedVendor.address_line1,
                      selectedVendor.address_line2,
                      selectedVendor.city,
                      selectedVendor.state,
                      selectedVendor.postal_code,
                      selectedVendor.country,
                    ]
                      .filter(Boolean)
                      .join(", ") || "—"}
                  </strong>
                </div>
              </div>
            </div>

            <div className="vendors-modal-footer">
              <button
                className="vendors-cancel-btn"
                onClick={() => setSelectedVendor(null)}
              >
                Close
              </button>

              <button
                className="vendors-primary-btn"
                onClick={() => {
                  const vendor = selectedVendor;
                  setSelectedVendor(null);
                  openEditForm(vendor);
                }}
              >
                <Edit size={15} />
                Edit Vendor
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Vendors;
