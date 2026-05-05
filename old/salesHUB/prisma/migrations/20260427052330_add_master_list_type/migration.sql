-- CreateEnum
CREATE TYPE "MasterListType" AS ENUM ('project_sheet', 'house_list');

-- AlterTable
ALTER TABLE "MasterList" ADD COLUMN     "googleSheetName" TEXT,
ADD COLUMN     "googleSpreadsheetId" TEXT,
ADD COLUMN     "lastSyncedAt" TIMESTAMP(3),
ADD COLUMN     "listType" "MasterListType" NOT NULL DEFAULT 'house_list';

-- CreateIndex
CREATE INDEX "MasterList_companyId_listType_idx" ON "MasterList"("companyId", "listType");
