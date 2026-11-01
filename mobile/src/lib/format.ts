export const digits = (value: string) => value.replace(/\D/g, '');

export function maskCpf(value: string): string {
  const d = digits(value).slice(0, 11);
  return d
    .replace(/^(\d{3})(\d)/, '$1.$2')
    .replace(/^(\d{3})\.(\d{3})(\d)/, '$1.$2.$3')
    .replace(/\.(\d{3})(\d)/, '.$1-$2');
}

export function maskPhone(value: string): string {
  const d = digits(value).slice(0, 11);
  if (d.length <= 2) return d;
  if (d.length <= 7) return `(${d.slice(0, 2)}) ${d.slice(2)}`;
  return `(${d.slice(0, 2)}) ${d.slice(2, 7)}-${d.slice(7)}`;
}

export function maskDate(value: string): string {
  const d = digits(value).slice(0, 8);
  if (d.length <= 2) return d;
  if (d.length <= 4) return `${d.slice(0, 2)}/${d.slice(2)}`;
  return `${d.slice(0, 2)}/${d.slice(2, 4)}/${d.slice(4)}`;
}

// "20/04/1985" -> "1985-04-20"; devolve null se a data não existir ou for futura
export function dateBrToIso(value: string): string | null {
  const match = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(value);
  if (!match) return null;
  const [, dd, mm, yyyy] = match;
  const date = new Date(Number(yyyy), Number(mm) - 1, Number(dd));
  const valid =
    date.getFullYear() === Number(yyyy) &&
    date.getMonth() === Number(mm) - 1 &&
    date.getDate() === Number(dd);
  if (!valid || date > new Date() || Number(yyyy) < 1900) return null;
  return `${yyyy}-${mm}-${dd}`;
}

export function formatMoney(value: string | number): string {
  return `R$ ${Number(value).toFixed(2).replace('.', ',')}`;
}

export function formatDate(iso: string | null): string {
  if (!iso) return '-';
  const date = new Date(iso);
  const dd = String(date.getDate()).padStart(2, '0');
  const mm = String(date.getMonth() + 1).padStart(2, '0');
  return `${dd}/${mm}/${date.getFullYear()}`;
}

export const firstName = (fullName: string) => fullName.trim().split(/\s+/)[0] ?? '';