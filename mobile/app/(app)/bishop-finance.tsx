import { useQuery } from '@tanstack/react-query';
import { Redirect } from 'expo-router';
import React from 'react';

import { Banner, Body, Card, Loading, Screen, Title } from '../../src/components/ui';
import { api, messageOf } from '../../src/lib/api';
import { useAuth } from '../../src/lib/auth';
import { formatMoney } from '../../src/lib/format';

type BishopFinanceSummary = {
  prebenda?: {
    active_holders: number;
    active_dependents: number;
    total_reais: number;
  };
};

export default function BishopFinanceScreen() {
  const { user, loading } = useAuth();
  const isBishop = !loading && user?.role === 'bishop';

  const summary = useQuery({
    queryKey: ['bishop-beneficiaries-summary', user?.id],
    queryFn: () => api<BishopFinanceSummary>('/beneficiaries/summary/'),
    enabled: isBishop,
  });
  const revenue = useQuery({
    queryKey: ['bishop-monthly-revenue', user?.id],
    enabled: isBishop,
    queryFn: () => api<{ month: string; total: string }>('/billing/payments/monthly-revenue/'),
  });

  if (loading) return <Loading />;
  if (!user) return <Redirect href="/login" />;
  if (!isBishop) return <Redirect href="/(app)/home" />;

  const prebenda = summary.data?.prebenda;

  return (
    <Screen>
      <Title>Financeiro</Title>
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
      <Card>
        <Body>Prebenda estimada</Body>
        {summary.isError ? (
          <Banner kind="error">{messageOf(summary.error)}</Banner>
        ) : summary.isPending ? (
          <Body muted>Carregando a prebenda...</Body>
        ) : prebenda ? (
          <>
            <Body>{formatMoney(prebenda.total_reais)}</Body>
            <Body muted>Titulares adimplentes: {prebenda.active_holders} × R$ 2,00</Body>
            <Body muted>Dependentes ativos desses titulares: {prebenda.active_dependents} × R$ 1,00</Body>
          </>
        ) : (
          <Body muted>Prebenda indisponível.</Body>
        )}
      </Card>
    </Screen>
  );
}
