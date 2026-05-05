-- AlterEnum: company-tier "Director" product name split → `manager`; `director` is project-scope only.
ALTER TYPE "AppRole" ADD VALUE 'manager';

-- Old company-scope `director` rows become Manager tier (see schema JSDoc on AppRole).
UPDATE "CompanyMember" SET "role" = CAST('manager' AS "AppRole") WHERE "role" = CAST('director' AS "AppRole");
