import {
  DarkTheme,
  DefaultTheme,
  ThemeProvider,
} from '@react-navigation/native'
import { Stack, useRouter, useSegments } from 'expo-router'
import * as SplashScreen from 'expo-splash-screen'
import { useEffect, useRef } from 'react'
import { ActivityIndicator, View } from 'react-native'
import 'react-native-reanimated'

import { useColorScheme } from '@/components/useColorScheme'
import Colors from '@/constants/Colors'
import { AuthProvider, useAuth } from '@/lib/auth'

export { ErrorBoundary } from 'expo-router'

export const unstable_settings = {
  initialRouteName: 'login',
}

void SplashScreen.preventAutoHideAsync().catch(() => {})

export default function RootLayout() {
  return (
    <AuthProvider>
      <RootNavigator />
    </AuthProvider>
  )
}

function RootNavigator() {
  const colorScheme = useColorScheme() ?? 'light'
  const { ready, token } = useAuth()
  const segments = useSegments()
  const router = useRouter()
  const colors = Colors[colorScheme]
  const navigating = useRef(false)

  useEffect(() => {
    if (ready) void SplashScreen.hideAsync().catch(() => {})
  }, [ready])

  useEffect(() => {
    if (!ready || navigating.current) return
    const inLogin = segments[0] === 'login'
    if (!token && !inLogin) {
      navigating.current = true
      router.replace('/login')
      requestAnimationFrame(() => {
        navigating.current = false
      })
    } else if (token && inLogin) {
      navigating.current = true
      router.replace('/(tabs)/day')
      requestAnimationFrame(() => {
        navigating.current = false
      })
    }
  }, [ready, token, segments, router])

  const navTheme = colorScheme === 'dark' ? DarkTheme : DefaultTheme
  const theme = {
    ...navTheme,
    colors: {
      ...navTheme.colors,
      primary: colors.tint,
      background: colors.background,
      card: colors.card,
      text: colors.text,
      border: 'rgba(21, 32, 43, 0.09)',
    },
  }

  if (!ready) {
    return (
      <View
        style={{
          flex: 1,
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: colors.background,
        }}
      >
        <ActivityIndicator color={colors.tint} />
      </View>
    )
  }

  return (
    <ThemeProvider value={theme}>
      <Stack screenOptions={{ headerShown: false, animation: 'none' }}>
        <Stack.Screen name="login" />
        <Stack.Screen name="(tabs)" />
        <Stack.Screen
          name="mission/[id]"
          options={{ headerShown: true, animation: 'default' }}
        />
      </Stack>
    </ThemeProvider>
  )
}
