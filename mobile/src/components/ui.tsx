import { Ionicons } from '@expo/vector-icons';
import React, { useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TextInputProps,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { colors, font, radius, spacing } from '../theme';

export function Screen({ children, scroll = true }: { children: React.ReactNode; scroll?: boolean }) {
  const content = scroll ? (
    <ScrollView
      contentContainerStyle={styles.screenContent}
      keyboardShouldPersistTaps="handled"
      showsVerticalScrollIndicator={false}>
      {children}
    </ScrollView>
  ) : (
    <View style={styles.screenContent}>{children}</View>
  );
  return (
    <SafeAreaView style={styles.screen} edges={['top']}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        {content}
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

export function Title({ children }: { children: React.ReactNode }) {
  return <Text style={styles.title}>{children}</Text>;
}

export function Body({ children, muted }: { children: React.ReactNode; muted?: boolean }) {
  return <Text style={[styles.body, muted && { color: colors.muted }]}>{children}</Text>;
}

export function Card({ children }: { children: React.ReactNode }) {
  return <View style={styles.card}>{children}</View>;
}

type ButtonProps = {
  title: string;
  onPress: () => void;
  variant?: 'primary' | 'outline' | 'ghost';
  loading?: boolean;
  disabled?: boolean;
};

export function Button({ title, onPress, variant = 'primary', loading, disabled }: ButtonProps) {
  const inactive = disabled || loading;
  return (
    <Pressable
      accessibilityRole="button"
      onPress={onPress}
      disabled={inactive}
      style={({ pressed }) => [
        styles.button,
        variant === 'primary' && { backgroundColor: colors.primary },
        variant === 'outline' && { borderWidth: 2, borderColor: colors.primary },
        variant === 'ghost' && { backgroundColor: 'transparent' },
        inactive && { opacity: 0.5 },
        pressed && { opacity: 0.8 },
      ]}>
      {loading ? (
        <ActivityIndicator color={variant === 'primary' ? '#fff' : colors.primary} />
      ) : (
        <Text style={[styles.buttonText, variant !== 'primary' && { color: colors.primary }]}>{title}</Text>
      )}
    </Pressable>
  );
}

type FieldProps = TextInputProps & { label: string; hint?: string; error?: string | null };

export function Field({ label, hint, error, ...inputProps }: FieldProps) {
  return (
    <View style={{ marginBottom: spacing.md }}>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        placeholderTextColor={colors.muted}
        style={[styles.input, !!error && { borderColor: colors.danger }]}
        {...inputProps}
      />
      {hint && !error ? <Text style={styles.hint}>{hint}</Text> : null}
      {error ? <Text style={[styles.hint, { color: colors.danger }]}>{error}</Text> : null}
    </View>
  );
}

type Option = { value: string; label: string };

export function Select({
  label,
  value,
  options,
  onChange,
  placeholder = 'Toque para escolher',
}: {
  label: string;
  value: string;
  options: Option[];
  onChange: (value: string) => void;
  placeholder?: string;
}) {
  const [open, setOpen] = useState(false);
  const selected = options.find((option) => option.value === value);
  return (
    <View style={{ marginBottom: spacing.md }}>
      <Text style={styles.label}>{label}</Text>
      <Pressable style={[styles.input, styles.select]} onPress={() => setOpen(true)}>
        <Text style={{ fontSize: font.body, color: selected ? colors.text : colors.muted }}>
          {selected ? selected.label : placeholder}
        </Text>
        <Ionicons name="chevron-down" size={20} color={colors.muted} />
      </Pressable>
      <Modal visible={open} animationType="slide" transparent onRequestClose={() => setOpen(false)}>
        <View style={styles.modalBackdrop}>
          <View style={styles.modalSheet}>
            <Text style={[styles.title, { fontSize: font.large, marginBottom: spacing.sm }]}>{label}</Text>
            <FlatList
              data={options}
              keyExtractor={(item) => item.value}
              renderItem={({ item }) => (
                <Pressable
                  style={styles.option}
                  onPress={() => {
                    onChange(item.value);
                    setOpen(false);
                  }}>
                  <Text style={{ fontSize: font.body, color: colors.text }}>{item.label}</Text>
                  {item.value === value ? <Ionicons name="checkmark" size={22} color={colors.primary} /> : null}
                </Pressable>
              )}
            />
            <Button title="Fechar" variant="outline" onPress={() => setOpen(false)} />
          </View>
        </View>
      </Modal>
    </View>
  );
}

export function Checkbox({ checked, onToggle, label }: { checked: boolean; onToggle: () => void; label: string }) {
  return (
    <Pressable style={styles.checkbox} onPress={onToggle} accessibilityRole="checkbox">
      <Ionicons name={checked ? 'checkbox' : 'square-outline'} size={28} color={colors.primary} />
      <Text style={[styles.body, { flex: 1 }]}>{label}</Text>
    </Pressable>
  );
}

export function Banner({ kind, children }: { kind: 'info' | 'error' | 'success'; children: React.ReactNode }) {
  const background = kind === 'error' ? colors.errorBg : kind === 'success' ? colors.successBg : colors.infoBg;
  const color = kind === 'error' ? colors.danger : kind === 'success' ? colors.success : colors.primaryDark;
  return (
    <View style={[styles.banner, { backgroundColor: background }]}>
      <Text style={{ fontSize: font.body, color }}>{children}</Text>
    </View>
  );
}

export function Loading() {
  return (
    <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.background }}>
      <ActivityIndicator size="large" color={colors.primary} />
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background },
  screenContent: { padding: spacing.md, paddingBottom: spacing.xl },
  title: { fontSize: font.title, fontWeight: '700', color: colors.text, marginBottom: spacing.sm },
  body: { fontSize: font.body, color: colors.text, lineHeight: 24 },
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    padding: spacing.md,
    marginBottom: spacing.md,
    borderWidth: 1,
    borderColor: colors.border,
  },
  button: {
    minHeight: 54,
    borderRadius: radius.md,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing.md,
    marginBottom: spacing.sm,
  },
  buttonText: { color: '#fff', fontSize: font.large, fontWeight: '700' },
  label: { fontSize: font.body, fontWeight: '600', color: colors.text, marginBottom: spacing.xs },
  input: {
    minHeight: 52,
    borderWidth: 1.5,
    borderColor: colors.border,
    borderRadius: radius.md,
    paddingHorizontal: spacing.md,
    fontSize: font.body,
    color: colors.text,
    backgroundColor: colors.surface,
  },
  select: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  hint: { fontSize: font.small, color: colors.muted, marginTop: spacing.xs },
  modalBackdrop: { flex: 1, backgroundColor: 'rgba(0,0,0,0.4)', justifyContent: 'flex-end' },
  modalSheet: {
    backgroundColor: colors.surface,
    borderTopLeftRadius: radius.lg,
    borderTopRightRadius: radius.lg,
    padding: spacing.md,
    maxHeight: '75%',
  },
  option: {
    minHeight: 52,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  checkbox: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm, marginVertical: spacing.sm },
  banner: { borderRadius: radius.md, padding: spacing.md, marginBottom: spacing.md },
});