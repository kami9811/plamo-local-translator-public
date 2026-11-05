import { defineConfig } from '@playwright/test';
export default defineConfig({testDir:'tests/browser',timeout:120000,workers:1,reporter:[['list'],['json',{outputFile:'work/browser-results.json'}]],use:{trace:'retain-on-failure'},outputDir:'work/browser-artifacts'});
