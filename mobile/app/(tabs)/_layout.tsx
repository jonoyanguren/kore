import { SymbolView } from 'expo-symbols'
import { Tabs } from 'expo-router'
import { Pressable, Text } from 'react-native'

import { useColorScheme } from '@/components/useColorScheme'
import { useClientOnlyValue } from '@/components/useClientOnlyValue'
import Colors from '@/constants/Colors'
import { useAuth } from '@/lib/auth'

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
          <Pressable onPress={() => void logout()} style={{ marginRight: 16 }} hitSlop={8}>
            <Text style={{ color: colors.muted, fontSize: 15 }}>Salir</Text>
          </Pressable>
        ),
      }}
    >
      <Tabs.Screen
        name="day"
        options={{
          title: 'Día',
          tabBarIcon: ({ color }) => (
            <SymbolView
              name={{ ios: 'sun.max', android: 'wb_sunny', web: 'wb_sunny' }}
              tintColor={color}
              size={26}
            />
          ),
        }}
      />
      <Tabs.Screen
        name="audio"
        options={{
          title: 'Audio',
          tabBarIcon: ({ color }) => (
            <SymbolView
              name={{ ios: 'mic.fill', android: 'mic', web: 'mic' }}
              tintColor={color}
              size={26}
            />
          ),
        }}
      />
      <Tabs.Screen
        name="tasks"
        options={{
          title: 'Tareas',
          tabBarIcon: ({ color }) => (
            <SymbolView
              name={{ ios: 'checklist', android: 'checklist', web: 'checklist' }}
              tintColor={color}
              size={26}
            />
          ),
        }}
      />
      <Tabs.Screen
        name="missions"
        options={{
          title: 'Misiones',
          tabBarIcon: ({ color }) => (
            <SymbolView
              name={{ ios: 'flag.fill', android: 'flag', web: 'flag' }}
              tintColor={color}
              size={26}
            />
          ),
        }}
      />
    </Tabs>
  )
}
