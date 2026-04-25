export const isManagerEmail = (email: string) => {
  const managerEmail = process.env.MANAGER_EMAIL?.trim().toLowerCase() ?? ''
  return managerEmail.length > 0 && email.trim().toLowerCase() === managerEmail
}

