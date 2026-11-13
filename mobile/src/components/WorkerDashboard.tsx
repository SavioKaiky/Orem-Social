import { useQuery } from '@tanstack/react-query';
import React, { useState } from 'react';
import { Alert, Linking, Text } from 'react-native';

import { api, messageOf } from '../lib/api';
import { maskPhone } from '../lib/format';
import { Paginated } from '../lib/types';
import { colors } from '../theme';
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
  phone: string;
  dependents: { id: number }[];
  status: BeneficiaryStatus;
};

async function openDialer(phone: string) {
  const digits = phone.replace(/\D/g, '');
  const number = phone.trimStart().startsWith('+') ? `+${digits}` : digits;

  try {
    await Linking.openURL(`tel:${number}`);
  } catch {
    Alert.alert('Não foi possível abrir o discador', 'Disque o número manualmente no aplicativo de telefone.');
  }
}

export function WorkerDashboard({ userId }: { userId: number }) {
  const [page, setPage] = useState(1);
  const [reportMonth, setReportMonth] = useState<Date | null>(null);
  const currentMonth = new Date();
  const monthFilter = reportMonth
    ? `${reportMonth.getFullYear()}-${String(reportMonth.getMonth() + 1).padStart(2, '0')}`
    : null;
  const currentMonthStart = new Date(currentMonth.getFullYear(), currentMonth.getMonth(), 1);

  function selectMonth(month: Date | null) {
    setReportMonth(month);
    setPage(1);
  }

  function moveMonth(offset: number) {
    if (reportMonth) {
      selectMonth(new Date(reportMonth.getFullYear(), reportMonth.getMonth() + offset, 1));
    }
  }
  const summary = useQuery({
    queryKey: ['worker-beneficiaries-summary', userId],
    queryFn: () => api<WorkerSummary>('/beneficiaries/summary/'),
  });
  const beneficiaries = useQuery({
    queryKey: ['worker-beneficiaries', userId, page, monthFilter],
    queryFn: () => {
      const monthParam = monthFilter ? `&month=${monthFilter}` : '';
      return api<Paginated<Beneficiary>>(`/beneficiaries/?page=${page}${monthParam}`);
    },
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

      {reportMonth ? (
        <Card>
          <Body>Cadastros de {reportMonth.toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' })}</Body>
          <Button title="Mês anterior" variant="outline" onPress={() => moveMonth(-1)} />
          {reportMonth < currentMonthStart ? (
            <Button title="Próximo mês" variant="outline" onPress={() => moveMonth(1)} />
          ) : null}
          <Button title="Ver todos os beneficiários" variant="outline" onPress={() => selectMonth(null)} />
        </Card>
      ) : (
        <Button title="Relatório mensal" variant="outline" onPress={() => selectMonth(currentMonthStart)} />
      )}

      {reportMonth ? null : <Body>Beneficiários vinculados</Body>}
      {beneficiaries.isError ? (
        <Banner kind="error">{messageOf(beneficiaries.error)}</Banner>
      ) : beneficiaries.data ? (
        <>
          {beneficiaries.data.results.length === 0 ? (
            <Body muted>{reportMonth ? 'Nenhum cadastro neste mês.' : 'Nenhum beneficiário vinculado.'}</Body>
          ) : (
            beneficiaries.data.results.map((beneficiary) => (
              <Card key={beneficiary.id}>
                <Body>{beneficiary.full_name}</Body>
                <Body muted>{STATUS_LABELS[beneficiary.status]}</Body>
                {reportMonth ? (
                  <>
                    <Body muted>
                      Telefone:{' '}
                      {beneficiary.phone && /\d/.test(beneficiary.phone) ? (
                        <Text
                          accessibilityRole="link"
                          accessibilityLabel={`Ligar para ${beneficiary.full_name}`}
                          onPress={() => openDialer(beneficiary.phone)}
                          style={{ color: colors.primary, textDecorationLine: 'underline' }}>
                          {maskPhone(beneficiary.phone)}
                        </Text>
                      ) : 'Não informado'}
                    </Body>
                    <Body muted>Dependentes ativos: {beneficiary.dependents.length}</Body>
                  </>
                ) : null}
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
