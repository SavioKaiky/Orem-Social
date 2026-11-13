import { useQuery } from '@tanstack/react-query';
import React, { useState } from 'react';

import { api, messageOf } from '../lib/api';
import { Paginated } from '../lib/types';
import { Banner, Body, Button, Card } from './ui';

const STATUS_LABELS = {
  active: 'Adimplente',
  inactive: 'Inadimplente',
  pending: 'Aguardando primeiro pagamento',
};

type BeneficiaryStatus = keyof typeof STATUS_LABELS;
type WorkerSummary = {
  total: number;
  groups: { by_status: Partial<Record<BeneficiaryStatus, number>> }[];
};

type Beneficiary = {
  id: number;
  full_name: string;
  status: BeneficiaryStatus;
};

export function WorkerDashboard({ userId }: { userId: number }) {
  const [page, setPage] = useState(1);
  const summary = useQuery({
    queryKey: ['worker-beneficiaries-summary', userId],
    queryFn: () => api<WorkerSummary>('/beneficiaries/summary/'),
  });
  const beneficiaries = useQuery({
    queryKey: ['worker-beneficiaries', userId, page],
    queryFn: () => api<Paginated<Beneficiary>>(`/beneficiaries/?page=${page}`),
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
        <Body>Painel do obreiro</Body>
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

      <Body>Beneficiários vinculados</Body>
      {beneficiaries.isError ? (
        <Banner kind="error">{messageOf(beneficiaries.error)}</Banner>
      ) : beneficiaries.data ? (
        <>
          {beneficiaries.data.results.length === 0 ? (
            <Body muted>Nenhum beneficiário vinculado.</Body>
          ) : (
            beneficiaries.data.results.map((beneficiary) => (
              <Card key={beneficiary.id}>
                <Body>{beneficiary.full_name}</Body>
                <Body muted>{STATUS_LABELS[beneficiary.status]}</Body>
              </Card>
            ))
          )}
          {beneficiaries.data.previous ? (
            <Button title="Página anterior" variant="outline" onPress={() => setPage(page - 1)} />
          ) : null}
          {beneficiaries.data.next ? (
            <Button title="Próxima página" variant="outline" onPress={() => setPage(page + 1)} />
          ) : null}
        </>
      ) : (
        <Body muted>Carregando os beneficiários...</Body>
      )}
    </>
  );
}
