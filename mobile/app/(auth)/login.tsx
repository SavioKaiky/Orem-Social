import { useRouter } from 'expo-router';
import React, { useState } from 'react';
import { Text, View } from 'react-native';

import { Banner, Body, Button, Field, Screen } from '../../src/components/ui';
import { ApiError, messageOf } from '../../src/lib/api';
import { useAuth } from '../../src/lib/auth';
import { digits } from '../../src/lib/format';
import { colors, font, spacing } from '../../src/theme';

export default function LoginScreen() {
  const { login } = useAuth();
  const router = useRouter();
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit() {
    setError(null);
    if (!digits(identifier) || !password) {
      setError('Informe seu CPF ou telefone e sua senha.');
      return;
    }
    setLoading(true);
    try {
      // Ao logar, o layout (auth) detecta o usuário e leva para o início
      await login(identifier, password);
    } catch (e) {
      setError(e instanceof ApiError && e.status === 401 ? 'CPF, telefone ou senha incorretos.' : messageOf(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <Screen>
      <View style={{ alignItems: 'center', marginVertical: spacing.xl }}>
        <Text style={{ fontSize: font.hero, fontWeight: '800', color: colors.primary }}>Orem Social</Text>
        <Body muted>Serviço Religioso Social da Igreja OREM</Body>
      </View>
      {error ? <Banner kind="error">{error}</Banner> : null}
      <Field
        label="CPF ou telefone"
        value={identifier}
        onChangeText={setIdentifier}
        keyboardType="number-pad"
        placeholder="CPF ou telefone com DDD"
      />
      <Field label="Senha" value={password} onChangeText={setPassword} secureTextEntry placeholder="Sua senha" />
      <Button title="Entrar" onPress={submit} loading={loading} />
      <Button title="Criar minha conta" variant="outline" onPress={() => router.push('/register')} />
    </Screen>
  );
}