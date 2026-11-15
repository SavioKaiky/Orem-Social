import { useQuery } from '@tanstack/react-query';
import { Redirect } from 'expo-router';
import React from 'react';

import { Banner, Body, Card, Loading, Screen, Title } from '../../src/components/ui';
import { api, messageOf } from '../../src/lib/api';
import { useAuth } from '../../src/lib/auth';
import { formatMoney } from '../../src/lib/format';

export default function WorkerFinanceScreen() {
  const { user, loading } = useAuth();
  const isWorker = !loading && user?.role === 'worker';

  const revenue = useQuery({
    queryKey: ['worker-monthly-revenue', user?.id],
    enabled: isWorker,
    queryFn: () => api<{ month: string; total: string }>('/billing/payments/monthly-revenue/'),
  });

  if (loading) return <Loading />;
  if (!user) return <Redirect href="/login" />;
  if (!isWorker) return <Redirect href="/(app)/home" />;

  return (
    <Screen>
      <Title>Financeiro</Title>
      <Card>
        <Body>Contribuições confirmadas no mês</Body>
        {revenue.isError ? (
          <Banner kind="error">{messageOf(revenue.error)}</Banner>
        ) : revenue.data ? (
          <>
            <Body>{formatMoney(revenue.data.total)}</Body>
            <Body muted>Dos seus titulares vinculados</Body>
            <Body muted>{revenue.data.month.split('-').reverse().join('/')}</Body>
          </>
        ) : (
          <Body muted>Carregando a receita...</Body>
        )}
      </Card>
    </Screen>
  );
}