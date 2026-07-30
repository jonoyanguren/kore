import { useCallback, useState } from 'react'
import { Text, View } from 'react-native'
import { useFocusEffect } from 'expo-router'

import { Card, Err, Loading, Muted, Screen } from '@/components/ui'
import { useColorScheme } from '@/components/useColorScheme'
import Colors from '@/constants/Colors'
import { apiDay } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import type { DaySnapshot } from '@/lib/types'

export default function DayScreen() {
  const colors = Colors[useColorScheme()]
  const { token } = useAuth()
  const [data, setData] = useState<DaySnapshot | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const load = useCallback(async () => {
    if (!token) return
    try {
      setErr(null)
      setData(await apiDay(token))
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [token])

  useFocusEffect(
    useCallback(() => {
      setLoading(true)
      void load()
    }, [load]),
  )

  if (loading && !data) return <Loading />

  return (
    <Screen
      refreshing={refreshing}
      onRefresh={() => {
        setRefreshing(true)
        void load()
      }}
    >
      {err ? <Err message={err} /> : null}
      {data ? (
        <>
          <Text style={{ fontSize: 28, fontWeight: '600', color: colors.text }}>
            {data.greeting}
          </Text>
          <Muted>
            {data.headline} · {data.clock}
          </Muted>

          <Card>
            <Text style={{ fontWeight: '600', color: colors.text }}>Tareas</Text>
            <Muted>
              {data.tasks.in_progress} en curso · {data.tasks.open} pendientes
            </Muted>
          </Card>

          {data.dream?.excerpt ? (
            <Card>
              <Text style={{ fontWeight: '600', color: colors.text }}>Dream</Text>
              <Muted>{data.dream.excerpt}</Muted>
            </Card>
          ) : null}

          {data.briefing.summary?.length ? (
            <Card>
              <Text style={{ fontWeight: '600', color: colors.text }}>Resumen</Text>
              {data.briefing.summary.slice(0, 5).map((line, i) => (
                <Muted key={i}>• {line}</Muted>
              ))}
            </Card>
          ) : null}

          {data.briefing.help?.length ? (
            <Card>
              <Text style={{ fontWeight: '600', color: colors.text }}>Ayuda</Text>
              {data.briefing.help.slice(0, 4).map((line, i) => (
                <Muted key={i}>• {line}</Muted>
              ))}
            </Card>
          ) : null}

          {data.agenda?.length ? (
            <Card>
              <Text style={{ fontWeight: '600', color: colors.text }}>Agenda</Text>
              {data.agenda.slice(0, 6).map((a) => (
                <Muted key={a.id}>
                  {a.starts_at.slice(11, 16)} · {a.title}
                </Muted>
              ))}
            </Card>
          ) : null}

          {data.inbox?.connected ? (
            <Card>
              <Text style={{ fontWeight: '600', color: colors.text }}>Inbox</Text>
              <Muted>
                {data.inbox.messages.length} unread
                {data.inbox.error ? ` · ${data.inbox.error}` : ''}
              </Muted>
              {data.inbox.messages.slice(0, 3).map((m) => (
                <View key={m.id} style={{ marginTop: 6 }}>
                  <Text style={{ color: colors.text, fontWeight: '500' }}>
                    {m.subject || '(sin asunto)'}
                  </Text>
                  <Muted>{m.from}</Muted>
                </View>
              ))}
            </Card>
          ) : null}
        </>
      ) : null}
    </Screen>
  )
}
