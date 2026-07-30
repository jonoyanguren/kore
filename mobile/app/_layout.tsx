import {
  DarkTheme,
  DefaultTheme,
  ThemeProvider,
} from '@react-navigation/native'
import { Stack, useRouter, useSegments } from 'expo-router'
import * as SplashScreen from 'expo-splash-screen'
import { useEffect } from 'react'
import { ActivityIndicator, View } from 'react-native'
import 'react-native-reanimated'

import { useColorScheme } from '@/components/useColorScheme'
import Colors from '@/constants/Colors'
import { AuthProvider, useAuth } from '@/lib/auth'

export { ErrorBoundary } from 'expo-router'

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

  useEffect(() => {
    if (ready) void SplashScreen.hideAsync().catch(() => {})
  }, [ready])

  // Keep Stack mounted — Redirect-without-navigator crashes Expo Go.
  useEffect(() => {
    if (!ready) return
    const inLogin = segments[0] === 'login'
    if (!token && !inLogin) {
      router.replace('/login')
    } else if (token && inLogin) {
      router.replace('/(tabs)/day')
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

  return (
    <ThemeProvider value={theme}>
      <Stack screenOptions={{ headerShown: false }}>
        <Stack.Screen name="login" />
        <Stack.Screen name="(tabs)" />
      </Stack>
      {!ready ? (
        <View
          style={{
            position: 'absolute',
            left: 0,
            right: 0,
            top: 0,
            bottom: 0,
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: colors.background,
          }}
        >
          <ActivityIndicator color={colors.tint} />
        </View>
      ) : null}
    </ThemeProvider>
  )
}
