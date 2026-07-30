import { DarkTheme, DefaultTheme, Stack, ThemeProvider, Redirect, useSegments } from 'expo-router'
import * as SplashScreen from 'expo-splash-screen'
import { useEffect } from 'react'
import { ActivityIndicator, View } from 'react-native'
import 'react-native-reanimated'

import { useColorScheme } from '@/components/useColorScheme'
import Colors from '@/constants/Colors'
import { AuthProvider, useAuth } from '@/lib/auth'

export { ErrorBoundary } from 'expo-router'

SplashScreen.preventAutoHideAsync()

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
  const colors = Colors[colorScheme]

  useEffect(() => {
    if (ready) void SplashScreen.hideAsync()
  }, [ready])

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

  const inLogin = segments[0] === 'login'
  if (!token && !inLogin) {
    return <Redirect href="/login" />
  }
  if (token && inLogin) {
    return <Redirect href="/(tabs)/day" />
  }

  const navTheme = colorScheme === 'dark' ? DarkTheme : DefaultTheme
  const theme = {
    ...navTheme,
    colors: {
      ...navTheme.colors,
      primary: colors.tint,
      background: colors.background,
      card: colors.card,
      text: colors.text,
      border: 'rgba(21,32,43,0.09)',
    },
  }

  return (
    <ThemeProvider value={theme}>
      <Stack screenOptions={{ headerShown: false }}>
        <Stack.Screen name="login" />
        <Stack.Screen name="(tabs)" />
      </Stack>
    </ThemeProvider>
  )
}
