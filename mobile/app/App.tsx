/**
 * Offline Transcriber — mobile
 *
 * P1 milestone: prove on-device, offline transcription with whisper.rn.
 * This screen transcribes a bundled sample clip using a bundled tiny GGML
 * model — no network, nothing leaves the phone. File-pick + mic capture come
 * next (see docs/mobile-plan.md).
 *
 * @format
 */

import { useCallback, useState } from 'react';
import {
  ActivityIndicator,
  SafeAreaView,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { initWhisper } from 'whisper.rn';

// Bundled by Metro at build time (downloaded into assets/ during CI).
const MODEL = require('./assets/ggml-tiny.bin');
const SAMPLE = require('./assets/jfk.wav');

type Status = 'idle' | 'loading' | 'transcribing' | 'done' | 'error';

function App(): React.JSX.Element {
  const [status, setStatus] = useState<Status>('idle');
  const [transcript, setTranscript] = useState('');
  const [error, setError] = useState('');
  const [elapsedMs, setElapsedMs] = useState<number | null>(null);

  const transcribe = useCallback(async () => {
    setError('');
    setTranscript('');
    setElapsedMs(null);
    setStatus('loading');
    const started = Date.now();
    try {
      const ctx = await initWhisper({ filePath: MODEL });
      setStatus('transcribing');
      const { promise } = ctx.transcribe(SAMPLE, { language: 'en' });
      const { result } = await promise;
      setTranscript((result || '').trim());
      setElapsedMs(Date.now() - started);
      setStatus('done');
      await ctx.release();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
      setStatus('error');
    }
  }, []);

  const busy = status === 'loading' || status === 'transcribing';

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar barStyle="light-content" backgroundColor="#0d1117" />
      <ScrollView contentContainerStyle={styles.container}>
        <Text style={styles.title}>Offline Transcriber</Text>
        <Text style={styles.subtitle}>
          On-device · offline · your audio never leaves the phone
        </Text>

        <TouchableOpacity
          style={[styles.button, busy && styles.buttonDisabled]}
          onPress={transcribe}
          disabled={busy}
          activeOpacity={0.8}>
          <Text style={styles.buttonText}>
            {busy ? 'Working…' : 'Transcribe sample clip'}
          </Text>
        </TouchableOpacity>

        {busy && (
          <View style={styles.statusRow}>
            <ActivityIndicator color="#1f6feb" />
            <Text style={styles.statusText}>
              {status === 'loading' ? 'Loading model…' : 'Transcribing…'}
            </Text>
          </View>
        )}

        {status === 'done' && (
          <View style={styles.resultBox}>
            <Text style={styles.resultLabel}>
              Transcript{elapsedMs != null ? `  ·  ${(elapsedMs / 1000).toFixed(1)}s` : ''}
            </Text>
            <Text style={styles.resultText}>{transcript || '(no speech detected)'}</Text>
          </View>
        )}

        {status === 'error' && (
          <View style={[styles.resultBox, styles.errorBox]}>
            <Text style={styles.errorLabel}>Error</Text>
            <Text style={styles.errorText}>{error}</Text>
          </View>
        )}

        <Text style={styles.footer}>
          Model: ggml-tiny (bundled). Next: pick your own audio, live mic,
          language choice, export.
        </Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#0d1117' },
  container: { padding: 24, paddingTop: 48, flexGrow: 1 },
  title: { color: '#f0f6fc', fontSize: 28, fontWeight: '700' },
  subtitle: { color: '#8b949e', fontSize: 14, marginTop: 6, marginBottom: 32 },
  button: {
    backgroundColor: '#1f6feb',
    paddingVertical: 16,
    borderRadius: 12,
    alignItems: 'center',
  },
  buttonDisabled: { backgroundColor: '#30363d' },
  buttonText: { color: '#ffffff', fontSize: 16, fontWeight: '600' },
  statusRow: { flexDirection: 'row', alignItems: 'center', marginTop: 24, gap: 10 },
  statusText: { color: '#8b949e', fontSize: 14 },
  resultBox: {
    marginTop: 28,
    backgroundColor: '#161b22',
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: '#30363d',
  },
  resultLabel: { color: '#8b949e', fontSize: 12, textTransform: 'uppercase', marginBottom: 8 },
  resultText: { color: '#f0f6fc', fontSize: 16, lineHeight: 24 },
  errorBox: { borderColor: '#f85149' },
  errorLabel: { color: '#f85149', fontSize: 12, textTransform: 'uppercase', marginBottom: 8 },
  errorText: { color: '#ff7b72', fontSize: 14, fontFamily: 'monospace' },
  footer: { color: '#484f58', fontSize: 12, marginTop: 'auto', paddingTop: 32 },
});

export default App;
