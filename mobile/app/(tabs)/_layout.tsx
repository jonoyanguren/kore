import { Tabs } from 'expo-router'
import { Pressable, Text } from 'react-native'

import { useColorScheme } from '@/components/useColorScheme'
import { useClientOnlyValue } from '@/components/useClientOnlyValue'
import Colors from '@/constants/Colors'
import { useAuth } from '@/lib/auth'

function TabIcon({ label }: { label: string }) {
  return <Text style={{ fontSize: 18 }}>{label}</Text>
}

export default function TabLayout() {
  const colorScheme = useColorScheme() ?? 'light'
  const colors = Colors[colorScheme]
  const { logout } = useAuth()

  return (
    <Tabs
      initialRouteName="day"
      screenOptions={{
        tabBarActiveTintColor: colors.tint,
        tabBarInactiveTintColor: colors.tabIconDefault,
        tabBarStyle: { backgroundColor: colors.card },
        headerShown: useClientOnlyValue(false, true),
        headerStyle: { backgroundColor: colors.card },
        headerTintColor: colors.text,
        headerRight: () => (
          <Pressable
            onPress={() => void logout()}
            style={{ marginRight: 16 }}
            hitSlop={8}
          >
            <Text style={{ color: colors.muted, fontSize: 15 }}>Salir</Text>
          </Pressable>
        ),
      }}
    >
      <Tabs.Screen
        name="day"
        options={{
          title: 'Día',
          tabBarIcon: () => <TabIcon label="☀" />,
        }}
      />
      <Tabs.Screen
        name="audio"
        options={{
          title: 'Captura',
          tabBarIcon: () => <TabIcon label="🎙" />,
        }}
      />
      <Tabs.Screen
        name="tasks"
        options={{
          title: 'Tareas',
          tabBarIcon: () => <TabIcon label="✓" />,
        }}
      />
      <Tabs.Screen
        name="missions"
        options={{
          title: 'Misiones',
          tabBarIcon: () => <TabIcon label="⚑" />,
        }}
      />
    </Tabs>
  )
}
