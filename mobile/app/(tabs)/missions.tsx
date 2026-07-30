import { useCallback, useState } from 'react'
import { Pressable, Text } from 'react-native'
import { Link, useFocusEffect } from 'expo-router'

import { Card, Err, Loading, Muted, Screen } from '@/components/ui'
import { useColorScheme } from '@/components/useColorScheme'
import Colors from '@/constants/Colors'
import { apiMissions } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import type { Mission } from '@/lib/types'

const STATUS: Record<string, string> = {
  draft: 'Borrador',
  clarifying: 'Aclarando',
  queued: 'En cola',
  running: 'Corriendo',
  waiting: 'Esperando',
  done: 'Hecha',
  failed: 'Falló',
  cancelled: 'Cancelada',
}

export default function MissionsScreen() {
  const colors = Colors[useColorScheme()]
  const { token } = useAuth()
  const [missions, setMissions] = useState<Mission[]>([])
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const load = useCallback(async () => {
    if (!token) return
    try {
      setErr(null)
      setMissions(await apiMissions(token))
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

  if (loading && missions.length === 0) return <Loading />

  return (
    <Screen
      refreshing={refreshing}
      onRefresh={() => {
        setRefreshing(true)
        void load()
      }}
    >
      <Text style={{ fontSize: 28, fontWeight: '600', color: colors.text }}>
        Misiones
      </Text>
      {err ? <Err message={err} /> : null}
      {missions.length === 0 ? <Muted>Ninguna misión</Muted> : null}
      {missions.map((m) => (
        <Link key={m.id} href={`/mission/${m.id}`} asChild>
          <Pressable>
            <Card>
              <Text style={{ color: colors.text, fontWeight: '600', fontSize: 16 }}>
                {m.title}
              </Text>
              <Muted>
                {STATUS[m.status] || m.status}
                {m.quality === 'pro' ? ' · Pro' : ' · Normal'}
                {m.plan?.total
                  ? ` · ${m.plan.completed}/${m.plan.total}`
                  : ''}
              </Muted>
            </Card>
          </Pressable>
        </Link>
      ))}
    </Screen>
  )
}
