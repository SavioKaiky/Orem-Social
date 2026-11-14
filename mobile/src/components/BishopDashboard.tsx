import { useQuery } from '@tanstack/react-query';
import React from 'react';

import { api, messageOf } from '../lib/api';
import { formatMoney } from '../lib/format';
import { Banner, Body, Card } from './ui';

type BeneficiarySummary = {
  total: number;
  groups: { by_status: Partial<Record<'active' | 'inactive' | 'pending', number>> }[];
};

export function BishopDashboard({ userId }: { userId: number }) {
  const summary = useQuery({
    queryKey: ['bishop-beneficiaries-summary', userId],
    queryFn: () => api<BeneficiarySummary>('/beneficiaries/summary/'),
  });
  const revenue = useQuery({
    queryKey: ['bishop-monthly-revenue', userId],
    queryFn: () => api<{ month: string; total: string }>('/billing/payments/monthly-revenue/'),
  });
  const counts = summary.data?.groups.reduce(
    (totals, { by_status }) => ({
      active: totals.active + (by_status.active ?? 0),
      inactive: totals.inactive + (by_status.inactive ?? 0),
      pending: totals.pending + (by_status.pending ?? 0),
    }),
    { active: 0, inactive: 0, pending: 0 },
  );

  return (
    <>
      <Card>
        <Body>Painel do Bispo Presidente</Body>
        {summary.isError ? (
          <Banner kind="error">{messageOf(summary.error)}</Banner>
        ) : summary.data && counts ? (
          <>
            <Body>Cadastrados: {summary.data.total}</Body>
            <Body>Adimplentes: {counts.active}</Body>
            <Body>Inadimplentes: {counts.inactive}</Body>
            <Body>Aguardando primeiro pagamento: {counts.pending}</Body>
          </>
        ) : (
          <Body muted>Carregando os totais...</Body>
        )}
      </Card>
      <Card>
        <Body>Receita de contribuições no mês</Body>
        {revenue.isError ? (
          <Banner kind="error">{messageOf(revenue.error)}</Banner>
        ) : revenue.data ? (
          <>
            <Body>{formatMoney(revenue.data.total)}</Body>
            <Body muted>{revenue.data.month.split('-').reverse().join('/')}</Body>
          </>
        ) : (
          <Body muted>Carregando a receita...</Body>
        )}
      </Card>
    </>
  );
}
