import { useAuth } from "../context/AuthContext";

// Base API URL
const API_BASE_URL = "http://localhost:5001/api";

// Helper function to get the stored token
const getToken = () => {
  return localStorage.getItem("access_token") || sessionStorage.getItem("access_token");
};

// Main fetch function that handles authentication
export const fetchWithAuth = async (
  endpoint: string,
  options: RequestInit = {}
): Promise<Response> => {
  const token = getToken();
  
  // Add authorization header if token exists
  const headers = {
    ...options.headers,
    "Content-Type": "application/json",
    ...(token ? { "Authorization": `Bearer ${token}` } : {})
  };
  
  try {
    // Make the request
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers
    });
    
    // If unauthorized, attempt to refresh token
    if (response.status === 401) {
      // Since we can't directly call useAuth() here (it's a React hook),
      // we'll need to handle refresh in the component
      throw new Error("UNAUTHORIZED");
    }
    
    return response;
  } catch (error) {
    console.error("API request failed:", error);
    throw error;
  }
};

// Hook for components to use authenticated API calls
export const useApi = () => {
  const { refreshToken, logout } = useAuth();
  
  // GET request with authentication
  const get = async (endpoint: string) => {
    try {
      const response = await fetchWithAuth(endpoint, { method: "GET" });
      return await response.json();
    } catch (error) {
      if (error instanceof Error && error.message === "UNAUTHORIZED") {
        try {
          // Attempt to refresh the token
          const newToken = await refreshToken();
          if (newToken) {
            // Retry the request with new token
            const retryResponse = await fetchWithAuth(endpoint, { method: "GET" });
            return await retryResponse.json();
          } else {
            // If refresh fails, logout
            await logout();
            throw new Error("Session expired. Please log in again.");
          }
        } catch (refreshError) {
          await logout();
          throw refreshError;
        }
      }
      throw error;
    }
  };
  
  // POST request with authentication
  const post = async (endpoint: string, data: any) => {
    try {
      const response = await fetchWithAuth(endpoint, {
        method: "POST",
        body: JSON.stringify(data)
      });
      return await response.json();
    } catch (error) {
      if (error instanceof Error && error.message === "UNAUTHORIZED") {
        try {
          const newToken = await refreshToken();
          if (newToken) {
            const retryResponse = await fetchWithAuth(endpoint, {
              method: "POST",
              body: JSON.stringify(data)
            });
            return await retryResponse.json();
          } else {
            await logout();
            throw new Error("Session expired. Please log in again.");
          }
        } catch (refreshError) {
          await logout();
          throw refreshError;
        }
      }
      throw error;
    }
  };
  
  // PUT request with authentication
  const put = async (endpoint: string, data: any) => {
    try {
      const response = await fetchWithAuth(endpoint, {
        method: "PUT",
        body: JSON.stringify(data)
      });
      return await response.json();
    } catch (error) {
      if (error instanceof Error && error.message === "UNAUTHORIZED") {
        // Same refresh pattern as above
        try {
          const newToken = await refreshToken();
          if (newToken) {
            const retryResponse = await fetchWithAuth(endpoint, {
              method: "PUT",
              body: JSON.stringify(data)
            });
            return await retryResponse.json();
          } else {
            await logout();
            throw new Error("Session expired. Please log in again.");
          }
        } catch (refreshError) {
          await logout();
          throw refreshError;
        }
      }
      throw error;
    }
  };
  
  // DELETE request with authentication
  const del = async (endpoint: string) => {
    try {
      const response = await fetchWithAuth(endpoint, { method: "DELETE" });
      return await response.json();
    } catch (error) {
      if (error instanceof Error && error.message === "UNAUTHORIZED") {
        // Same refresh pattern as above
        try {
          const newToken = await refreshToken();
          if (newToken) {
            const retryResponse = await fetchWithAuth(endpoint, { method: "DELETE" });
            return await retryResponse.json();
          } else {
            await logout();
            throw new Error("Session expired. Please log in again.");
          }
        } catch (refreshError) {
          await logout();
          throw refreshError;
        }
      }
      throw error;
    }
  };
  
  return { get, post, put, del };
};