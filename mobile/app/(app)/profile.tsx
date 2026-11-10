import React from 'react';
import { Alert, Linking } from 'react-native';

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

const PRIVACY_EMAIL = 'saviokaikylopes@kaiky.org';

const DELETION_SUBJECT = 'Excluir conta';
const DELETION_MESSAGE = [
  'Olá, equipe Orem Social.',
  'Solicito a exclusão da minha conta de beneficiário e dos dados pessoais vinculados a ela.',
  'Por favor, me orientem sobre como confirmar minha identidade e me avisem quando o pedido for concluído.',
  'Obrigado.',
].join('\n\n');

async function requestAccountDeletion() {
  const subject = encodeURIComponent(DELETION_SUBJECT);
  const body = encodeURIComponent(DELETION_MESSAGE);
  try {
    await Linking.openURL(`mailto:${PRIVACY_EMAIL}?subject=${subject}&body=${body}`);
  } catch {
    Alert.alert('Solicitar exclusão da conta', `Envie um e-mail para ${PRIVACY_EMAIL} com o assunto “Excluir conta”.`);
  }
}

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
      {user.role === 'beneficiary' ? (
        <Card>
          <Body>Solicite a exclusão da sua conta por e-mail. A equipe confirmará sua identidade antes de processar o pedido.</Body>
          <Button title="Solicitar exclusão da conta" variant="outline" onPress={requestAccountDeletion} />
        </Card>
      ) : null}
      <Button title="Sair da conta" variant="outline" onPress={logout} />
    </Screen>
  );
}