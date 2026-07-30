import {
  ActivityIndicator,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
  type RefreshControlProps,
} from 'react-native'

import { useColorScheme } from '@/components/useColorScheme'
import Colors from '@/constants/Colors'

export function Screen({
  children,
  refreshing,
  onRefresh,
}: {
  children: React.ReactNode
  refreshing?: boolean
  onRefresh?: () => void
}) {
  const colors = Colors[useColorScheme()]
  const refreshProps: RefreshControlProps | undefined = onRefresh
    ? {
        refreshing: !!refreshing,
        onRefresh,
        tintColor: colors.tint,
      }
    : undefined

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: colors.background }}
      contentContainerStyle={styles.pad}
      keyboardShouldPersistTaps="handled"
      refreshControl={
        refreshProps ? <RefreshControl {...refreshProps} /> : undefined
      }
    >
      {children}
    </ScrollView>
  )
}

export function Loading() {
  const colors = Colors[useColorScheme()]
  return (
    <View style={styles.center}>
      <ActivityIndicator color={colors.tint} />
    </View>
  )
}

export function Err({ message }: { message: string }) {
  const colors = Colors[useColorScheme()]
  return (
    <Text style={{ color: colors.danger, marginBottom: 12 }}>{message}</Text>
  )
}

export function Muted({ children }: { children: React.ReactNode }) {
  const colors = Colors[useColorScheme()]
  return <Text style={{ color: colors.muted, fontSize: 15, lineHeight: 22 }}>{children}</Text>
}

export function Card({ children }: { children: React.ReactNode }) {
  const colors = Colors[useColorScheme()]
  return (
    <View style={[styles.card, { backgroundColor: colors.card }]}>{children}</View>
  )
}

const styles = StyleSheet.create({
  pad: { padding: 16, paddingBottom: 40, gap: 12 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24 },
  card: {
    borderRadius: 12,
    padding: 14,
    gap: 6,
  },
})
