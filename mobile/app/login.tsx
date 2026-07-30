import { useRef, useState } from 'react'
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native'

import { useColorScheme } from '@/components/useColorScheme'
import Colors from '@/constants/Colors'
import { API_BASE } from '@/lib/config'
import { useAuth } from '@/lib/auth'

export default function LoginScreen() {
  const colorScheme = useColorScheme() ?? 'light'
  const colors = Colors[colorScheme]
  const { login } = useAuth()
  const [secret, setSecret] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<TextInput>(null)

  async function onSubmit() {
    setBusy(true)
    setError(null)
    try {
      await login(secret)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <KeyboardAvoidingView
      style={[styles.root, { backgroundColor: colors.background }]}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <ScrollView
        keyboardShouldPersistTaps="handled"
        keyboardDismissMode="on-drag"
        contentContainerStyle={styles.scroll}
        bounces={false}
      >
        <Pressable onPress={() => inputRef.current?.focus()}>
          <View style={[styles.card, { backgroundColor: colors.card }]}>
            <Text style={[styles.brand, { color: colors.tint }]}>Kore</Text>
            <Text style={[styles.lede, { color: colors.muted }]}>
              Consola móvil · mismo secret que la web
            </Text>
            <TextInput
              ref={inputRef}
              value={secret}
              onChangeText={setSecret}
              placeholder="CONSOLE_SECRET"
              placeholderTextColor={colors.tabIconDefault}
              secureTextEntry
              textContentType="password"
              autoComplete="password"
              autoCapitalize="none"
              autoCorrect={false}
              autoFocus
              editable={!busy}
              importantForAutofill="yes"
              style={[
                styles.input,
                {
                  color: colors.text,
                  borderColor: 'rgba(21,32,43,0.12)',
                  backgroundColor: '#fff',
                },
              ]}
              onSubmitEditing={() => void onSubmit()}
            />
            {error ? (
              <Text style={[styles.error, { color: colors.danger }]}>{error}</Text>
            ) : null}
            <Pressable
              onPress={() => void onSubmit()}
              disabled={busy || !secret.trim()}
              style={[
                styles.btn,
                {
                  backgroundColor: colors.tint,
                  opacity: busy || !secret.trim() ? 0.5 : 1,
                },
              ]}
            >
              {busy ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={styles.btnText}>Entrar</Text>
              )}
            </Pressable>
            <Text style={[styles.hint, { color: colors.muted }]}>{API_BASE}</Text>
          </View>
        </Pressable>
      </ScrollView>
    </KeyboardAvoidingView>
  )
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  scroll: {
    flexGrow: 1,
    justifyContent: 'center',
    padding: 24,
  },
  card: {
    borderRadius: 16,
    padding: 22,
    gap: 12,
    shadowColor: '#15202b',
    shadowOpacity: 0.06,
    shadowRadius: 16,
    shadowOffset: { width: 0, height: 8 },
  },
  brand: { fontSize: 32, fontWeight: '600', letterSpacing: -0.5 },
  lede: { fontSize: 15, marginBottom: 4 },
  input: {
    borderWidth: 1,
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 14,
    fontSize: 16,
    minHeight: 48,
  },
  btn: {
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 4,
  },
  btnText: { color: '#fff', fontSize: 16, fontWeight: '600' },
  error: { fontSize: 14 },
  hint: { fontSize: 12, marginTop: 4 },
})
