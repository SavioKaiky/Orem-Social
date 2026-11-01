import { Redirect } from 'expo-router';
import React from 'react';

import { Loading } from '../src/components/ui';
import { useAuth } from '../src/lib/auth';

// Porta de entrada: decide para onde ir conforme o usuário esteja logado ou não
export default function Index() {
  const { user, loading } = useAuth();
  if (loading) return <Loading />;
  return <Redirect href={user ? '/home' : '/login'} />;
}