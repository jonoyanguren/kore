import { useCallback, useState } from 'react'
import { Text, View } from 'react-native'
import { Stack, useLocalSearchParams, useFocusEffect } from 'expo-router'

import { Card, Err, Loading, Muted, Screen } from '@/components/ui'
import { useColorScheme } from '@/components/useColorScheme'
import Colors from '@/constants/Colors'
import { apiMission } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { missionModeLabel, type Mission } from '@/lib/types'

export default function MissionDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>()
  const colors = Colors[useColorScheme()]
  const { token } = useAuth()
  const [mission, setMission] = useState<Mission | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    if (!token || !id) return
    try {
      setErr(null)
      setMission(await apiMission(token, Number(id)))
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }, [token, id])

  useFocusEffect(
    useCallback(() => {
      setLoading(true)
      void load()
    }, [load]),
  )

  return (
    <>
      <Stack.Screen options={{ title: mission?.title || 'Misión', headerShown: true }} />
      {loading && !mission ? (
        <Loading />
      ) : (
        <Screen
          refreshing={false}
          onRefresh={() => {
            void load()
          }}
        >
          {err ? <Err message={err} /> : null}
          {mission ? (
            <>
              <Muted>
                {mission.status}
                {` · ${missionModeLabel(mission)}`}
              </Muted>
              {mission.brief ? (
                <Card>
                  <Text style={{ fontWeight: '600', color: colors.text }}>Encargo</Text>
                  <Muted>{mission.brief}</Muted>
                </Card>
              ) : null}
              {mission.plan?.tasks?.length ? (
                <Card>
                  <Text style={{ fontWeight: '600', color: colors.text }}>Plan</Text>
                  {mission.plan.tasks.map((t, i) => (
                    <View key={`${i}-${t.title}`} style={{ marginTop: 6 }}>
                      <Text style={{ color: colors.text, fontWeight: '500' }}>
                        {t.status === 'done' ? '✓' : '○'} {t.title}
                      </Text>
                      <Muted>{t.goal}</Muted>
                    </View>
                  ))}
                </Card>
              ) : null}
              {mission.markdown ? (
                <Card>
                  <Text style={{ fontWeight: '600', color: colors.text }}>Informe</Text>
                  <Text
                    style={{
                      color: colors.text,
                      fontSize: 14,
                      lineHeight: 20,
                      marginTop: 6,
                    }}
                  >
                    {mission.markdown}
                  </Text>
                </Card>
              ) : (
                <Muted>Sin informe aún</Muted>
              )}
              {mission.error ? (
                <Err message={mission.error} />
              ) : null}
            </>
          ) : null}
        </Screen>
      )}
    </>
  )
}
