/** Primary chips shown by default on Universe — keep this short. */

export const PRIMARY_FACTOR_IDS = ["below_target", "mos_pos", "fresh"] as const

export type PrimaryFactorId = (typeof PRIMARY_FACTOR_IDS)[number]

export function isPrimaryFactor(id: string): boolean {
  return (PRIMARY_FACTOR_IDS as readonly string[]).includes(id)
}
