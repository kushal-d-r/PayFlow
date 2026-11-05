import { useEffect, useState } from "react";
import AuthContext from "./AuthContext";
import api from "../services/api";

function AuthProvider({ children }) {
  const [accessToken, setAccessToken] = useState(() =>
    localStorage.getItem("access_token")
  );

  useEffect(() => {
    const handleAuthLogout = () => setAccessToken(null);
    const handleStorage = (event) => {
      if (event.key === "access_token") setAccessToken(event.newValue);
    };

    window.addEventListener("auth:logout", handleAuthLogout);
    window.addEventListener("storage", handleStorage);
    return () => {
      window.removeEventListener("auth:logout", handleAuthLogout);
      window.removeEventListener("storage", handleStorage);
    };
  }, []);

  const login = async (username, password) => {
    const response = await api.post("/token/", {
      username,
      password,
    });

    const { access, refresh } = response.data;

    localStorage.setItem("access_token", access);
    localStorage.setItem("refresh_token", refresh);

    setAccessToken(access);

    return response.data;
  };

  const logout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");

    setAccessToken(null);
  };

  const value = {
    accessToken,
    isAuthenticated: Boolean(accessToken),
    login,
    logout,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export default AuthProvider;
