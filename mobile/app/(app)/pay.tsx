import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import * as Clipboard from 'expo-clipboard';
import { useRouter } from 'expo-router';
import React, { useState } from 'react';
import { Pressable, Text, View } from 'react-native';
import QRCode from 'react-native-qrcode-svg';

import { Banner, Body, Button, Card, Screen, Title } from '../../src/components/ui';
import { api, messageOf } from '../../src/lib/api';
import { formatMoney } from '../../src/lib/format';
import { BillingSummary, Payment, PaymentMethodInfo } from '../../src/lib/types';
import { colors, radius, spacing } from '../../src/theme';

export default function PayScreen() {
  const router = useRouter();
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
    queryFn: () => api<Payment>(`/billing/payments/${payment!.id}/`),
    enabled: !!payment && payment.status === 'pending',
    refetchInterval: (query) => (query.state.data?.status === 'paid' ? false : 5000),
  });

  const current = status.data ?? payment;
  const paid = current?.status === 'paid';

  React.useEffect(() => {
    if (paid) queryClient.invalidateQueries({ queryKey: ['billing-me'] });
  }, [paid, queryClient]);

  const simulate = useMutation({
    mutationFn: () => api<Payment>('/billing/dev/simulate-payment/', { method: 'POST', body: { txid: current!.txid } }),
    onSuccess: (data) => setPayment(data),
  });

  async function copyCode() {
    await Clipboard.setStringAsync(current!.pix_copy_paste);
    setCopied(true);
    setTimeout(() => setCopied(false), 3000);
  }

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
        <View style={{ alignItems: 'center', marginVertical: spacing.lg, padding: spacing.md, backgroundColor: '#fff', borderRadius: radius.md }}>
          <QRCode value={current.pix_copy_paste} size={220} />
        </View>
        <Body>1. Abra o aplicativo do seu banco.{'\n'}2. Escolha pagar com PIX e leia o QR Code, ou use o código copia e cola.{'\n'}3. Volte aqui: a confirmação aparece sozinha.</Body>
        <View style={{ height: spacing.md }} />
        <Button title={copied ? 'Código copiado!' : 'Copiar código PIX'} onPress={copyCode} />
        <Banner kind="info">Aguardando o pagamento... Esta cobrança vale por 24 horas.</Banner>
        {__DEV__ ? (
          <Button title="Simular pagamento (só em desenvolvimento)" variant="outline" onPress={() => simulate.mutate()} loading={simulate.isPending} />
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

      {methods.data?.map((item) => {
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
                  {selected ? '● ' : '○ '}{item.title}
                </Text>
                {item.recommended ? (
                  <Text style={{ backgroundColor: colors.accent, color: '#fff', fontWeight: '700', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 999, overflow: 'hidden' }}>
                    Recomendado
                  </Text>
                ) : null}
              </View>
              <Body muted>{item.description}</Body>
              {!item.available ? <Body>Em breve no aplicativo.</Body> : null}
            </Card>
          </Pressable>
        );
      })}

      {createCharge.isError ? <Banner kind="error">{messageOf(createCharge.error)}</Banner> : null}
      <Button title="Gerar PIX" onPress={() => createCharge.mutate()} loading={createCharge.isPending} disabled={method !== 'pix_manual'} />
      <Button title="Voltar" variant="ghost" onPress={() => router.back()} />
    </Screen>
  );
}