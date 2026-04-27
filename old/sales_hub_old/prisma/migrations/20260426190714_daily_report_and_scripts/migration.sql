-- CreateTable
CREATE TABLE "DailyReport" (
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
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    CONSTRAINT "DailyReport_projectId_fkey" FOREIGN KEY ("projectId") REFERENCES "Project" ("id") ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT "DailyReport_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "ProjectScript" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "projectId" TEXT NOT NULL,
    "category" TEXT NOT NULL,
    "seq" INTEGER NOT NULL,
    "title" TEXT NOT NULL,
    "body" TEXT NOT NULL,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    CONSTRAINT "ProjectScript_projectId_fkey" FOREIGN KEY ("projectId") REFERENCES "Project" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

-- CreateIndex
CREATE INDEX "DailyReport_projectId_date_idx" ON "DailyReport"("projectId", "date");

-- CreateIndex
CREATE INDEX "DailyReport_userId_idx" ON "DailyReport"("userId");

-- CreateIndex
CREATE UNIQUE INDEX "DailyReport_projectId_userId_date_key" ON "DailyReport"("projectId", "userId", "date");

-- CreateIndex
CREATE INDEX "ProjectScript_projectId_category_idx" ON "ProjectScript"("projectId", "category");

-- CreateIndex
CREATE INDEX "ProjectScript_projectId_category_seq_idx" ON "ProjectScript"("projectId", "category", "seq");
