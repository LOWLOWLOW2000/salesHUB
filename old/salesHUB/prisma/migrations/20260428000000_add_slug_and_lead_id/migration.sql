-- Project.slug: フォルダ名・エクスポートファイル名に使う人間可読スラッグ
ALTER TABLE "Project" ADD COLUMN "slug" TEXT;
CREATE UNIQUE INDEX "Project_slug_key" ON "Project"("slug");

-- SalesAccount.leadId: PJシートの lead_id（例: PEAK-000001）
ALTER TABLE "SalesAccount" ADD COLUMN "leadId" TEXT;
CREATE INDEX "SalesAccount_companyId_leadId_idx" ON "SalesAccount"("companyId", "leadId");
