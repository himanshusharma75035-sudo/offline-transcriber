const { getDefaultConfig, mergeConfig } = require('@react-native/metro-config');

/**
 * Metro configuration
 * https://reactnative.dev/docs/metro
 *
 * @type {import('@react-native/metro-config').MetroConfig}
 */
const defaultConfig = getDefaultConfig(__dirname);

const config = {
  resolver: {
    // GGML Whisper models ship as .bin; let Metro bundle them as assets so
    // `require('./assets/ggml-tiny.bin')` resolves. (.wav is already a default
    // asset extension.)
    assetExts: [...defaultConfig.resolver.assetExts, 'bin'],
  },
};

module.exports = mergeConfig(defaultConfig, config);
