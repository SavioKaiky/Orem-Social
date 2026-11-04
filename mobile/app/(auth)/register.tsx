import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'expo-router';
import React, { useState } from 'react';
import { ScrollView, Text, View } from 'react-native';

import {
  Banner,
  Body,
  Button,
  Card,
  Checkbox,
  Field,
  Screen,
  Select,
  Title,
} from '../../src/components/ui';
import { api, messageOf } from '../../src/lib/api';
import { useAuth } from '../../src/lib/auth';
import {
  dateBrToIso,
  digits,
  formatMoney,
  maskCpf,
  maskDate,
  maskPhone,
} from '../../src/lib/format';
import { Pricing, Terms } from '../../src/lib/types';
import { colors, radius, spacing } from '../../src/theme';

const STATES: [string, string][] = [
  ['AC', 'Acre'], ['AL', 'Alagoas'], ['AP', 'Amapá'], ['AM', 'Amazonas'], ['BA', 'Bahia'],
  ['CE', 'Ceará'], ['DF', 'Distrito Federal'], ['ES', 'Espírito Santo'], ['GO', 'Goiás'],
  ['MA', 'Maranhão'], ['MT', 'Mato Grosso'], ['MS', 'Mato Grosso do Sul'], ['MG', 'Minas Gerais'],
  ['PA', 'Pará'], ['PB', 'Paraíba'], ['PR', 'Paraná'], ['PE', 'Pernambuco'], ['PI', 'Piauí'],
  ['RJ', 'Rio de Janeiro'], ['RN', 'Rio Grande do Norte'], ['RS', 'Rio Grande do Sul'],
  ['RO', 'Rondônia'], ['RR', 'Roraima'], ['SC', 'Santa Catarina'], ['SP', 'São Paulo'],
  ['SE', 'Sergipe'], ['TO', 'Tocantins'],
];
const STATE_OPTIONS = STATES.map(([value, label]) => ({ value, label: `${label} (${value})` }));

const RELATIONSHIPS = [
  { value: 'spouse', label: 'Cônjuge' },
  { value: 'child', label: 'Filho(a)' },
  { value: 'parent', label: 'Pai/Mãe' },
  { value: 'parent_in_law', label: 'Sogro(a)' },
  { value: 'other', label: 'Outro' },
];
const relationshipLabel = (value: string) => RELATIONSHIPS.find((r) => r.value === value)?.label ?? value;

type DependentDraft = { full_name: string; birth_date: string; cpf: string; relationship: string };
const emptyDependent: DependentDraft = { full_name: '', birth_date: '', cpf: '', relationship: '' };

export default function RegisterScreen() {
  const router = useRouter();
  const { login } = useAuth();
  const [step, setStep] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const [form, setForm] = useState({
    full_name: '', cpf: '', birth_date: '', phone: '', email: '',
    password: '', confirm: '', city: '', state: '', worker_code: '',
  });
  const set = (key: keyof typeof form) => (value: string) => setForm((prev) => ({ ...prev, [key]: value }));

  const [dependents, setDependents] = useState<DependentDraft[]>([]);
  const [draft, setDraft] = useState<DependentDraft>(emptyDependent);
  const [adding, setAdding] = useState(false);
  const [accepted, setAccepted] = useState(false);

  const terms = useQuery({
    queryKey: ['terms'],
    queryFn: () => api<Terms>('/terms/current/', { auth: false }),
    enabled: step === 3,
  });
  const pricing = useQuery({
    queryKey: ['pricing'],
    queryFn: () => api<Pricing>('/billing/pricing/', { auth: false }),
    enabled: step === 3,
  });

  function validateStep1(): string | null {
    if (form.full_name.trim().split(/\s+/).length < 2) return 'Informe seu nome completo.';
    if (digits(form.cpf).length !== 11) return 'Informe um CPF com 11 números.';
    if (!dateBrToIso(form.birth_date)) return 'Informe uma data de nascimento válida (dia/mês/ano).';
    if (digits(form.phone).length < 10) return 'Informe um telefone com DDD.';
    if (!form.email.trim()) return 'Informe seu e-mail.';
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) return 'Informe um e-mail válido.';
    if (form.password.length < 8) return 'A senha precisa ter pelo menos 8 caracteres.';
    if (form.password !== form.confirm) return 'As senhas não são iguais.';
    return null;
  }

  function validateStep2(): string | null {
    if (!form.city.trim()) return 'Informe sua cidade.';
    if (!form.state) return 'Escolha seu estado.';
    if (!form.worker_code.trim()) return 'Informe o código do obreiro que indicou você.';
    return null;
  }

  function next() {
    const problem = step === 1 ? validateStep1() : validateStep2();
    setError(problem);
    if (!problem) setStep(step + 1);
  }

  function saveDependent() {
    if (draft.full_name.trim().split(/\s+/).length < 2) return setError('Informe o nome completo do dependente.');
    if (!dateBrToIso(draft.birth_date)) return setError('Informe uma data de nascimento válida para o dependente.');
    if (!draft.relationship) return setError('Escolha o parentesco do dependente.');
    if (draft.cpf && digits(draft.cpf).length !== 11) return setError('O CPF do dependente precisa ter 11 números.');
    setError(null);
    setDependents((prev) => [...prev, draft]);
    setDraft(emptyDependent);
    setAdding(false);
  }

  async function submit() {
    if (!accepted) return setError('Para criar a conta, aceite os Termos de Uso.');
    setError(null);
    setLoading(true);
    try {
      await api('/beneficiaries/register/', {
        method: 'POST',
        auth: false,
        body: {
          cpf: digits(form.cpf),
          full_name: form.full_name.trim(),
          email: form.email.trim(),
          phone: digits(form.phone),
          password: form.password,
          birth_date: dateBrToIso(form.birth_date),
          city: form.city.trim(),
          state: form.state,
          worker_code: form.worker_code.trim().toUpperCase(),
          accept_terms: accepted,
          dependents: dependents.map((d) => ({
            full_name: d.full_name.trim(),
            birth_date: dateBrToIso(d.birth_date),
            relationship: d.relationship,
            ...(digits(d.cpf) ? { cpf: digits(d.cpf) } : {}),
          })),
        },
      });
      // Conta criada: entra direto, e o layout leva para o início
      await login(form.cpf, form.password);
    } catch (e) {
      setError(messageOf(e));
    } finally {
      setLoading(false);
    }
  }

  const monthly = pricing.data
    ? Number(pricing.data.holder_amount) + dependents.length * Number(pricing.data.dependent_amount)
    : null;

  return (
    <Screen>
      <Text style={{ color: colors.muted, fontSize: 14, marginBottom: spacing.xs }}>Passo {step} de 3</Text>
      {error ? <Banner kind="error">{error}</Banner> : null}

      {step === 1 && (
        <>
          <Title>Seus dados</Title>
          <Field label="Nome completo" value={form.full_name} onChangeText={set('full_name')} autoCapitalize="words" />
          <Field label="CPF" value={form.cpf} onChangeText={(t) => set('cpf')(maskCpf(t))} keyboardType="number-pad" placeholder="000.000.000-00" />
          <Field label="Data de nascimento" value={form.birth_date} onChangeText={(t) => set('birth_date')(maskDate(t))} keyboardType="number-pad" placeholder="DD/MM/AAAA" />
          <Field label="Telefone (com DDD)" value={form.phone} onChangeText={(t) => set('phone')(maskPhone(t))} keyboardType="number-pad" placeholder="(62) 99999-0000" />
          <Field label="E-mail" value={form.email} onChangeText={set('email')} keyboardType="email-address" autoCapitalize="none" />
          <Field label="Crie uma senha" value={form.password} onChangeText={set('password')} secureTextEntry hint="Mínimo de 8 caracteres." />
          <Field label="Repita a senha" value={form.confirm} onChangeText={set('confirm')} secureTextEntry />
          <Button title="Continuar" onPress={next} />
          <Button title="Já tenho conta" variant="ghost" onPress={() => router.back()} />
        </>
      )}

      {step === 2 && (
        <>
          <Title>Onde você mora</Title>
          <Field label="Cidade" value={form.city} onChangeText={set('city')} autoCapitalize="words" />
          <Select label="Estado" value={form.state} options={STATE_OPTIONS} onChange={set('state')} />
          <Field
            label="Código do obreiro"
            value={form.worker_code}
            onChangeText={(t) => set('worker_code')(t.toUpperCase())}
            autoCapitalize="characters"
            placeholder="Ex.: OBR-01"
            hint="A adesão é por indicação. Peça o código ao obreiro que convidou você."
          />
          <Button title="Continuar" onPress={next} />
          <Button title="Voltar" variant="ghost" onPress={() => { setError(null); setStep(1); }} />
        </>
      )}

      {step === 3 && (
        <>
          <Title>Dependentes e termos</Title>
          <Body muted>Adicione quem fará parte do seu grupo familiar. Você pode pular e incluir depois.</Body>
          <View style={{ height: spacing.md }} />

          {dependents.map((dependent, index) => (
            <Card key={`${dependent.full_name}-${index}`}>
              <Text style={{ fontSize: 17, fontWeight: '700', color: colors.text }}>{dependent.full_name}</Text>
              <Body muted>{relationshipLabel(dependent.relationship)} · nascimento {dependent.birth_date}</Body>
              <Button
                title="Remover"
                variant="ghost"
                onPress={() => setDependents((prev) => prev.filter((_, i) => i !== index))}
              />
            </Card>
          ))}

          {adding ? (
            <Card>
              <Field label="Nome completo do dependente" value={draft.full_name} onChangeText={(t) => setDraft({ ...draft, full_name: t })} autoCapitalize="words" />
              <Field label="Data de nascimento" value={draft.birth_date} onChangeText={(t) => setDraft({ ...draft, birth_date: maskDate(t) })} keyboardType="number-pad" placeholder="DD/MM/AAAA" />
              <Select label="Parentesco" value={draft.relationship} options={RELATIONSHIPS} onChange={(v) => setDraft({ ...draft, relationship: v })} />
              <Field label="CPF (opcional)" value={draft.cpf} onChangeText={(t) => setDraft({ ...draft, cpf: maskCpf(t) })} keyboardType="number-pad" hint="Crianças pequenas podem não ter CPF." />
              <Button title="Salvar dependente" onPress={saveDependent} />
              <Button title="Cancelar" variant="ghost" onPress={() => { setAdding(false); setDraft(emptyDependent); setError(null); }} />
            </Card>
          ) : (
            <Button title="Adicionar dependente" variant="outline" onPress={() => setAdding(true)} />
          )}

          {monthly !== null && (
            <Banner kind="info">
              Sua contribuição mensal será de {formatMoney(monthly)} (você + {dependents.length} dependente(s)).
            </Banner>
          )}

          <Title>Termos de Uso</Title>
          {terms.isLoading ? <Body muted>Carregando os termos...</Body> : null}
          {terms.data ? (
            <View style={{ borderWidth: 1, borderColor: colors.border, borderRadius: radius.md, backgroundColor: colors.surface, maxHeight: 220 }}>
              <ScrollView nestedScrollEnabled contentContainerStyle={{ padding: spacing.md }}>
                <Body>{terms.data.content}</Body>
              </ScrollView>
            </View>
          ) : null}
          {terms.isError ? (
            <>
            <Banner kind="error">Não foi possível carregar os termos. Verifique a conexão.</Banner>
            <Button title="Tentar novamente" variant="outline" onPress={() => terms.refetch()} />
            </>
          ) : null}
          <Checkbox checked={accepted} onToggle={() => setAccepted(!accepted)} label="Li e aceito os Termos de Uso. Sei que a adesão é voluntária e que posso sair quando quiser." />

          <Button title="Concluir cadastro" onPress={submit} loading={loading} disabled={!terms.data || adding} />
          <Button title="Voltar" variant="ghost" onPress={() => { setError(null); setStep(2); }} />
        </>
      )}
    </Screen>
  );
}