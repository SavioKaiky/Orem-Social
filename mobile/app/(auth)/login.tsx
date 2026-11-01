import { useRouter } from 'expo-router';
import React, { useState } from 'react';
import { Text, View } from 'react-native';

import { Banner, Body, Button, Field, Screen } from '../../src/components/ui';
import { ApiError, messageOf } from '../../src/lib/api';
import { useAuth } from '../../src/lib/auth';
import { digits, maskCpf } from '../../src/lib/format';
import { colors, font, spacing } from '../../src/theme';

export default function LoginScreen() {
  const { login } = useAuth();
  const router = useRouter();
  const [cpf, setCpf] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit() {
    setError(null);
    if (digits(cpf).length !== 11 || !password) {
      setError('Informe seu CPF e sua senha.');
      return;
    }
    setLoading(true);
    try {
      // Ao logar, o layout (auth) detecta o usuário e leva para o início
      await login(cpf, password);
    } catch (e) {
      setError(e instanceof ApiError && e.status === 401 ? 'CPF ou senha incorretos.' : messageOf(e));
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
        label="CPF"
        value={cpf}
        onChangeText={(text) => setCpf(maskCpf(text))}
        keyboardType="number-pad"
        placeholder="000.000.000-00"
      />
      <Field label="Senha" value={password} onChangeText={setPassword} secureTextEntry placeholder="Sua senha" />
      <Button title="Entrar" onPress={submit} loading={loading} />
      <Button title="Criar minha conta" variant="outline" onPress={() => router.push('/register')} />
    </Screen>
  );
}