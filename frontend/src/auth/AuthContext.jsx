import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  getCurrentUser,
  loginAccount,
  logoutAccount,
} from "../api/auth";

import {
  TOKEN_STORAGE_KEY,
  REFRESH_TOKEN_STORAGE_KEY,
} from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({
  children,
}) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sessionExpiredMessage, setSessionExpiredMessage] = useState(null);

  const logout = useCallback(async () => {
    const refreshToken = sessionStorage.getItem(
      REFRESH_TOKEN_STORAGE_KEY
    );

    // Server-side revocation (best-effort)
    await logoutAccount(refreshToken);

    // Clear all client-side auth state
    sessionStorage.removeItem(
      TOKEN_STORAGE_KEY
    );
    sessionStorage.removeItem(
      REFRESH_TOKEN_STORAGE_KEY
    );

    setUser(null);
    setSessionExpiredMessage(null);
  }, []);

  // Listen for session-expired events from the API interceptor
  useEffect(() => {
    function handleSessionExpired() {
      sessionStorage.removeItem(TOKEN_STORAGE_KEY);
      sessionStorage.removeItem(REFRESH_TOKEN_STORAGE_KEY);
      setUser(null);
      setSessionExpiredMessage(
        "Your session has expired. Please sign in again."
      );
    }

    window.addEventListener(
      "auth:session-expired",
      handleSessionExpired
    );

    return () => {
      window.removeEventListener(
        "auth:session-expired",
        handleSessionExpired
      );
    };
  }, []);

  const refreshUser = useCallback(async () => {
    const token = sessionStorage.getItem(TOKEN_STORAGE_KEY);
    if (!token) {
      setUser(null);
      setLoading(false);
      return null;
    }
    try {
      const currentUser = await getCurrentUser();
      setUser(currentUser);
      return currentUser;
    } catch {
      sessionStorage.removeItem(TOKEN_STORAGE_KEY);
      sessionStorage.removeItem(REFRESH_TOKEN_STORAGE_KEY);
      setUser(null);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let isMounted = true;
    const token = sessionStorage.getItem(TOKEN_STORAGE_KEY);
    if (!token) {
      queueMicrotask(() => {
        if (isMounted) {
          setUser(null);
          setLoading(false);
        }
      });
      return () => {
        isMounted = false;
      };
    }
    getCurrentUser()
      .then((currentUser) => {
        if (isMounted) setUser(currentUser);
      })
      .catch(() => {
        if (isMounted) {
          sessionStorage.removeItem(TOKEN_STORAGE_KEY);
          sessionStorage.removeItem(REFRESH_TOKEN_STORAGE_KEY);
          setUser(null);
        }
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });
    return () => {
      isMounted = false;
    };
  }, []);

  const login = useCallback(
    async ({
      email,
      password,
    }) => {
      const result = await loginAccount({
        email,
        password,
      });

      const token =
        result?.access_token ||
        result?.token;

      if (!token) {
        throw new Error(
          "The backend did not return an access token."
        );
      }

      // Store both access and refresh tokens
      sessionStorage.setItem(
        TOKEN_STORAGE_KEY,
        token
      );

      if (result?.refresh_token) {
        sessionStorage.setItem(
          REFRESH_TOKEN_STORAGE_KEY,
          result.refresh_token
        );
      }

      // Clear any expired-session messages
      setSessionExpiredMessage(null);

      try {
        const currentUser =
          await getCurrentUser();

        setUser(currentUser);

        return currentUser;
      } catch (error) {
        sessionStorage.removeItem(
          TOKEN_STORAGE_KEY
        );
        sessionStorage.removeItem(
          REFRESH_TOKEN_STORAGE_KEY
        );

        throw error;
      }
    },
    []
  );

  const value = useMemo(
    () => ({
      user,
      loading,
      login,
      logout,
      refreshUser,
      isAuthenticated: Boolean(user),
      sessionExpiredMessage,
      clearSessionExpiredMessage: () => setSessionExpiredMessage(null),
    }),
    [
      user,
      loading,
      login,
      logout,
      refreshUser,
      sessionExpiredMessage,
    ]
  );

  return (
    <AuthContext.Provider
      value={value}
    >
      {children}
    </AuthContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const context =
    useContext(AuthContext);

  if (!context) {
    throw new Error(
      "useAuth must be used inside AuthProvider."
    );
  }

  return context;
}