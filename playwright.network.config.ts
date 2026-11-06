import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir:'tests/browser', testMatch:'network.spec.ts', timeout:30000, workers:1,
  reporter:[['list'],['json',{outputFile:'work/network-browser-results.json'}]],
  outputDir:'work/network-browser-artifacts',
});
