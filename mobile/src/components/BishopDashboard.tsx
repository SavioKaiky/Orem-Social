import { useQuery } from '@tanstack/react-query';
import React, { useState } from 'react';

import { api, messageOf } from '../lib/api';
import { formatMoney } from '../lib/format';
import { Banner, Body, Button, Card } from './ui';

type BeneficiarySummary = {
  total: number;
  groups: {
    state: string;
    total: number;
    by_status: Partial<Record<'active' | 'inactive' | 'pending', number>>;
  }[];
};

type WorkerRankingEntry = {
  id: number;
  full_name: string;
  code: string | null;
  total: number;
  active: number;
};

export function BishopDashboard({ userId }: { userId: number }) {
  const [reportMonth, setReportMonth] = useState<Date | null>(null);
  const now = new Date();
  const currentMonth = new Date(now.getFullYear(), now.getMonth(), 1);
  const month = reportMonth
    ? `${reportMonth.getFullYear()}-${String(reportMonth.getMonth() + 1).padStart(2, '0')}`
    : null;
  const report = useQuery({
    queryKey: ['bishop-beneficiaries-summary', userId, month],
    queryFn: () => api<BeneficiarySummary>(`/beneficiaries/summary/?month=${month}`),
    enabled: month !== null,
  });

  function moveMonth(offset: number) {
    const selected = reportMonth ?? currentMonth;
    setReportMonth(new Date(selected.getFullYear(), selected.getMonth() + offset, 1));
  }

  const summary = useQuery({
    queryKey: ['bishop-beneficiaries-summary', userId],
    queryFn: () => api<BeneficiarySummary>('/beneficiaries/summary/'),
  });
  const revenue = useQuery({
    queryKey: ['bishop-monthly-revenue', userId],
    queryFn: () => api<{ month: string; total: string }>('/billing/payments/monthly-revenue/'),
  });
  const ranking = useQuery({
    queryKey: ['bishop-worker-ranking', userId],
    queryFn: () => api<WorkerRankingEntry[]>('/workers/ranking/'),
  });
  const reportQuery = month ? report : summary;
  const counts = summary.data?.groups.reduce(
    (totals, { by_status }) => ({
      active: totals.active + (by_status.active ?? 0),
      inactive: totals.inactive + (by_status.inactive ?? 0),
      pending: totals.pending + (by_status.pending ?? 0),
    }),
    { active: 0, inactive: 0, pending: 0 },
  );

  const assessedHolders = counts ? counts.active + counts.inactive : 0;
  const complianceRate = counts && assessedHolders > 0
    ? (counts.active / assessedHolders).toLocaleString('pt-BR', {
        style: 'percent',
        maximumFractionDigits: 2,
      })
    : null;

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
            <Body>Taxa de adimplência: {complianceRate ?? 'sem base para cálculo'}</Body>
            <Body muted>Base do cálculo: titulares adimplentes e inadimplentes.</Body>
          </>
        ) : (
          <Body muted>Carregando os totais...</Body>
        )}
      </Card>

      <Card>
        <Body>Ranking de obreiros</Body>
        <Body muted>Até 10 obreiros por número de beneficiários vinculados</Body>
        {ranking.isError ? (
          <Banner kind="error">{messageOf(ranking.error)}</Banner>
        ) : !ranking.data ? (
          <Body muted>Carregando o ranking...</Body>
        ) : ranking.data.length === 0 ? (
          <Body muted>Nenhum obreiro com beneficiários vinculados.</Body>
        ) : (
          ranking.data.map((worker, index) => (
            <React.Fragment key={worker.id}>
              <Body>{index + 1}. {worker.full_name}{worker.code ? ` (${worker.code})` : ''}</Body>
              <Body muted>Vinculados: {worker.total} · Adimplentes: {worker.active}</Body>
            </React.Fragment>
          ))
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
      <Card>
        <Body>Beneficiários por UF</Body>
        <Body muted>
          {reportMonth
            ? `Cadastros de ${reportMonth.toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' })}`
            : 'Todos os períodos'}
        </Body>
        {reportMonth ? (
          <>
            <Button title="Mês anterior" variant="outline" onPress={() => moveMonth(-1)} />
            {reportMonth < currentMonth ? (
              <Button title="Próximo mês" variant="outline" onPress={() => moveMonth(1)} />
            ) : null}
            <Button title="Todos os períodos" variant="outline" onPress={() => setReportMonth(null)} />
          </>
        ) : (
          <Button title="Filtrar por mês" variant="outline" onPress={() => setReportMonth(currentMonth)} />
        )}
      </Card>
      {reportQuery.isError ? (
        <Banner kind="error">{messageOf(reportQuery.error)}</Banner>
      ) : !reportQuery.data ? (
        <Body muted>Carregando o relatório...</Body>
      ) : reportQuery.data.groups.length === 0 ? (
        <Body muted>Nenhum cadastro no período.</Body>
      ) : (
        reportQuery.data.groups.map(({ state, total, by_status }) => (
          <Card key={state}>
            <Body>{state}</Body>
            <Body>Cadastrados: {total}</Body>
            <Body>Adimplentes: {by_status.active ?? 0}</Body>
            <Body>Inadimplentes: {by_status.inactive ?? 0}</Body>
            <Body>Aguardando primeiro pagamento: {by_status.pending ?? 0}</Body>
          </Card>
        ))
      )}
    </>
  );
}
