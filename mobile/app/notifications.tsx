import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Redirect, useRouter } from 'expo-router';
import React, { useEffect, useState } from 'react';
import { Pressable, Text, View } from 'react-native';

import { Banner, Body, Button, Card, Loading, Screen, Title } from '../src/components/ui';
import { api, messageOf } from '../src/lib/api';
import { useAuth } from '../src/lib/auth';
import { Notification, Paginated } from '../src/lib/types';
import { colors, font, spacing } from '../src/theme';

export default function NotificationsScreen() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [items, setItems] = useState<Notification[]>([]);

  const notifications = useQuery({
    queryKey: ['billing-notifications', page],
    queryFn: () => api<Paginated<Notification>>(`/billing/notifications/?page=${page}`),
    enabled: user?.role === 'beneficiary',
  });

  const markAllRead = useMutation({
    mutationFn: () => api<{ updated: number }>('/billing/notifications/mark-all-read/', { method: 'POST' }),
    onSuccess: () => {
      const readAt = new Date().toISOString();
      setItems((current) => current.map((item) => ({ ...item, read_at: item.read_at ?? readAt })));
      queryClient.invalidateQueries({ queryKey: ['billing-notifications'] });
    },
  });

  useEffect(() => {
    if (user?.role === 'beneficiary') markAllRead.mutate();
  }, [user?.role]);

  useEffect(() => {
    if (!notifications.data) return;
    setItems((current) =>
      page === 1 ? notifications.data.results : [...current, ...notifications.data.results],
    );
  }, [notifications.data, page]);

  if (loading) return <Loading />;
  if (!user) return <Redirect href="/login" />;
  if (user.role !== 'beneficiary') return <Redirect href="/(app)/home" />;

  return (
    <Screen>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: spacing.sm }}>
        <Pressable accessibilityRole="button" accessibilityLabel="Voltar" onPress={() => router.back()} style={{ padding: 6 }}>
          <Text style={{ fontSize: 22, color: colors.primary }}>‹</Text>
        </Pressable>
        <Title>Notificações</Title>
      </View>

      {notifications.isError ? <Banner kind="error">{messageOf(notifications.error)}</Banner> : null}
      {markAllRead.isError ? <Banner kind="error">{messageOf(markAllRead.error)}</Banner> : null}
      {notifications.isLoading && items.length === 0 ? <Loading /> : null}

      {items.length === 0 && !notifications.isLoading ? (
        <Card><Body>Você ainda não tem notificações.</Body></Card>
      ) : (
        items.map((notification) => (
          <Card key={notification.id}>
            <Text style={{ fontSize: font.body, fontWeight: '700', color: colors.text }}>
              {notification.title}
            </Text>
            <Body>{notification.body}</Body>
            {!notification.read_at ? <Body muted>Não lida</Body> : null}
          </Card>
        ))
      )}

      {notifications.data?.next ? (
        <Button
          title="Carregar mais"
          variant="outline"
          loading={notifications.isFetching}
          onPress={() => setPage((current) => current + 1)}
        />
      ) : null}
    </Screen>
  );
}
