import { useQuery } from '@tanstack/react-query';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import React from 'react';
import { Pressable, Text, View } from 'react-native';

import { Banner, Body, Button, Card, Loading, Screen, Title } from '../../src/components/ui';
import { api, messageOf } from '../../src/lib/api';
import { useAuth } from '../../src/lib/auth';
import { firstName, formatDate, formatMoney } from '../../src/lib/format';
import { BillingSummary, Notification, Paginated } from '../../src/lib/types';
import { WorkerDashboard } from '../../src/components/WorkerDashboard';
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
    queryKey: ['billing-notifications', 1],
    queryFn: () => api<Paginated<Notification>>('/billing/notifications/'),
    enabled: isBeneficiary,
  });

  if (!user) return <Loading />;

  const unreadCount = notifications.data?.results.filter((notification) => !notification.read_at).length ?? 0;

  return (
    <Screen>
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
        <Title>Olá, {firstName(user.full_name)}!</Title>
        {isBeneficiary ? (
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={unreadCount ? `Notificações, ${unreadCount} não lidas` : 'Notificações'}
            onPress={() => router.push('/notifications')}
            style={{ padding: 8 }}>
            <Ionicons name="notifications-outline" size={26} color={colors.primary} />
            {unreadCount > 0 ? (
              <View
                style={{
                  position: 'absolute',
                  top: 0,
                  right: 0,
                  minWidth: 18,
                  height: 18,
                  paddingHorizontal: 4,
                  borderRadius: 9,
                  backgroundColor: colors.danger,
                  alignItems: 'center',
                  justifyContent: 'center',
                }}>
                <Text style={{ color: '#fff', fontSize: 11, fontWeight: '700' }}>
                  {unreadCount > 9 ? '9+' : unreadCount}
                </Text>
              </View>
            ) : null}
          </Pressable>
        ) : null}
      </View>

      {user.role === 'worker' ? (
        <WorkerDashboard key={user.id} userId={user.id} />
      ) : !isBeneficiary ? (
        <Card>
          <Body>O seu painel de gestão será liberado nas próximas atualizações do aplicativo.</Body>
        </Card>
      ) : billing.isLoading ? (
        <Body muted>Carregando sua situação...</Body>
      ) : billing.isError ? (
        <Banner kind="error">{messageOf(billing.error)}</Banner>
      ) : billing.data ? (
        <>
          <Card>
            <Text style={{ fontSize: font.small, color: colors.muted }}>Situação da contribuição</Text>
            {billing.data.is_current ? (
              <>
                <Text style={{ fontSize: font.title, fontWeight: '700', color: colors.success }}>Em dia</Text>
                <Body>Sua contribuição cobre o período até {formatDate(billing.data.covered_until)}.</Body>
                <Body muted>
                  {billing.data.carence_met
                    ? 'Carência geral de 4 meses cumprida.'
                    : `Carência em andamento (${billing.data.carence_months ?? 4} meses de contribuição contínua).`}
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
                <Body>Faça sua primeira contribuição para ativar seu cadastro. A telemedicina não exige carência.</Body>
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