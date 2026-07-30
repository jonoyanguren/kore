import { useState } from 'react'
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'

import { useColorScheme } from '@/components/useColorScheme'
import Colors from '@/constants/Colors'
import { API_BASE } from '@/lib/config'
import { useAuth } from '@/lib/auth'

export default function LoginScreen() {
  const colors = Colors[useColorScheme() ?? 'light']
  const { login } = useAuth()
  const [secret, setSecret] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function onSubmit() {
    if (!secret.trim() || busy) return
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
    <SafeAreaView style={[styles.root, { backgroundColor: colors.background }]}>
      <View style={styles.inner}>
        <Text style={[styles.brand, { color: colors.tint }]}>Kore</Text>
        <Text style={[styles.lede, { color: colors.muted }]}>
          Mismo secret que la web
        </Text>

        {/* Bare TextInput — no Pressable/ScrollView parents (steal focus on iOS). */}
        <TextInput
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
          spellCheck={false}
          style={[
            styles.input,
            {
              color: colors.text,
              borderColor: 'rgba(21,32,43,0.18)',
              backgroundColor: '#ffffff',
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
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  inner: {
    flex: 1,
    justifyContent: 'center',
    paddingHorizontal: 24,
  },
  brand: { fontSize: 32, fontWeight: '600', marginBottom: 8 },
  lede: { fontSize: 15, marginBottom: 20 },
  input: {
    borderWidth: 1,
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 14,
    fontSize: 17,
    minHeight: 52,
  },
  btn: {
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 16,
  },
  btnText: { color: '#fff', fontSize: 16, fontWeight: '600' },
  error: { fontSize: 14, marginTop: 10 },
  hint: { fontSize: 12, marginTop: 10 },
})
