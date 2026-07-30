import { StyleSheet, Text, View } from 'react-native'

import { useColorScheme } from '@/components/useColorScheme'
import Colors from '@/constants/Colors'

export default function DayScreen() {
  const colors = Colors[useColorScheme() ?? 'light']
  return (
    <View style={[styles.root, { backgroundColor: colors.background }]}>
      <Text style={[styles.title, { color: colors.text }]}>Día</Text>
      <Text style={[styles.muted, { color: colors.muted }]}>
        M1: briefing desde GET /api/day
      </Text>
    </View>
  )
}

const styles = StyleSheet.create({
  root: { flex: 1, padding: 20, gap: 8 },
  title: { fontSize: 28, fontWeight: '600' },
  muted: { fontSize: 15, lineHeight: 22 },
})
