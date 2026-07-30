import { StyleSheet, Text, View } from 'react-native'

import { useColorScheme } from '@/components/useColorScheme'
import Colors from '@/constants/Colors'

/** Modo audio — sin chat. Stub M0; grabación en M2. */
export default function AudioScreen() {
  const colors = Colors[useColorScheme() ?? 'light']
  return (
    <View style={[styles.root, { backgroundColor: colors.background }]}>
      <Text style={[styles.title, { color: colors.text }]}>Audio</Text>
      <Text style={[styles.muted, { color: colors.muted }]}>
        Cuéntale el rollo a Kore. Notas encadenadas → diario, memoria, tareas…
        sin burbujas de chat.
      </Text>
      <View style={[styles.pad, { backgroundColor: colors.card }]}>
        <Text style={[styles.padLabel, { color: colors.tint }]}>M2</Text>
        <Text style={[styles.muted, { color: colors.muted }]}>
          Grabar · soltar · ingest (transcribe → clasificar). Push-to-talk vs
          continuo: lo vemos al implementar.
        </Text>
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  root: { flex: 1, padding: 20, gap: 12 },
  title: { fontSize: 28, fontWeight: '600' },
  muted: { fontSize: 15, lineHeight: 22 },
  pad: {
    marginTop: 12,
    borderRadius: 14,
    padding: 18,
    gap: 8,
    minHeight: 160,
    justifyContent: 'center',
  },
  padLabel: { fontSize: 13, fontWeight: '600', letterSpacing: 0.06 },
})
