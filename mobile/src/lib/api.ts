import { clearTokens, loadTokens, saveTokens, Tokens } from './tokens';

// 10.0.2.2 só funciona no emulador; no celular físico use o EXPO_PUBLIC_API_URL do .env
const BASE_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://10.0.2.2:8000/api';

export class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(status: number, data: unknown, message: string) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

type Options = {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE';
  body?: unknown;
  auth?: boolean;
};

let onSessionExpired: (() => void) | null = null;
export function setSessionExpiredHandler(handler: (() => void) | null) {
  onSessionExpired = handler;
}

const FIELD_LABELS: Record<string, string> = {
  cpf: 'CPF',
  full_name: 'Nome',
  phone: 'Telefone',
  email: 'E-mail',
  password: 'Senha',
  birth_date: 'Data de nascimento',
  city: 'Cidade',
  state: 'Estado',
  worker_code: 'Código do obreiro',
  accept_terms: 'Termos de uso',
  relationship: 'Parentesco',
  dependents: 'Dependentes',
};

// Achata o erro do Django (campos, listas, objetos aninhados) em uma frase para o usuário
function extractMessage(data: unknown, status: number): string {
  if (status === 0) return 'Sem conexão com o servidor. Verifique sua internet e tente novamente.';
  if (status === 429) return 'Muitas tentativas. Aguarde um minuto e tente de novo.';
  if (status >= 500) return 'O servidor teve um problema. Tente novamente em instantes.';

  const found: string[] = [];
  const walk = (value: unknown, label?: string) => {
    if (typeof value === 'string') {
      found.push(label ? `${label}: ${value}` : value);
    } else if (Array.isArray(value)) {
      value.forEach((item) => walk(item, label));
    } else if (value && typeof value === 'object') {
      Object.entries(value as Record<string, unknown>).forEach(([key, inner]) => {
        const isGeneric = key === 'detail' || key === 'non_field_errors';
        walk(inner, isGeneric ? undefined : (FIELD_LABELS[key] ?? label));
      });
    }
  };
  walk(data);
  return found[0] ?? 'Não foi possível concluir. Tente novamente.';
}

async function send(path: string, options: Options, access: string | null): Promise<Response> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (access) headers.Authorization = `Bearer ${access}`;
  return fetch(`${BASE_URL}${path}`, {
    method: options.method ?? 'GET',
    headers,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  });
}

let refreshing: Promise<Tokens | null> | null = null;

async function refreshTokens(): Promise<Tokens | null> {
  const current = await loadTokens();
  if (!current) return null;
  try {
    const response = await fetch(`${BASE_URL}/auth/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh: current.refresh }),
    });
    if (!response.ok) return null;
    const data = await response.json();
    // O backend gira o refresh a cada uso: guardamos o novo
    const next: Tokens = { access: data.access, refresh: data.refresh ?? current.refresh };
    await saveTokens(next);
    return next;
  } catch {
    return null;
  }
}

export async function api<T>(path: string, options: Options = {}): Promise<T> {
  const useAuth = options.auth !== false;
  const tokens = useAuth ? await loadTokens() : null;

  let response: Response;
  try {
    response = await send(path, options, tokens?.access ?? null);
  } catch {
    throw new ApiError(0, null, extractMessage(null, 0));
  }

  if (response.status === 401 && useAuth && tokens) {
    // Várias chamadas podem receber 401 juntas; só uma renova o token
    if (!refreshing) {
      refreshing = refreshTokens().finally(() => {
        refreshing = null;
      });
    }
    const next = await refreshing;
    if (!next) {
      await clearTokens();
      onSessionExpired?.();
      throw new ApiError(401, null, 'Sua sessão expirou. Entre novamente.');
    }
    try {
      response = await send(path, options, next.access);
    } catch {
      throw new ApiError(0, null, extractMessage(null, 0));
    }
  }

  const text = await response.text();
  let data: unknown = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = null;
  }
  if (!response.ok) {
    throw new ApiError(response.status, data, extractMessage(data, response.status));
  }
  return data as T;
}

export function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : 'Não foi possível concluir. Tente novamente.';
}
