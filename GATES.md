# Gates

- [ ] G1 TypeScript passes
  CHECK: powershell -NoProfile -Command "npx tsc --noEmit; if ($LASTEXITCODE -eq 0) { 'PASS_TSC' }"
  EXPECT: PASS_TSC

- [ ] G2 Frontend build passes
  CHECK: powershell -NoProfile -Command "npm run build; if ($LASTEXITCODE -eq 0) { 'PASS_BUILD' }"
  EXPECT: PASS_BUILD

- [ ] G3 Python dependency manifest exists
  CHECK: powershell -NoProfile -Command "if (Test-Path -LiteralPath requirements.txt) { Get-Content -LiteralPath requirements.txt -Raw }"
  EXPECT: fastapi

- [ ] G4 Prompt schema joins avoid known-invalid assumptions
  CHECK: powershell -NoProfile -Command "$text = (Get-Content -LiteralPath prompts/02_db_schema.txt -Raw) + (Get-Content -LiteralPath prompts/03_domain_skills.txt -Raw) + (Get-Content -LiteralPath scripts/gen-prompt.tsx -Raw); if ($text -notmatch 'amfi_fund_benchmarks\.fund_id' -and $text -notmatch 'mfi360_fund_plans\.isin[^_]' -and $text -notmatch 'mcx_icomdex_indices_history\.index_id') { 'PASS_PROMPT_SCHEMA' }"
  EXPECT: PASS_PROMPT_SCHEMA

- [ ] G5 Bundle splitting configured
  CHECK: powershell -NoProfile -Command "Get-Content -LiteralPath vite.config.ts -Raw"
  EXPECT: manualChunks

- [ ] G6 Renderer normalization has structured guards
  CHECK: powershell -NoProfile -Command "Get-Content -LiteralPath src/ChatMessage.tsx -Raw"
  EXPECT: validateRenderableOpenUI
