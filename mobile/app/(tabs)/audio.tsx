import { useCallback, useState } from 'react'
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native'
import { useFocusEffect } from 'expo-router'
import { SafeAreaView } from 'react-native-safe-area-context'

import { Err, Muted } from '@/components/ui'
import { useColorScheme } from '@/components/useColorScheme'
import Colors from '@/constants/Colors'
import {
  apiAddDiary,
  apiChat,
  apiDiary,
  apiMessages,
} from '@/lib/api'
import { useAuth } from '@/lib/auth'
import type { ChatMessage, DiaryEntry } from '@/lib/types'

type Mode = 'notas' | 'chat'

export default function CaptureScreen() {
  const colors = Colors[useColorScheme()]
  const { token } = useAuth()
  const [mode, setMode] = useState<Mode>('notas')
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [notes, setNotes] = useState<DiaryEntry[]>([])
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [status, setStatus] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!token) return
    try {
      setErr(null)
      if (mode === 'notas') {
        const d = await apiDiary(token)
        setNotes([...d.entries].reverse())
      } else {
        const msgs = await apiMessages(token, 40)
        setMessages(msgs)
      }
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e))
    }
  }, [token, mode])

  useFocusEffect(
    useCallback(() => {
      void load()
    }, [load]),
  )

  async function onSend() {
    const t = text.trim()
    if (!t || !token || busy) return
    setBusy(true)
    setErr(null)
    setStatus(null)
    try {
      if (mode === 'notas') {
        await apiAddDiary(token, t)
        setText('')
        setStatus('Nota guardada en diario')
        await load()
      } else {
        setStatus('Pensando…')
        const { reply } = await apiChat(token, t)
        setText('')
        setStatus(null)
        await load()
        // Optimistic: ensure reply visible if list lags
        if (reply) {
          setMessages((prev) => [
            ...prev,
            { role: 'user', content: t },
            { role: 'assistant', content: reply },
          ])
          await load()
        }
      }
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e))
      setStatus(null)
    } finally {
      setBusy(false)
    }
  }

  return (
    <SafeAreaView
      style={{ flex: 1, backgroundColor: colors.background }}
      edges={['bottom']}
    >
      <View style={styles.modes}>
        <Pressable
          onPress={() => setMode('notas')}
          style={[
            styles.modeBtn,
            mode === 'notas' && { backgroundColor: colors.tint },
          ]}
        >
          <Text
            style={{
              color: mode === 'notas' ? '#fff' : colors.text,
              fontWeight: '600',
            }}
          >
            Notas
          </Text>
        </Pressable>
        <Pressable
          onPress={() => setMode('chat')}
          style={[
            styles.modeBtn,
            mode === 'chat' && { backgroundColor: colors.tint },
          ]}
        >
          <Text
            style={{
              color: mode === 'chat' ? '#fff' : colors.text,
              fontWeight: '600',
            }}
          >
            Chat
          </Text>
        </Pressable>
      </View>

      <View style={{ paddingHorizontal: 16, paddingBottom: 4, gap: 4 }}>
        <Muted>
          {mode === 'notas'
            ? 'Suelta el rollo → diario (sin respuesta). Voz en M2.'
            : 'Pregunta a Kore (mismo chat que la web).'}
        </Muted>
        {err ? <Err message={err} /> : null}
        {status ? <Muted>{status}</Muted> : null}
      </View>

      {mode === 'notas' ? (
        <FlatList
          style={{ flex: 1, marginTop: 8 }}
          data={notes}
          keyExtractor={(item) => String(item.id)}
          contentContainerStyle={{ paddingHorizontal: 16, paddingBottom: 12, gap: 8 }}
          ListEmptyComponent={<Muted>Sin notas hoy</Muted>}
          renderItem={({ item }) => (
            <View style={[styles.bubble, { backgroundColor: colors.card }]}>
              <Text style={{ color: colors.text, lineHeight: 20 }}>{item.text}</Text>
            </View>
          )}
        />
      ) : (
        <FlatList
          style={{ flex: 1, marginTop: 8 }}
          data={messages}
          keyExtractor={(item, i) => String(item.id ?? i)}
          contentContainerStyle={{ paddingHorizontal: 16, paddingBottom: 12, gap: 8 }}
          ListEmptyComponent={<Muted>Sin mensajes aún</Muted>}
          renderItem={({ item }) => {
            const mine = item.role === 'user'
            return (
              <View
                style={[
                  styles.bubble,
                  {
                    backgroundColor: mine ? colors.tint : colors.card,
                    alignSelf: mine ? 'flex-end' : 'flex-start',
                    maxWidth: '88%',
                  },
                ]}
              >
                <Text
                  style={{
                    color: mine ? '#fff' : colors.text,
                    lineHeight: 20,
                  }}
                >
                  {item.content}
                </Text>
              </View>
            )
          }}
        />
      )}

      <View style={[styles.composer, { borderTopColor: 'rgba(21,32,43,0.08)' }]}>
        <TextInput
          value={text}
          onChangeText={setText}
          placeholder={mode === 'notas' ? 'Cuéntale el rollo…' : 'Escribe a Kore…'}
          placeholderTextColor={colors.tabIconDefault}
          multiline
          style={[
            styles.input,
            {
              color: colors.text,
              backgroundColor: '#fff',
              borderColor: 'rgba(21,32,43,0.12)',
            },
          ]}
          editable={!busy}
        />
        <Pressable
          onPress={() => void onSend()}
          disabled={busy || !text.trim()}
          style={[
            styles.send,
            {
              backgroundColor: colors.tint,
              opacity: busy || !text.trim() ? 0.5 : 1,
            },
          ]}
        >
          {busy ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={{ color: '#fff', fontWeight: '600' }}>
              {mode === 'notas' ? 'Guardar' : 'Enviar'}
            </Text>
          )}
        </Pressable>
      </View>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  modes: {
    flexDirection: 'row',
    gap: 8,
    paddingHorizontal: 16,
    paddingTop: 8,
    paddingBottom: 4,
  },
  modeBtn: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: 'rgba(21,32,43,0.06)',
  },
  bubble: {
    borderRadius: 12,
    padding: 12,
  },
  composer: {
    flexDirection: 'row',
    gap: 8,
    alignItems: 'flex-end',
    padding: 12,
    borderTopWidth: 1,
  },
  input: {
    flex: 1,
    minHeight: 44,
    maxHeight: 120,
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 16,
  },
  send: {
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 12,
    minWidth: 84,
    alignItems: 'center',
  },
})
