import React from 'react';

import { Body, Button, Card, Loading, Screen, Title } from '../../src/components/ui';
import { useAuth } from '../../src/lib/auth';
import { maskCpf, maskPhone } from '../../src/lib/format';
import { Role } from '../../src/lib/types';

const ROLE_LABELS: Record<Role, string> = {
  admin: 'Administrador',
  bishop: 'Bispo Presidente',
  worker: 'Obreiro multiplicador',
  beneficiary: 'Beneficiário',
  provider: 'Prestador de serviço',
};

export default function ProfileScreen() {
  const { user, logout } = useAuth();
  if (!user) return <Loading />;

  return (
    <Screen>
      <Title>Meu perfil</Title>
      <Card>
        <Body>{user.full_name}</Body>
        <Body muted>{ROLE_LABELS[user.role]}</Body>
        <Body muted>CPF: {maskCpf(user.cpf)}</Body>
        {user.phone ? <Body muted>Telefone: {maskPhone(user.phone)}</Body> : null}
        {user.worker_code ? <Body muted>Seu código de obreiro: {user.worker_code}</Body> : null}
      </Card>
      <Button title="Sair da conta" variant="outline" onPress={logout} />
    </Screen>
  );
}