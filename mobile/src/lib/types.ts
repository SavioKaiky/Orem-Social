export type Role = 'admin' | 'bishop' | 'worker' | 'beneficiary' | 'provider';

export type User = {
  id: number;
  cpf: string;
  full_name: string;
  email: string;
  phone: string;
  role: Role;
  worker_code: string | null;
};

export type BillingSummary = {
  status: 'pending' | 'active' | 'inactive';
  covered_until: string | null;
  grace_deadline: string | null;
  is_current: boolean;
  carence_met: boolean;
  carence_days: number;
  carence_months: number;
  can_renew: boolean;
  next_amount: string;
  dependents_count: number;
};

export type PaymentMethodInfo = {
  code: 'pix_automatic' | 'pix_manual';
  title: string;
  description: string;
  recommended: boolean;
  available: boolean;
};

export type Payment = {
  id: number;
  amount: string;
  status: 'pending' | 'paid' | 'expired';
  txid: string;
  pix_copy_paste: string;
  expires_at: string;
  paid_at: string | null;
};

export type Pricing = {
  valid_from: string;
  minimum_wage: string;
  holder_amount: string;
  dependent_amount: string;
};

export type Terms = { version: string; content: string };
