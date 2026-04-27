-- CreateTable
CREATE TABLE "DealStage" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "projectId" TEXT NOT NULL,
    "accountName" TEXT NOT NULL,
    "contactName" TEXT NOT NULL DEFAULT '',
    "stage" TEXT NOT NULL,
    "source" TEXT NOT NULL DEFAULT '',
    "amount" INTEGER,
    "appointmentDate" DATETIME,
    "closedAt" DATETIME,
    "lostReason" TEXT NOT NULL DEFAULT '',
    "wonReason" TEXT NOT NULL DEFAULT '',
    "notes" TEXT NOT NULL DEFAULT '',
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    CONSTRAINT "DealStage_projectId_fkey" FOREIGN KEY ("projectId") REFERENCES "Project" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "AiSuggestion" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "projectId" TEXT NOT NULL,
    "periodStart" DATETIME NOT NULL,
    "periodEnd" DATETIME NOT NULL,
    "promptSummary" TEXT NOT NULL,
    "suggestion" TEXT NOT NULL,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    CONSTRAINT "AiSuggestion_projectId_fkey" FOREIGN KEY ("projectId") REFERENCES "Project" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

-- RedefineTables
PRAGMA defer_foreign_keys=ON;
PRAGMA foreign_keys=OFF;
CREATE TABLE "new_DailyReport" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "projectId" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "date" DATETIME NOT NULL,
    "callCount" INTEGER NOT NULL DEFAULT 0,
    "connectCount" INTEGER NOT NULL DEFAULT 0,
    "receptionNgCount" INTEGER NOT NULL DEFAULT 0,
    "keymanNgCount" INTEGER NOT NULL DEFAULT 0,
    "materialSentCount" INTEGER NOT NULL DEFAULT 0,
    "appointmentCount" INTEGER NOT NULL DEFAULT 0,
    "callMinutes" INTEGER NOT NULL DEFAULT 0,
    "totalMinutes" INTEGER NOT NULL DEFAULT 0,
    "notes" TEXT NOT NULL DEFAULT '',
    "callSlots" TEXT NOT NULL DEFAULT '',
    "receptionNgReasons" TEXT NOT NULL DEFAULT '',
    "keymanNgReasons" TEXT NOT NULL DEFAULT '',
    "appointmentReasonTags" TEXT NOT NULL DEFAULT '',
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    CONSTRAINT "DailyReport_projectId_fkey" FOREIGN KEY ("projectId") REFERENCES "Project" ("id") ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT "DailyReport_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);
INSERT INTO "new_DailyReport" ("appointmentCount", "callCount", "callMinutes", "connectCount", "createdAt", "date", "id", "keymanNgCount", "materialSentCount", "notes", "projectId", "receptionNgCount", "totalMinutes", "updatedAt", "userId") SELECT "appointmentCount", "callCount", "callMinutes", "connectCount", "createdAt", "date", "id", "keymanNgCount", "materialSentCount", "notes", "projectId", "receptionNgCount", "totalMinutes", "updatedAt", "userId" FROM "DailyReport";
DROP TABLE "DailyReport";
ALTER TABLE "new_DailyReport" RENAME TO "DailyReport";
CREATE INDEX "DailyReport_projectId_date_idx" ON "DailyReport"("projectId", "date");
CREATE INDEX "DailyReport_userId_idx" ON "DailyReport"("userId");
CREATE UNIQUE INDEX "DailyReport_projectId_userId_date_key" ON "DailyReport"("projectId", "userId", "date");
PRAGMA foreign_keys=ON;
PRAGMA defer_foreign_keys=OFF;

-- CreateIndex
CREATE INDEX "DealStage_projectId_stage_idx" ON "DealStage"("projectId", "stage");

-- CreateIndex
CREATE INDEX "DealStage_projectId_appointmentDate_idx" ON "DealStage"("projectId", "appointmentDate");

-- CreateIndex
CREATE INDEX "AiSuggestion_projectId_createdAt_idx" ON "AiSuggestion"("projectId", "createdAt");
