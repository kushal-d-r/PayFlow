
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";

import AuthProvider from "./context/AuthProvider";
import { useAuth } from "./context/useAuth";

import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Invoices from "./pages/Invoices";
import InvoiceUpload from "./pages/invoices/InvoiceUpload";
import PurchaseOrders from "./pages/PurchaseOrders";
import GoodsReceipts from "./pages/GoodsReceipts";
import Vendors from "./pages/Vendors";
import Approvals from "./pages/Approvals";
import Payments from "./pages/Payments";
import Reports from "./pages/Reports";

function ProtectedRoute({ children }) {
  const { isAuthenticated } = useAuth();

  return isAuthenticated
    ? children
    : <Navigate to="/" replace />;
}

function AppRoutes() {
  const { isAuthenticated } = useAuth();

  return (
    <Routes>
      {/* Login */}
      <Route
        path="/"
        element={
          isAuthenticated
            ? <Navigate to="/dashboard" replace />
            : <Login />
        }
      />

      {/* Dashboard */}
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        }
      />

      {/* Invoices */}
      <Route
        path="/invoices"
        element={
          <ProtectedRoute>
            <Invoices />
          </ProtectedRoute>
        }
      />

      {/* Upload Invoice */}
      <Route
        path="/invoices/upload"
        element={
          <ProtectedRoute>
            <InvoiceUpload />
          </ProtectedRoute>
        }
      />





      <Route
        path="/purchase-orders"
        element={
          <ProtectedRoute>
            <PurchaseOrders />
          </ProtectedRoute>
        }
      />


      <Route
        path="/goods-receipts"
        element={
          <ProtectedRoute>
            <GoodsReceipts />
          </ProtectedRoute>
        }
      />

        <Route
            path="/vendors"
            element={
              <ProtectedRoute>
                <Vendors />
              </ProtectedRoute>
            }
          />


      <Route
        path="/approvals"
        element={
          <ProtectedRoute>
            <Approvals />
          </ProtectedRoute>
        }
      />

      <Route
        path="/payments"
        element={<ProtectedRoute><Payments /></ProtectedRoute>}
      />

      <Route
        path="/reports"
        element={<ProtectedRoute><Reports /></ProtectedRoute>}
      />




      {/* Unknown routes */}
      <Route
        path="*"
        element={<Navigate to="/" replace />}
      />
    </Routes>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
