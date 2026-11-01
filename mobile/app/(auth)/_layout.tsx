import { Redirect, Stack } from 'expo-router';
import React from 'react';

import { Loading } from '../../src/components/ui';
import { useAuth } from '../../src/lib/auth';

export default function AuthLayout() {
  const { user, loading } = useAuth();
  if (loading) return <Loading />;
  if (user) return <Redirect href="/home" />;
  return <Stack screenOptions={{ headerShown: false }} />;
}