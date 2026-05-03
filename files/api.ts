/**
 * Cliente HTTP tipado para consumir la API backend.
 * Usa el Result pattern para manejo explícito de errores.
 */
import type {
  ApiError,
  Result,
  TokenResponse,
  User,
  PaginatedResponse,
} from '@types/index';

const API_BASE = import.meta.env.PUBLIC_API_URL ?? 'http://localhost:8000';
const TIMEOUT_MS = Number(import.meta.env.PUBLIC_API_TIMEOUT ?? 30_000);

// ─── Helpers ──────────────────────────────────────────────────────────────────

function getAuthHeader(): Record<string, string> {
  const token = localStorage.getItem('access_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function parseResponse<T>(response: Response): Promise<Result<T>> {
  if (!response.ok) {
    let error: ApiError;
    try {
      const body = (await response.json()) as { error?: string; message?: string };
      error = {
        message: body.message ?? 'Error desconocido',
        code: body.error ?? 'UNKNOWN_ERROR',
        statusCode: response.status,
      };
    } catch {
      error = {
        message: response.statusText,
        code: 'HTTP_ERROR',
        statusCode: response.status,
      };
    }
    return { ok: false, error };
  }

  const data = (await response.json()) as T;
  return { ok: true, value: data };
}

async function request<T>(path: string, options: RequestInit = {}): Promise<Result<T>> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_MS);

  try {
    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
        ...options.headers,
      },
    });
    return await parseResponse<T>(response);
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      return {
        ok: false,
        error: {
          message: 'Tiempo de espera agotado.',
          code: 'TIMEOUT',
          statusCode: 408,
        },
      };
    }
    return {
      ok: false,
      error: { message: 'Error de red.', code: 'NETWORK_ERROR', statusCode: 0 },
    };
  } finally {
    clearTimeout(timeoutId);
  }
}

// ─── Auth API ─────────────────────────────────────────────────────────────────

export const authApi = {
  async login(email: string, password: string): Promise<Result<TokenResponse>> {
    const body = new URLSearchParams({ username: email, password });
    return request<TokenResponse>('/api/v1/auth/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: body.toString(),
    });
  },
};

// ─── Users API ────────────────────────────────────────────────────────────────

export const usersApi = {
  async create(input: {
    email: string;
    name: string;
    password: string;
  }): Promise<Result<User>> {
    return request<User>('/api/v1/users/', {
      method: 'POST',
      body: JSON.stringify(input),
    });
  },

  async getById(id: number): Promise<Result<User>> {
    return request<User>(`/api/v1/users/${id}`);
  },

  async list(params?: {
    skip?: number;
    limit?: number;
    onlyActive?: boolean;
  }): Promise<Result<PaginatedResponse<User>>> {
    const query = new URLSearchParams();
    if (params?.skip !== undefined) query.set('skip', String(params.skip));
    if (params?.limit !== undefined) query.set('limit', String(params.limit));
    if (params?.onlyActive) query.set('only_active', 'true');

    return request<PaginatedResponse<User>>(`/api/v1/users/?${query.toString()}`);
  },

  async update(
    id: number,
    data: { name?: string; isActive?: boolean }
  ): Promise<Result<User>> {
    return request<User>(`/api/v1/users/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  async delete(id: number): Promise<Result<void>> {
    return request<void>(`/api/v1/users/${id}`, { method: 'DELETE' });
  },
};
