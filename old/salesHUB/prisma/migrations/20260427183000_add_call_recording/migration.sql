-- CreateEnum
CREATE TYPE "CallRecordingSource" AS ENUM ('zoom_phone');

-- CreateEnum
CREATE TYPE "CallRecordingMatchStatus" AS ENUM ('unmatched', 'matched_auto', 'matched_manual');

-- CreateEnum
CREATE TYPE "CallTranscriptSource" AS ENUM ('zoom', 'asr');

-- CreateEnum
CREATE TYPE "CallTranscriptFormat" AS ENUM ('vtt', 'txt', 'json');

-- CreateTable
CREATE TABLE "CallRecording" (
    "id" TEXT NOT NULL,
    "source" "CallRecordingSource" NOT NULL,
    "sourceRecordingRef" TEXT NOT NULL,
    "audioPath" TEXT NOT NULL,
    "transcriptPath" TEXT,
    "transcriptText" TEXT NOT NULL DEFAULT '',
    "transcriptSource" "CallTranscriptSource",
    "transcriptFormat" "CallTranscriptFormat",
    "recordedAt" TIMESTAMP(3) NOT NULL,
    "durationSec" INTEGER,
    "callerLabel" TEXT NOT NULL DEFAULT '',
    "calleePhoneNorm" TEXT NOT NULL DEFAULT '',
    "direction" TEXT NOT NULL DEFAULT '',
    "status" TEXT NOT NULL DEFAULT '',
    "matchStatus" "CallRecordingMatchStatus" NOT NULL DEFAULT 'unmatched',
    "matchConfidence" INTEGER NOT NULL DEFAULT 0,
    "matchedAt" TIMESTAMP(3),
    "projectId" TEXT,
    "callLogId" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "CallRecording_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "CallRecording_sourceRecordingRef_key" ON "CallRecording"("sourceRecordingRef");

-- CreateIndex
CREATE INDEX "CallRecording_projectId_recordedAt_idx" ON "CallRecording"("projectId", "recordedAt");

-- CreateIndex
CREATE INDEX "CallRecording_callLogId_idx" ON "CallRecording"("callLogId");

-- CreateIndex
CREATE INDEX "CallRecording_calleePhoneNorm_idx" ON "CallRecording"("calleePhoneNorm");

-- CreateIndex
CREATE INDEX "CallRecording_recordedAt_idx" ON "CallRecording"("recordedAt");

-- CreateIndex
CREATE INDEX "CallRecording_matchStatus_idx" ON "CallRecording"("matchStatus");

-- AddForeignKey
ALTER TABLE "CallRecording" ADD CONSTRAINT "CallRecording_projectId_fkey" FOREIGN KEY ("projectId") REFERENCES "Project"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "CallRecording" ADD CONSTRAINT "CallRecording_callLogId_fkey" FOREIGN KEY ("callLogId") REFERENCES "CallLog"("id") ON DELETE SET NULL ON UPDATE CASCADE;

