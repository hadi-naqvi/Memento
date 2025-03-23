"use client";

import React, { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { useRouter } from "next/navigation";

interface User {
  id: string;
  email?: string;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string, rememberMe: boolean) => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<string | null>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    // Check for existing session on initial load
    const checkSession = async () => {
      const token = localStorage.getItem("access_token") || sessionStorage.getItem("access_token");
      
      if (!token) {
        setLoading(false);
        return;
      }

      try {
        // Check token expiry
        const expiry = localStorage.getItem("token_expiry") || sessionStorage.getItem("token_expiry");
        const now = new Date().getTime();
        
        if (expiry && parseInt(expiry) <= now) {
          // Token expired, try to refresh
          const newToken = await refreshToken();
          if (!newToken) {
            throw new Error("Failed to refresh token");
          }
        }

        // Get user data
        const userId = localStorage.getItem("user_id") || sessionStorage.getItem("user_id");
        setUser({ id: userId as string });
      } catch (error) {
        console.error("Session verification error:", error);
        await logout();
      } finally {
        setLoading(false);
      }
    };

    checkSession();
  }, []);

  const login = async (email: string, password: string, rememberMe: boolean) => {
    setLoading(true);

    try {
      const response = await fetch("http://localhost:5000/api/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Login failed");
      }

      // Store tokens in localStorage or sessionStorage based on rememberMe
      const storage = rememberMe ? localStorage : sessionStorage;
      storage.setItem("access_token", data.access_token);
      storage.setItem("refresh_token", data.refresh_token);
      storage.setItem("firebase_token", data.firebase_token);
      storage.setItem("user_id", data.user_id);
      
      // Set token expiry time for client-side refresh handling
      const expiryTime = new Date().getTime() + (data.expires_in * 1000);
      storage.setItem("token_expiry", expiryTime.toString());

      setUser({ id: data.user_id, email });
      router.push("/dashboard");
    } finally {
      setLoading(false);
    }
  };

  const refreshToken = async (): Promise<string | null> => {
    const refresh = localStorage.getItem("refresh_token") || sessionStorage.getItem("refresh_token");
    
    if (!refresh) {
      return null;
    }

    try {
      const response = await fetch("http://localhost:5000/api/auth/refresh", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ refresh_token: refresh }),
      });

      if (!response.ok) {
        throw new Error("Failed to refresh token");
      }

      const data = await response.json();
      
      // Update tokens in storage
      const storage = localStorage.getItem("refresh_token") ? localStorage : sessionStorage;
      storage.setItem("access_token", data.access_token);
      storage.setItem("refresh_token", data.refresh_token);
      storage.setItem("firebase_token", data.firebase_token);
      
      // Update expiry time
      const expiryTime = new Date().getTime() + (data.expires_in * 1000);
      storage.setItem("token_expiry", expiryTime.toString());
      
      return data.access_token;
    } catch (error) {
      console.error("Token refresh failed:", error);
      return null;
    }
  };

  const logout = async () => {
    try {
      const token = localStorage.getItem("access_token") || sessionStorage.getItem("access_token");
      
      if (token) {
        await fetch("http://localhost:5000/api/auth/logout", {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
      }
    } catch (error) {
      console.error("Logout error:", error);
    } finally {
      // Clear all storage
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      localStorage.removeItem("firebase_token");
      localStorage.removeItem("user_id");
      localStorage.removeItem("token_expiry");
      
      sessionStorage.removeItem("access_token");
      sessionStorage.removeItem("refresh_token");
      sessionStorage.removeItem("firebase_token");
      sessionStorage.removeItem("user_id");
      sessionStorage.removeItem("token_expiry");
      
      setUser(null);
      router.push("/login");
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, refreshToken }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}