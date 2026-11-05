
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Upload,
  FileText,
  CheckCircle,
  AlertCircle,
  ArrowLeft,
  Loader,
  RefreshCw,
} from "lucide-react";
import api, { fetchAllPages } from "../../services/api";
import "./InvoiceUpload.css";

const initialForm = {
  vendor: "",
  purchase_order: "",
  invoice_number: "",
  invoice_date: "",
  due_date: "",
  currency: "INR",
  subtotal: "",
  tax_amount: "",
  total_amount: "",
  notes: "",
};

function getList(data) {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.results)) return data.results;
  if (Array.isArray(data?.vendors)) return data.vendors;
  if (Array.isArray(data?.data)) return data.data;
  return [];
}

function getVendorName(vendor) {
  return (
    vendor.legal_name ||
    vendor.name ||
    vendor.vendor_name ||
    vendor.company_name ||
    vendor.supplier_name ||
    vendor.display_name ||
    `Vendor #${vendor.id}`
  );
}

function getVendorCode(vendor) {
  return (
    vendor.vendor_code ||
    vendor.code ||
    vendor.vendor_id ||
    ""
  );
}

function InvoiceUpload() {
  const navigate = useNavigate();

  const [file, setFile] = useState(null);
  const [batchFiles, setBatchFiles] = useState([]);
  const [batchResults, setBatchResults] = useState([]);
  const [batchUploading, setBatchUploading] = useState(false);
  const [document, setDocument] = useState(null);
  const [vendors, setVendors] = useState([]);
  const [purchaseOrders, setPurchaseOrders] = useState([]);
  const [lineItems, setLineItems] = useState([]);
  const [form, setForm] = useState(initialForm);

  const [uploading, setUploading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [loadingVendors, setLoadingVendors] = useState(true);

  const [error, setError] = useState("");
  const [vendorError, setVendorError] = useState("");
  const [success, setSuccess] = useState("");

  const availablePurchaseOrders = purchaseOrders.filter((po) =>
    Number(po.vendor) === Number(form.vendor) &&
    ["ISSUED", "PARTIALLY_RECEIVED", "FULLY_RECEIVED"].includes(po.status)
  );

  // Load vendors from Django API
  const loadVendors = async () => {
    setLoadingVendors(true);
    setVendorError("");

    try {
      const vendorList = (await fetchAllPages("/vendors/", { page_size: 100 })).filter(
        (vendor) => vendor.id != null
      );

      setVendors(vendorList);

      if (vendorList.length === 0) {
        setVendorError(
          "No vendors found. Please create a vendor before creating an invoice."
        );
      }
    } catch (err) {
      console.error(
        "Vendor loading error:",
        err.response?.data || err
      );

      setVendorError(
        err.response?.data?.detail ||
        "Unable to load vendors. Please check the backend API."
      );

      setVendors([]);
    } finally {
      setLoadingVendors(false);
    }
  };

  useEffect(() => {
    let active = true;

    const fetchVendors = async () => {
      setLoadingVendors(true);
      setVendorError("");

      try {
        const vendorList = (await fetchAllPages("/vendors/", { page_size: 100 })).filter(
          (vendor) => vendor.id != null
        );

        if (active) {
          setVendors(vendorList);

          if (vendorList.length === 0) {
            setVendorError(
              "No vendors found. Please create a vendor first."
            );
          }
        }
      } catch (err) {
        console.error(
          "Vendor loading error:",
          err.response?.data || err
        );

        if (active) {
          setVendorError(
            err.response?.data?.detail ||
            "Unable to load vendors. Please refresh."
          );
        }
      } finally {
        if (active) setLoadingVendors(false);
      }
    };

    fetchVendors();

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;
    api.get("/purchase-orders/")
      .then((response) => {
        if (active) setPurchaseOrders(getList(response.data));
      })
      .catch(() => {
        if (active) setVendorError("Purchase orders could not be loaded. You can still create an invoice without a PO.");
      });
    return () => { active = false; };
  }, []);

  const updateField = (event) => {
    const { name, value } = event.target;

    if (name === "vendor") {
      setLineItems([]);
      setForm((previous) => ({ ...previous, vendor: value, purchase_order: "" }));
      return;
    }

    setForm((previous) => ({
      ...previous,
      [name]: value,
    }));
  };

  const selectPurchaseOrder = (event) => {
    const purchaseOrderId = event.target.value;
    const selectedPO = purchaseOrders.find((po) => String(po.id) === purchaseOrderId);
    setForm((previous) => ({
      ...previous,
      purchase_order: purchaseOrderId,
      currency: selectedPO?.currency || previous.currency,
    }));
    const extractedLines = document?.extracted_data?.line_items || [];
    setLineItems((selectedPO?.items || []).map((item, index) => {
      const normalizedDescription = String(item.description || "").toLowerCase().trim();
      const extracted = extractedLines.find((line) =>
        String(line.description || "").toLowerCase().trim() === normalizedDescription
      ) || extractedLines.find((line) => Number(line.line_number) === Number(item.line_number)) || extractedLines[index];
      return {
        line_number: index + 1,
        purchase_order_item: item.id,
        description: extracted?.description || item.description,
        quantity: extracted?.quantity || item.quantity,
        unit_price: extracted?.unit_price || item.unit_price,
        tax_rate: extracted?.tax_rate || item.tax_rate,
      };
    }));
  };

  const updateLineItem = (index, field, value) => {
    setLineItems((items) => items.map((item, itemIndex) =>
      itemIndex === index ? { ...item, [field]: value } : item
    ));
  };

  const selectFile = (event) => {
    const selected = event.target.files?.[0];

    if (!selected) return;

    setError("");
    setSuccess("");
    setDocument(null);

    const allowedTypes = [
      "application/pdf",
      "image/jpeg",
      "image/png",
      "image/tiff",
    ];

    if (!allowedTypes.includes(selected.type)) {
      const extension = selected.name.split(".").pop()?.toLowerCase();
      if (["tif", "tiff"].includes(extension)) {
        setFile(selected);
        return;
      }
      setFile(null);
      setError("Only PDF, JPG, JPEG, PNG and TIFF files are supported.");
      return;
    }

    if (selected.size > 10 * 1024 * 1024) {
      setFile(null);
      setError("File size must not exceed 10 MB.");
      return;
    }

    setFile(selected);
  };

  const selectBatchFiles = (event) => {
    const selectedFiles = Array.from(event.target.files || []);
    const supported = /\.(pdf|jpe?g|png|tiff?)$/i;
    const invalid = selectedFiles.find((item) =>
      !supported.test(item.name) || item.size > 10 * 1024 * 1024
    );
    if (invalid) {
      setError(`${invalid.name} is unsupported or larger than 10 MB.`);
      setBatchFiles([]);
      setBatchResults([]);
      return;
    }
    setError("");
    setBatchFiles(selectedFiles);
    setBatchResults([]);
  };

  const uploadBatch = async () => {
    setBatchUploading(true);
    setBatchResults([]);
    const completed = [];
    for (const batchFile of batchFiles) {
      try {
        const data = new FormData();
        data.append("file", batchFile);
        const response = await api.post("/invoice-documents/", data);
        completed.push({ fileName: batchFile.name, document: response.data });
      } catch (err) {
        completed.push({
          fileName: batchFile.name,
          error: err.response?.data?.detail || "Upload or OCR failed.",
        });
      }
      setBatchResults([...completed]);
    }
    setBatchUploading(false);
  };

  const reviewBatchDocument = (batchResult) => {
    const extracted = batchResult.document.extracted_data || {};
    setDocument(batchResult.document);
    setFile(null);
    setForm((previous) => ({
      ...previous,
      invoice_number: extracted.invoice_number || "",
      invoice_date: extracted.invoice_date || "",
      due_date: extracted.due_date || "",
      currency: extracted.currency || "INR",
      subtotal: extracted.subtotal || "",
      tax_amount: extracted.tax_amount || "",
      total_amount: extracted.total_amount || "",
    }));
    setSuccess(`Loaded ${batchResult.fileName} for invoice review.`);
  };

  // Upload invoice document and process OCR
  const uploadDocument = async () => {
    if (!file) {
      setError("Please select an invoice document first.");
      return;
    }

    setUploading(true);
    setError("");
    setSuccess("");

    try {
      const data = new FormData();
      data.append("file", file);

      const response = await api.post(
        "/invoice-documents/",
        data
      );

      setDocument(response.data);

      if (response.data.processing_status === "COMPLETED") {
        setSuccess(
          "Document uploaded and OCR processing completed."
        );
      } else {
        setSuccess(
          `Document uploaded. Processing status: ${response.data.processing_status}`
        );
      }

      const extracted = response.data.extracted_data || {};

      setForm((previous) => ({
        ...previous,
        invoice_number:
          extracted.invoice_number || previous.invoice_number,
        invoice_date:
          extracted.invoice_date || previous.invoice_date,
        due_date:
          extracted.due_date || previous.due_date,
        currency:
          extracted.currency || previous.currency,
        subtotal:
          extracted.subtotal ?? previous.subtotal,
        tax_amount:
          extracted.tax_amount ?? previous.tax_amount,
        total_amount:
          extracted.total_amount ?? previous.total_amount,
      }));

    } catch (err) {
      console.error(
        "Invoice upload error:",
        err.response?.data || err
      );

      const responseData = err.response?.data;

      let message = "Document upload failed. Please try again.";

      if (typeof responseData === "string") {
        message = responseData;
      } else if (responseData) {
        message = Object.entries(responseData)
          .map(([key, value]) => {
            const details = Array.isArray(value)
              ? value.join(", ")
              : typeof value === "object"
                ? JSON.stringify(value)
                : value;

            return `${key}: ${details}`;
          })
          .join(" | ");
      } else if (err.message) {
        message = err.message;
      }

      setError(message);
    } finally {
      setUploading(false);
    }
  };

  // Create invoice from reviewed OCR details
  const createInvoice = async (event) => {
    event.preventDefault();

    if (!document?.id) {
      setError(
        "Upload and process a document before creating an invoice."
      );
      return;
    }

    if (document.processing_status !== "COMPLETED") {
      setError(
        "OCR processing is not complete. Please check document status."
      );
      return;
    }

    if (!form.vendor) {
      setError("Please select a vendor.");
      return;
    }

    if (form.purchase_order && !lineItems.length) {
      setError("The selected purchase order has no invoice lines. Add or select at least one line item.");
      return;
    }

    if (lineItems.some((item) => !Number(item.quantity) || Number(item.quantity) <= 0)) {
      setError("Each selected PO line must have a quantity greater than zero.");
      return;
    }

    setCreating(true);
    setError("");
    setSuccess("");

    const payload = {
      vendor: Number(form.vendor),
      invoice_number: form.invoice_number.trim(),
      invoice_date: form.invoice_date,
      due_date: form.due_date,
      currency: form.currency,
      subtotal: Number(form.subtotal),
      tax_amount: Number(form.tax_amount),
      total_amount: Number(form.total_amount),
      notes: form.notes,
    };
    if (form.purchase_order) {
      payload.purchase_order = Number(form.purchase_order);
      payload.items = lineItems.map((item) => ({
        line_number: item.line_number,
        purchase_order_item: Number(item.purchase_order_item),
        description: item.description,
        quantity: Number(item.quantity),
        unit_price: Number(item.unit_price),
        tax_rate: Number(item.tax_rate),
      }));
    }

    try {
      await api.post(
        `/invoice-documents/${document.id}/create-invoice/`,
        payload
      );

      setSuccess("Invoice created successfully.");

      setTimeout(() => {
        navigate("/invoices");
      }, 1000);
    } catch (err) {
      console.error(
        "Invoice creation error:",
        err.response?.data || err
      );

      const data = err.response?.data;

      const message =
        data?.detail ||
        data?.message ||
        Object.entries(data || {})
          .map(([key, value]) =>
            `${key}: ${
              Array.isArray(value)
                ? value.join(", ")
                : typeof value === "object"
                  ? JSON.stringify(value)
                  : value
            }`
          )
          .join(" | ");

      setError(
        message ||
        "Unable to create invoice. Please check the details."
      );
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="invoice-upload-page">

      <div className="upload-page-header">
        <button
          className="back-button"
          onClick={() => navigate("/invoices")}
          type="button"
        >
          <ArrowLeft size={18} />
          Back to Invoices
        </button>

        <h1>Upload Invoice</h1>

        <p>
          Upload a supplier invoice and extract its details automatically.
        </p>
      </div>

      {error && (
        <div className="upload-alert error-alert">
          <AlertCircle size={18} />
          {error}
        </div>
      )}

      {success && (
        <div className="upload-alert success-alert">
          <CheckCircle size={18} />
          {success}
        </div>
      )}

      {/* Invoice document upload */}
      <section className="upload-panel">
        <h2>
          <Upload size={20} />
          Invoice Document
        </h2>

        <label className="file-drop-area">
          <FileText size={38} />

          <strong>
            {file
              ? file.name
              : "Choose an invoice document"}
          </strong>

          <span>PDF, JPG, PNG or TIFF · Maximum 10 MB</span>

          <input
            type="file"
            accept=".pdf,.jpg,.jpeg,.png,.tif,.tiff"
            onChange={selectFile}
          />
        </label>

        {file && (
          <div className="selected-file">
            <FileText size={18} />
            <span>{file.name}</span>
            <span>
              {(file.size / 1024 / 1024).toFixed(2)} MB
            </span>
          </div>
        )}

        <button
          className="primary-button"
          type="button"
          onClick={uploadDocument}
          disabled={!file || uploading}
        >
          {uploading ? (
            <>
              <Loader size={17} className="spin" />
              Uploading and processing...
            </>
          ) : (
            <>
              <Upload size={17} />
              Upload and Extract Details
            </>
          )}
        </button>

        {document && (
          <div className="ocr-result">
            <CheckCircle size={18} />

            <div>
              <strong>Document uploaded</strong>

              <p>
                Processing status: {document.processing_status}
              </p>

              {document.extracted_data?.ocr_confidence_label && (
                <p className={`ocr-confidence ${document.extracted_data.ocr_confidence === null ? "unknown" : document.extracted_data.ocr_confidence < 65 ? "low" : document.extracted_data.ocr_confidence < 85 ? "medium" : "high"}`}>
                  {document.extracted_data.ocr_confidence != null ? `OCR confidence: ${document.extracted_data.ocr_confidence}%` : "OCR confidence not measured"} ({document.extracted_data.ocr_confidence_label}). Verify every extracted value; fields remain editable.
                </p>
              )}

              {document.extracted_data?.validation?.warnings?.map((warning) => (
                <p className="field-help" key={warning}>{warning}</p>
              ))}

              {document.error_message && (
                <p>{document.error_message}</p>
              )}
            </div>
          </div>
        )}

        {document?.extracted_text && (
          <details className="extracted-text">
            <summary>View OCR extracted text</summary>
            <pre>{document.extracted_text}</pre>
          </details>
        )}
      </section>

      <section className="upload-panel">
        <h2><Upload size={20} /> Bulk invoice upload</h2>
        <p>Select several files. Each is uploaded and OCR processed, then can be opened in the invoice review form.</p>
        <label className="file-drop-area">
          <FileText size={32} />
          <strong>{batchFiles.length ? `${batchFiles.length} files selected` : "Choose multiple invoice documents"}</strong>
          <span>PDF, JPG, PNG or TIFF · Maximum 10 MB each</span>
          <input type="file" accept=".pdf,.jpg,.jpeg,.png,.tif,.tiff" multiple onChange={selectBatchFiles} />
        </label>
        {batchFiles.length > 0 && <ul className="batch-file-list">{batchFiles.map((item) => <li key={`${item.name}-${item.lastModified}`}>{item.name} · {(item.size / 1024 / 1024).toFixed(2)} MB</li>)}</ul>}
        <button className="primary-button" type="button" onClick={uploadBatch} disabled={!batchFiles.length || batchUploading}>
          {batchUploading ? <><Loader size={17} className="spin" /> Processing {batchResults.length}/{batchFiles.length}…</> : <><Upload size={17} /> Upload and OCR selected files</>}
        </button>
        {batchResults.length > 0 && <div className="batch-results"><h3>Batch results</h3>{batchResults.map((result) => <div className="batch-result-row" key={result.fileName}><span>{result.fileName}</span>{result.error ? <span className="batch-error">{result.error}</span> : <><span>{result.document.processing_status}</span><button type="button" onClick={() => reviewBatchDocument(result)}>Review invoice</button></>}</div>)}</div>}
      </section>

      {/* Invoice details form */}
      <section className="upload-panel">
        <h2>Invoice Details</h2>

        <p className="panel-description">
          Review and correct the extracted information before creating the invoice.
        </p>

        <form onSubmit={createInvoice}>
          <div className="invoice-form-grid">

            {/* Vendor selection */}
            <div className="form-field full-field">
              <label>Vendor *</label>

              <div className="vendor-select-row">
                <select
                  name="vendor"
                  value={form.vendor}
                  onChange={updateField}
                  required
                  disabled={loadingVendors || vendors.length === 0}
                >
                  <option value="">
                    {loadingVendors
                      ? "Loading vendors..."
                      : vendors.length === 0
                        ? "No vendors available"
                        : "Select vendor"}
                  </option>

                  {vendors.map((vendor) => (
                    <option
                      key={vendor.id}
                      value={vendor.id}
                    >
                      {getVendorName(vendor)}
                      {getVendorCode(vendor)
                        ? ` (${getVendorCode(vendor)})`
                        : ""}
                    </option>
                  ))}
                </select>

                <button
                  type="button"
                  className="back-button"
                  onClick={loadVendors}
                  disabled={loadingVendors}
                  title="Refresh vendors"
                >
                  <RefreshCw size={16} />
                </button>
              </div>

              {vendorError && (
                <p className="field-error">
                  {vendorError}
                </p>
              )}
            </div>

            <div className="form-field full-field">
              <label>Purchase Order (optional, required for matching)</label>
              <select
                name="purchase_order"
                value={form.purchase_order}
                onChange={selectPurchaseOrder}
                disabled={!form.vendor}
              >
                <option value="">No purchase order selected</option>
                {availablePurchaseOrders.map((po) => (
                  <option key={po.id} value={po.id}>
                    {po.po_number} · {po.status} · {po.currency}
                  </option>
                ))}
              </select>
              {form.vendor && !availablePurchaseOrders.length && (
                <p className="field-help">No issued or received purchase orders are available for this vendor.</p>
              )}
            </div>

            {form.purchase_order && <div className="full-field invoice-line-editor">
              <h3>Invoice line items</h3>
              <p>Review quantities, prices, and tax against the purchase order before matching.</p>
              {lineItems.map((item, index) => <div className="invoice-line-row" key={item.purchase_order_item}>
                <label>Description<input value={item.description} onChange={(event) => updateLineItem(index, "description", event.target.value)} required /></label>
                <label>Quantity<input type="number" min="0.001" step="0.001" value={item.quantity} onChange={(event) => updateLineItem(index, "quantity", event.target.value)} required /></label>
                <label>Unit price<input type="number" min="0" step="0.01" value={item.unit_price} onChange={(event) => updateLineItem(index, "unit_price", event.target.value)} required /></label>
                <label>Tax %<input type="number" min="0" max="100" step="0.01" value={item.tax_rate} onChange={(event) => updateLineItem(index, "tax_rate", event.target.value)} required /></label>
                <button type="button" className="remove-line-button" onClick={() => setLineItems((items) => items.filter((_, itemIndex) => itemIndex !== index))}>Remove</button>
              </div>)}
              {!lineItems.length && <p className="field-error">Add at least one line from the purchase order.</p>}
            </div>}

            <div className="form-field">
              <label>Invoice Number *</label>

              <input
                name="invoice_number"
                value={form.invoice_number}
                onChange={updateField}
                required
              />
            </div>

            <div className="form-field">
              <label>Currency *</label>

              <select
                name="currency"
                value={form.currency}
                onChange={updateField}
                required
              >
                <option value="INR">INR</option>
                <option value="USD">USD</option>
                <option value="EUR">EUR</option>
                <option value="GBP">GBP</option>
              </select>
            </div>

            <div className="form-field">
              <label>Invoice Date *</label>

              <input
                type="date"
                name="invoice_date"
                value={form.invoice_date}
                onChange={updateField}
                required
              />
            </div>

            <div className="form-field">
              <label>Due Date *</label>

              <input
                type="date"
                name="due_date"
                value={form.due_date}
                onChange={updateField}
                required
              />
            </div>

            <div className="form-field">
              <label>Subtotal *</label>

              <input
                type="number"
                name="subtotal"
                min="0"
                step="0.01"
                value={form.subtotal}
                onChange={updateField}
                required
              />
            </div>

            <div className="form-field">
              <label>Tax Amount *</label>

              <input
                type="number"
                name="tax_amount"
                min="0"
                step="0.01"
                value={form.tax_amount}
                onChange={updateField}
                required
              />
            </div>

            <div className="form-field">
              <label>Total Amount *</label>

              <input
                type="number"
                name="total_amount"
                min="0"
                step="0.01"
                value={form.total_amount}
                onChange={updateField}
                required
              />
            </div>

            <div className="form-field full-field">
              <label>Notes</label>

              <textarea
                name="notes"
                rows="3"
                value={form.notes}
                onChange={updateField}
                placeholder="Additional invoice notes..."
              />
            </div>

          </div>

          <button
            className="primary-button create-invoice-button"
            type="submit"
            disabled={
              !document ||
              creating ||
              loadingVendors ||
              vendors.length === 0
            }
          >
            {creating
              ? "Creating Invoice..."
              : "Create Invoice"}
          </button>
        </form>
      </section>
    </div>
  );
}

export default InvoiceUpload;
