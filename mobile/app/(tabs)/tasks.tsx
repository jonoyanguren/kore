import { useCallback, useState } from 'react'
import { Pressable, Text, View } from 'react-native'
import { useFocusEffect } from 'expo-router'

import { Card, Err, Loading, Muted, Screen } from '@/components/ui'
import { useColorScheme } from '@/components/useColorScheme'
import Colors from '@/constants/Colors'
import { apiCompleteTask, apiTasks } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import type { Task } from '@/lib/types'

const STATUS: Record<string, string> = {
  open: 'Pendiente',
  in_progress: 'En curso',
  done: 'Hecha',
  cancelled: 'Cancelada',
}

export default function TasksScreen() {
  const colors = Colors[useColorScheme()]
  const { token } = useAuth()
  const [tasks, setTasks] = useState<Task[]>([])
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [busyId, setBusyId] = useState<number | null>(null)

  const load = useCallback(async () => {
    if (!token) return
    try {
      setErr(null)
      const all = await apiTasks(token, 'all')
      setTasks(
        all.filter((t) => t.status === 'open' || t.status === 'in_progress'),
      )
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

  async function complete(id: number) {
    if (!token || busyId) return
    setBusyId(id)
    try {
      await apiCompleteTask(token, id)
      await load()
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e))
    } finally {
      setBusyId(null)
    }
  }

  if (loading && tasks.length === 0) return <Loading />

  return (
    <Screen
      refreshing={refreshing}
      onRefresh={() => {
        setRefreshing(true)
        void load()
      }}
    >
      <Text style={{ fontSize: 28, fontWeight: '600', color: colors.text }}>
        Tareas
      </Text>
      {err ? <Err message={err} /> : null}
      {tasks.length === 0 ? <Muted>Nada abierto</Muted> : null}
      {tasks.map((t) => (
        <Card key={t.id}>
          <View
            style={{
              flexDirection: 'row',
              justifyContent: 'space-between',
              gap: 10,
              alignItems: 'flex-start',
            }}
          >
            <View style={{ flex: 1, gap: 4 }}>
              <Text style={{ color: colors.text, fontWeight: '600', fontSize: 16 }}>
                {t.title}
              </Text>
              <Muted>
                {STATUS[t.status] || t.status}
                {t.project ? ` · ${t.project}` : ''}
              </Muted>
            </View>
            <Pressable
              onPress={() => void complete(t.id)}
              disabled={busyId === t.id}
              style={{
                paddingHorizontal: 12,
                paddingVertical: 8,
                borderRadius: 8,
                backgroundColor: colors.tint,
                opacity: busyId === t.id ? 0.5 : 1,
              }}
            >
              <Text style={{ color: '#fff', fontWeight: '600' }}>Hecha</Text>
            </Pressable>
          </View>
        </Card>
      ))}
    </Screen>
  )
}
