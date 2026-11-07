import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'expo-router';
import React from 'react';
import { Text } from 'react-native';

import { Banner, Body, Button, Card, Loading, Screen, Title } from '../../src/components/ui';
import { api, messageOf } from '../../src/lib/api';
import { useAuth } from '../../src/lib/auth';
import { firstName, formatDate, formatMoney } from '../../src/lib/format';
import { BillingSummary, Notification, Paginated } from '../../src/lib/types';
import { colors, font } from '../../src/theme';

export default function HomeScreen() {
  const { user } = useAuth();
  const router = useRouter();
  const isBeneficiary = user?.role === 'beneficiary';

  const billing = useQuery({
    queryKey: ['billing-me'],
    queryFn: () => api<BillingSummary>('/billing/me/'),
    enabled: isBeneficiary,
  });

  const notifications = useQuery({
    queryKey: ['billing-notifications'],
    queryFn: () => api<Paginated<Notification>>('/billing/notifications/'),
    enabled: isBeneficiary,
  });

  if (!user) return <Loading />;

  return (
    <Screen>
      <Title>Olá, {firstName(user.full_name)}!</Title>

      {!isBeneficiary ? (
        <Card>
          <Body>O seu painel de gestão será liberado nas próximas atualizações do aplicativo.</Body>
        </Card>
      ) : billing.isLoading ? (
        <Body muted>Carregando sua situação...</Body>
      ) : billing.isError ? (
        <Banner kind="error">{messageOf(billing.error)}</Banner>
      ) : billing.data ? (
        <>
          {notifications.data?.results.map((notification) => (
            <Card key={notification.id}>
              <Text style={{ fontSize: font.small, fontWeight: '700', color: colors.accent }}>
                {notification.title}
              </Text>
              <Body>{notification.body}</Body>
            </Card>
          ))}

          <Card>
            <Text style={{ fontSize: font.small, color: colors.muted }}>Situação da contribuição</Text>
            {billing.data.is_current ? (
              <>
                <Text style={{ fontSize: font.title, fontWeight: '700', color: colors.success }}>Em dia</Text>
                <Body>Seus benefícios estão ativos até {formatDate(billing.data.covered_until)}.</Body>
                <Body muted>
                  {billing.data.carence_met
                    ? 'Carência cumprida: todos os benefícios estão liberados.'
                    : `Carência em andamento (${billing.data.carence_days} dias de contribuição contínua).`}
                </Body>
              </>
            ) : billing.data.status === 'inactive' ? (
              <>
                <Text style={{ fontSize: font.title, fontWeight: '700', color: colors.danger }}>Inativo</Text>
                <Body>Seu prazo venceu. Contribua para reativar. A contagem da carência recomeça.</Body>
              </>
            ) : (
              <>
                <Text style={{ fontSize: font.title, fontWeight: '700', color: colors.accent }}>Aguardando pagamento</Text>
                <Body>Faça sua primeira contribuição para liberar os benefícios.</Body>
              </>
            )}
          </Card>

          <Card>
            <Text style={{ fontSize: font.small, color: colors.muted }}>Contribuição mensal</Text>
            <Text style={{ fontSize: font.hero, fontWeight: '800', color: colors.text }}>
              {formatMoney(billing.data.next_amount)}
            </Text>
            <Body muted>Você + {billing.data.dependents_count} dependente(s)</Body>
          </Card>

          {billing.data.can_renew ? (
            <Button title="Pagar contribuição" onPress={() => router.push('/pay')} />
          ) : (
            <Banner kind="success">Sua contribuição está em dia. O próximo pagamento será liberado perto do vencimento.</Banner>
          )}
        </>
      ) : null}
    </Screen>
  );
}