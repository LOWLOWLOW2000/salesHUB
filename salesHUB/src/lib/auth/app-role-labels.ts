import type { AppRole } from '@prisma/client'

/** UI copy aligned with Tier model (gm → manager → director / is|fs|cs; `as` 将来強化)。 */
export const appRoleUiLabel = (role: AppRole): string =>
  ({
    gm: 'GM — General Manager / 企業管理者',
    manager: 'Manager — 全PJ閲覧・Director以下の任命',
    director: 'Director — 担当案件の管理・起案・招待',
    as: 'AS — 獲得営業（計画: 獲得案件で Director 同権）',
    is: 'IS — メンバー',
    fs: 'FS — メンバー',
    cs: 'CS — メンバー'
  } satisfies Record<AppRole, string>)[role]
