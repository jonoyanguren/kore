import { Link, Stack } from 'expo-router'
import { StyleSheet, Text, View } from 'react-native'

export default function NotFoundScreen() {
  return (
    <>
      <Stack.Screen options={{ title: 'Oops' }} />
      <View style={styles.container}>
        <Text style={styles.title}>Pantalla no encontrada</Text>
        <Link href="/login" style={styles.link}>
          <Text style={styles.linkText}>Ir al login</Text>
        </Link>
      </View>
    </>
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 20,
  },
  title: { fontSize: 20, fontWeight: '600' },
  link: { marginTop: 15, paddingVertical: 15 },
  linkText: { fontSize: 14, color: '#1f6f5b' },
})
