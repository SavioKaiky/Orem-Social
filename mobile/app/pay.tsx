import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import * as Clipboard from 'expo-clipboard';
import { Redirect, useRouter } from 'expo-router';
import React, { useState } from 'react';
import { Pressable, Text, View } from 'react-native';
import QRCode from 'react-native-qrcode-svg';

import { Banner, Body, Button, Card, Screen, Title } from '../src/components/ui';
import { api, messageOf } from '../src/lib/api';
import { useAuth } from '../src/lib/auth';
import { formatMoney } from '../src/lib/format';
import { BillingSummary, Payment, PaymentMethodInfo } from '../src/lib/types';
import { colors, radius, spacing } from '../src/theme';

// O botão de simulação aparece no Expo Go (__DEV__) e nos builds de teste, que ligam esta variável
// no eas.json. O perfil "production" não a define, então o app público nunca mostra o botão.
const SIMULATOR_ENABLED =
  __DEV__ || process.env.EXPO_PUBLIC_ENABLE_PAYMENT_SIMULATOR === 'true';

export default function PayScreen() {
  const router = useRouter();
  const { user, loading } = useAuth();
  const queryClient = useQueryClient();
  const [method, setMethod] = useState<PaymentMethodInfo['code']>('pix_manual');
  const [payment, setPayment] = useState<Payment | null>(null);
  const [copied, setCopied] = useState(false);

  const methods = useQuery({
    queryKey: ['payment-methods'],
    queryFn: () => api<PaymentMethodInfo[]>('/billing/payment-methods/'),
  });
  const summary = useQuery({
    queryKey: ['billing-me'],
    queryFn: () => api<BillingSummary>('/billing/me/'),
  });

  const createCharge = useMutation({
    mutationFn: () => api<Payment>('/billing/charges/', { method: 'POST' }),
    onSuccess: (data) => setPayment(data),
  });

  // Enquanto o PIX não for confirmado, consulta o servidor a cada 5 segundos
  const status = useQuery({
    queryKey: ['payment', payment?.id],
    queryFn: () => api<Payment>(`/billing/payments/${payment?.id}/`),
    enabled: !!payment && payment.status === 'pending',
    refetchInterval: (query) => (query.state.data?.status === 'paid' ? false : 5000),
  });

  // Se qualquer fonte já disser "pago", vale essa; senão usa a resposta mais recente
  const current = [status.data, payment].find((item) => item?.status === 'paid') ?? status.data ?? payment;
  const paid = current?.status === 'paid';

  React.useEffect(() => {
    if (paid) queryClient.invalidateQueries({ queryKey: ['billing-me'] });
  }, [paid, queryClient]);

  const simulate = useMutation({
    // O txid entra como argumento (e não lido de `current` aqui dentro): o React Compiler
    // lê esses valores antecipadamente e quebrava com `current` ainda nulo
    mutationFn: (txid: string) =>
      api<Payment>('/billing/dev/simulate-payment/', { method: 'POST', body: { txid } }),
    onSuccess: (data) => {
      setPayment(data);
      queryClient.setQueryData(['payment', data.id], data);
    },
  });

  async function copyCode(code: string) {
    await Clipboard.setStringAsync(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 3000);
  }

  // Esta tela está fora das abas, então ela mesma confere se há sessão
  if (!loading && !user) return <Redirect href="/login" />;

  if (paid) {
    return (
      <Screen>
        <Title>Pagamento confirmado!</Title>
        <Banner kind="success">Recebemos sua contribuição. Seus benefícios estão ativos. Obrigado!</Banner>
        <Button title="Voltar ao início" onPress={() => router.replace('/home')} />
      </Screen>
    );
  }

  if (current) {
    return (
      <Screen>
        <Title>Pague com PIX</Title>
        <Body muted>Valor: {formatMoney(current.amount)}</Body>
        <View
          style={{
            alignItems: 'center',
            marginVertical: spacing.lg,
            padding: spacing.md,
            backgroundColor: '#fff',
            borderRadius: radius.md,
          }}>
          <QRCode value={current.pix_copy_paste} size={220} />
        </View>
        <Body>
          1. Abra o aplicativo do seu banco.{'\n'}2. Escolha pagar com PIX e leia o QR Code, ou use o código copia e
          cola.{'\n'}3. Volte aqui: a confirmação aparece sozinha.
        </Body>
        <View style={{ height: spacing.md }} />
        <Button title={copied ? 'Código copiado!' : 'Copiar código PIX'} onPress={() => copyCode(current.pix_copy_paste)} />
        <Banner kind="info">Aguardando o pagamento... Esta cobrança vale por 24 horas.</Banner>
        {simulate.isError ? (
          <Banner kind="error">
            A simulação falhou: {messageOf(simulate.error)} Confira se o backend está com DJANGO_DEBUG=True.
          </Banner>
        ) : null}
        {SIMULATOR_ENABLED ? (
          <Button
            title="Simular pagamento (apenas em testes)"
            variant="outline"
            onPress={() => simulate.mutate(current.txid)}
            loading={simulate.isPending}
          />
        ) : null}
        <Button title="Voltar" variant="ghost" onPress={() => router.back()} />
      </Screen>
    );
  }

  return (
    <Screen>
      <Title>Como você quer pagar?</Title>
      {summary.data ? <Body muted>Valor da contribuição: {formatMoney(summary.data.next_amount)}</Body> : null}
      <View style={{ height: spacing.md }} />

      {methods.isLoading ? <Body muted>Carregando...</Body> : null}
      {methods.isError ? <Banner kind="error">{messageOf(methods.error)}</Banner> : null}

      {Array.isArray(methods.data) ? methods.data.map((item) => {
        const selected = method === item.code && item.available;
        return (
          <Pressable
            key={item.code}
            disabled={!item.available}
            onPress={() => setMethod(item.code)}
            style={{ opacity: item.available ? 1 : 0.6 }}>
            <Card>
              <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
                <Text style={{ fontSize: 18, fontWeight: '700', color: selected ? colors.primary : colors.text }}>
                  {selected ? '● ' : '○ '}
                  {item.title}
                </Text>
                {item.recommended ? (
                  <Text
                    style={{
                      backgroundColor: colors.accent,
                      color: '#fff',
                      fontWeight: '700',
                      paddingHorizontal: 10,
                      paddingVertical: 4,
                      borderRadius: 999,
                      overflow: 'hidden',
                    }}>
                    Recomendado
                  </Text>
                ) : null}
              </View>
              <Body muted>{item.description}</Body>
              {!item.available ? <Body>Em breve no aplicativo.</Body> : null}
            </Card>
          </Pressable>
        );
      }) : null}

      {methods.data && !Array.isArray(methods.data) ? (
        <Banner kind="error">Resposta inesperada do servidor em payment-methods.</Banner>
      ) : null}

      {createCharge.isError ? <Banner kind="error">{messageOf(createCharge.error)}</Banner> : null}
      <Button
        title="Gerar PIX"
        onPress={() => createCharge.mutate()}
        loading={createCharge.isPending}
        disabled={method !== 'pix_manual'}
      />
      <Button title="Voltar" variant="ghost" onPress={() => router.back()} />
    </Screen>
  );
}