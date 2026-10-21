import React, { useState, useEffect } from 'react';
import { StatusBar } from 'expo-status-bar';
import { StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { WebView } from 'react-native-webview';
import { Asset } from 'expo-asset';
import * as FileSystem from 'expo-file-system/legacy';

export default function App() {
  const [html, setHtml] = useState(null);

  useEffect(() => {
    async function loadGame() {
      try {
        const [asset] = await Asset.loadAsync(require('./assets/game.html'));
        const content = await FileSystem.readAsStringAsync(asset.localUri);
        setHtml(content);
      } catch (e) {
        console.error('Game load error:', e);
      }
    }
    loadGame();
  }, []);

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar style="light" />
      {html ? (
        <WebView
          source={{ html }}
          style={styles.webview}
          javaScriptEnabled
          domStorageEnabled
          bounces={false}
          overScrollMode="never"
          showsVerticalScrollIndicator={false}
          showsHorizontalScrollIndicator={false}
          originWhitelist={['*']}
        />
      ) : (
        <View style={styles.loading} />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#050510' },
  webview: { flex: 1 },
  loading: { flex: 1, backgroundColor: '#050510' },
});
