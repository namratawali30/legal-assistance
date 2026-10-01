import api from "./client";

export async function registerAccount({
  fullName,
  email,
  password,
}) {
  const response = await api.post(
    "/api/v1/auth/register",
    {
      full_name: fullName,
      email,
      password,
    }
  );

  return response.data;
}

export async function loginAccount({
  email,
  password,
}) {
  const response = await api.post(
    "/api/v1/auth/login",
    {
      email,
      password,
    }
  );

  return response.data;
}

export async function getCurrentUser() {
  const response = await api.get(
    "/api/v1/auth/me"
  );

  return response.data;
}

export async function refreshToken(refreshTokenValue) {
  const response = await api.post(
    "/api/v1/auth/refresh",
    { refresh_token: refreshTokenValue }
  );

  return response.data;
}

export async function logoutAccount(refreshTokenValue) {
  try {
    await api.post(
      "/api/v1/auth/logout",
      refreshTokenValue ? { refresh_token: refreshTokenValue } : {}
    );
  } catch {
    // Logout should not fail visibly to the user —
    // the frontend clears state regardless.
  }
}