import * as SecureStore from 'expo-secure-store';

const KEY = 'orem.tokens';

export type Tokens = { access: string; refresh: string };

// Os tokens ficam no armazenamento seguro do aparelho, nunca em texto simples
export async function loadTokens(): Promise<Tokens | null> {
  const raw = await SecureStore.getItemAsync(KEY);
  return raw ? (JSON.parse(raw) as Tokens) : null;
}

export async function saveTokens(tokens: Tokens): Promise<void> {
  await SecureStore.setItemAsync(KEY, JSON.stringify(tokens));
}

export async function clearTokens(): Promise<void> {
  await SecureStore.deleteItemAsync(KEY);
}